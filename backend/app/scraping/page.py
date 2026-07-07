from __future__ import annotations

import asyncio
from typing import Any, Optional

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

from app.scraping.exceptions import NavigationError
from app.scraping.models import BrowserConfig, NavigationOptions
from app.collectors.exceptions import NetworkError
from app.collectors.logging import CollectorLoggerProtocol


class PageManager:
    """Manages page-level operations and navigation utilities.

    All methods are generic - no website-specific selectors or logic.
    Navigation failures are wrapped in NavigationError.
    """

    def __init__(
        self,
        config: BrowserConfig,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._pages: list[Page] = []

    async def create_page(self, context: BrowserContext) -> Page:
        """Create a new page in the given context.

        Args:
            context: A Playwright BrowserContext.

        Returns:
            A new Page instance.

        Raises:
            NavigationError: If page creation fails.
        """
        try:
            page = await context.new_page()
            self._pages.append(page)
            if self._logger:
                self._logger.info(
                    "Page created",
                    total_pages=len(self._pages),
                )
            return page
        except Exception as e:
            raise NavigationError(
                message=f"Failed to create page: {e}",
                original=e,
            ) from e

    async def goto(
        self,
        page: Page,
        options: NavigationOptions,
    ) -> Page:
        """Navigate to a URL.

        Args:
            page: The page to navigate.
            options: Navigation options including URL, timeout, wait strategy.

        Returns:
            The page after navigation.

        Raises:
            NavigationError: If navigation fails.
        """
        timeout = options.timeout_ms or self._config.timeout_ms
        rate_limit = self._config.rate_limit_ms

        if rate_limit > 0:
            await asyncio.sleep(rate_limit / 1000.0)

        try:
            if self._logger:
                self._logger.info(
                    "Navigating to URL",
                    url=options.url,
                    timeout=timeout,
                )

            response = await page.goto(
                url=options.url,
                wait_until=options.wait_until,
                timeout=timeout,
            )

            status_code = response.status if response else None
            if status_code and status_code >= 400:
                raise NavigationError(
                    message=(
                        f"HTTP {status_code} loading {options.url}"
                    ),
                    url=options.url,
                    status_code=status_code,
                )

            if options.extra_headers:
                await page.set_extra_http_headers(options.extra_headers)

            if options.wait_for_selector:
                selector_timeout = (
                    options.wait_for_selector_timeout_ms or timeout
                )
                try:
                    await page.wait_for_selector(
                        selector=options.wait_for_selector,
                        timeout=selector_timeout,
                    )
                except PlaywrightTimeout as e:
                    raise NavigationError(
                        message=(
                            f"Selector '{options.wait_for_selector}' "
                            f"not found on {options.url}"
                        ),
                        url=options.url,
                        original=e,
                    ) from e

            if options.scroll_to_bottom:
                await self.scroll_to_bottom(page)

            if options.take_screenshot:
                await self.take_screenshot(page)

            if self._logger:
                self._logger.info(
                    "Navigation complete",
                    url=options.url,
                    status=status_code,
                )

            return page

        except NavigationError:
            raise

        except PlaywrightTimeout as e:
            raise NavigationError(
                message=f"Navigation timed out: {options.url}",
                url=options.url,
                original=e,
            ) from e

        except Exception as e:
            raise NavigationError(
                message=f"Navigation failed: {options.url} - {e}",
                url=options.url,
                original=e,
            ) from e

    async def reload(self, page: Page) -> None:
        """Reload the current page.

        Raises:
            NavigationError: If reload fails.
        """
        try:
            await page.reload(wait_until="load")
        except Exception as e:
            raise NavigationError(
                message=f"Page reload failed: {e}",
                original=e,
            ) from e

    async def wait_for_selector(
        self,
        page: Page,
        selector: str,
        timeout_ms: Optional[int] = None,
    ) -> Any:
        """Wait for a CSS selector to appear.

        Args:
            page: The page to wait on.
            selector: CSS selector string.
            timeout_ms: Maximum wait time.

        Returns:
            The element handle.

        Raises:
            NavigationError: If the selector does not appear.
        """
        timeout = timeout_ms or self._config.timeout_ms
        try:
            return await page.wait_for_selector(
                selector=selector,
                timeout=timeout,
            )
        except PlaywrightTimeout as e:
            raise NavigationError(
                message=f"Selector '{selector}' not found within {timeout}ms",
                original=e,
            ) from e

    async def wait_for_load_state(
        self,
        page: Page,
        state: str = "networkidle",
        timeout_ms: Optional[int] = None,
    ) -> None:
        """Wait for the page to reach a specific load state.

        Args:
            page: The page to wait on.
            state: Load state ('load', 'domcontentloaded', 'networkidle').
            timeout_ms: Maximum wait time.
        """
        timeout = timeout_ms or self._config.timeout_ms
        try:
            await page.wait_for_load_state(state=state, timeout=timeout)
        except PlaywrightTimeout as e:
            raise NavigationError(
                message=f"Page did not reach state '{state}' within {timeout}ms",
                original=e,
            ) from e

    async def wait_for_network_idle(
        self,
        page: Page,
        timeout_ms: Optional[int] = None,
    ) -> None:
        """Wait for network activity to cease.

        Convenience wrapper around wait_for_load_state('networkidle').
        """
        await self.wait_for_load_state(page, state="networkidle", timeout_ms=timeout_ms)

    async def scroll_to_bottom(self, page: Page) -> None:
        """Scroll the page to the bottom.

        Useful for triggering lazy-loaded content.
        """
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)
        except Exception as e:
            if self._logger:
                self._logger.warning(
                    "Scroll to bottom failed",
                    exception=str(e),
                )

    async def scroll_to_element(
        self,
        page: Page,
        selector: str,
    ) -> None:
        """Scroll to a specific element on the page.

        Args:
            page: The page to scroll on.
            selector: CSS selector for the target element.
        """
        try:
            await page.evaluate(
                f"document.querySelector('{selector}')?.scrollIntoView()",
            )
            await asyncio.sleep(0.3)
        except Exception as e:
            if self._logger:
                self._logger.warning(
                    "Scroll to element failed",
                    selector=selector,
                    exception=str(e),
                )

    async def take_screenshot(
        self,
        page: Page,
        path: Optional[str] = None,
    ) -> Optional[bytes]:
        """Take a screenshot of the current page.

        Args:
            page: The page to screenshot.
            path: Optional file path to save the screenshot.

        Returns:
            Screenshot bytes if path is not provided, otherwise None.
        """
        try:
            kwargs: dict = {"full_page": True}
            if path:
                kwargs["path"] = path
            return await page.screenshot(**kwargs)
        except Exception as e:
            if self._logger:
                self._logger.warning(
                    "Screenshot failed",
                    exception=str(e),
                )
            return None

    async def get_html(self, page: Page) -> str:
        """Get the full HTML content of the page.

        Returns:
            The page HTML as a string.
        """
        try:
            return await page.content()
        except Exception as e:
            raise NavigationError(
                message=f"Failed to get page HTML: {e}",
                original=e,
            ) from e

    async def get_title(self, page: Page) -> str:
        """Get the page title.

        Returns:
            The page title string.
        """
        try:
            return await page.title()
        except Exception as e:
            raise NavigationError(
                message=f"Failed to get page title: {e}",
                original=e,
            ) from e

    async def get_url(self, page: Page) -> str:
        """Get the current page URL.

        Returns:
            The current URL string.
        """
        try:
            return page.url
        except Exception as e:
            raise NavigationError(
                message=f"Failed to get page URL: {e}",
                original=e,
            ) from e

    async def close_page(self, page: Page) -> None:
        """Close a page and remove it from tracking.

        Safe to call multiple times.
        """
        try:
            await page.close()
        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Error closing page",
                    exception=e,
                )
        finally:
            if page in self._pages:
                self._pages.remove(page)

    async def cleanup(self) -> None:
        """Close all tracked pages.

        Safe to call multiple times.
        """
        for page in list(self._pages):
            await self.close_page(page)

    @property
    def pages(self) -> list[Page]:
        return list(self._pages)

    @property
    def page_count(self) -> int:
        return len(self._pages)
