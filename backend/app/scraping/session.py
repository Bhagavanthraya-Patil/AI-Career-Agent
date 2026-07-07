from __future__ import annotations

from typing import Any, Optional

from playwright.async_api import Browser, BrowserContext, Page

from app.scraping.browser import BrowserManager
from app.scraping.context import ContextManager
from app.scraping.exceptions import BrowserError, NavigationError
from app.scraping.models import BrowserConfig, NavigationOptions, SessionConfig
from app.scraping.page import PageManager
from app.collectors.exceptions import NetworkError
from app.collectors.logging import CollectorLoggerProtocol
from app.collectors.retry import RetryStrategy


class BrowserSession:
    """High-level facade for browser automation.

    Combines BrowserManager, ContextManager, and PageManager into a
    single dependency-injection-ready interface.

    Future collectors request a BrowserSession without managing
    Playwright directly:

        class MyCollector(BaseCollector):
            def __init__(self, config, logger, browser_session: BrowserSession):
                ...

    Usage:
        session = BrowserSession(browser_config, session_config, logger)
        await session.start()
        page = await session.navigate("https://example.com")
        html = await session.get_html(page)
        await session.stop()
    """

    def __init__(
        self,
        browser_config: BrowserConfig,
        session_config: Optional[SessionConfig] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._browser_config = browser_config
        self._session_config = session_config or SessionConfig()
        self._logger = logger

        self._browser_manager = BrowserManager(browser_config, logger)
        self._context_manager = ContextManager(browser_config, logger)
        self._page_manager = PageManager(browser_config, logger)

        self._retry = RetryStrategy(
            max_retries=self._session_config.max_retries,
            base_delay_seconds=self._session_config.retry_base_delay_s,
            max_delay_seconds=self._session_config.retry_max_delay_s,
            backoff_multiplier=self._session_config.retry_backoff,
            timeout_seconds=self._session_config.navigation_timeout_s,
            retryable_exceptions=(
                NetworkError,
                NavigationError,
            ),
        )

        self._context: Optional[BrowserContext] = None
        self._current_page: Optional[Page] = None
        self._started = False

    async def start(
        self,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> None:
        """Start a browser session.

        Initializes Playwright, launches a browser, creates a context,
        and creates a default page.

        Args:
            extra_headers: Optional HTTP headers for all requests.

        Raises:
            BrowserError: If any startup step fails.
        """
        await self._browser_manager.initialize()
        browser = await self._browser_manager.create_browser()
        self._context = await self._context_manager.create_context(
            browser,
            extra_headers=extra_headers,
        )
        self._current_page = await self._page_manager.create_page(self._context)
        self._started = True

        if self._logger:
            self._logger.info(
                "Browser session started",
                browser_type=self._browser_config.browser_type,
                headless=self._browser_config.headless,
            )

    async def navigate(
        self,
        url: str,
        options: Optional[NavigationOptions] = None,
    ) -> Page:
        """Navigate to a URL with retry support.

        Args:
            url: The target URL.
            options: Optional navigation options overrides.

        Returns:
            The page after navigation.

        Raises:
            NavigationError: If all navigation retries fail.
        """
        if not self._started or self._current_page is None:
            raise BrowserError(
                message="Session not started. Call start() first.",
            )

        nav_options = options or NavigationOptions(url=url)
        nav_options.url = url

        if nav_options.retry_on_failure:
            try:
                page = await self._retry.execute(
                    self._page_manager.goto,
                    self._current_page,
                    nav_options,
                )
                return page
            except Exception as e:
                raise NavigationError(
                    message=(
                        f"Navigation failed after "
                        f"{self._session_config.max_retries} retries: {url}"
                    ),
                    url=url,
                    original=e,
                ) from e
        else:
            return await self._page_manager.goto(
                self._current_page,
                nav_options,
            )

    async def goto(
        self,
        page: Page,
        options: NavigationOptions,
    ) -> Page:
        """Navigate a specific page to a URL.

        Low-level access allowing collectors to manage multiple pages.
        """
        return await self._page_manager.goto(page, options)

    async def reload(self) -> None:
        """Reload the current page."""
        if self._current_page is None:
            raise BrowserError(message="No current page to reload.")
        await self._page_manager.reload(self._current_page)

    async def create_page(self) -> Page:
        """Create a new page in the current context.

        Returns:
            A new Page instance.
        """
        if self._context is None:
            raise BrowserError(
                message="No active context. Call start() first.",
            )
        return await self._page_manager.create_page(self._context)

    def switch_page(self, page: Page) -> None:
        """Switch the active page to an existing page.

        Args:
            page: The page to make active.
        """
        self._current_page = page

    async def close_page(self, page: Optional[Page] = None) -> None:
        """Close a specific page or the current page."""
        target = page or self._current_page
        if target is None:
            return
        if target == self._current_page:
            self._current_page = None
        await self._page_manager.close_page(target)

    async def stop(self) -> None:
        """Stop the browser session and release all resources.

        Closes pages, context, browser, and Playwright.
        Safe to call multiple times (idempotent).
        """
        await self._page_manager.cleanup()
        self._current_page = None
        await self._context_manager.cleanup()
        self._context = None
        await self._browser_manager.cleanup()
        self._started = False

        if self._logger:
            self._logger.info("Browser session stopped")

    # Delegate page utilities

    async def wait_for_selector(
        self,
        selector: str,
        timeout_ms: Optional[int] = None,
    ) -> Any:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        return await self._page_manager.wait_for_selector(
            self._current_page,
            selector,
            timeout_ms,
        )

    async def wait_for_load_state(
        self,
        state: str = "networkidle",
        timeout_ms: Optional[int] = None,
    ) -> None:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        await self._page_manager.wait_for_load_state(
            self._current_page,
            state,
            timeout_ms,
        )

    async def wait_for_network_idle(
        self,
        timeout_ms: Optional[int] = None,
    ) -> None:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        await self._page_manager.wait_for_network_idle(
            self._current_page,
            timeout_ms,
        )

    async def scroll_to_bottom(self) -> None:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        await self._page_manager.scroll_to_bottom(self._current_page)

    async def scroll_to_element(self, selector: str) -> None:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        await self._page_manager.scroll_to_element(
            self._current_page,
            selector,
        )

    async def take_screenshot(
        self,
        path: Optional[str] = None,
    ) -> Optional[bytes]:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        return await self._page_manager.take_screenshot(
            self._current_page,
            path,
        )

    async def get_html(self) -> str:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        return await self._page_manager.get_html(self._current_page)

    async def get_title(self) -> str:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        return await self._page_manager.get_title(self._current_page)

    async def get_url(self) -> str:
        if self._current_page is None:
            raise BrowserError(message="No active page.")
        return await self._page_manager.get_url(self._current_page)

    # Properties

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def browser(self) -> Optional[Browser]:
        return self._browser_manager.browser

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

    @property
    def current_page(self) -> Optional[Page]:
        return self._current_page

    @property
    def browser_config(self) -> BrowserConfig:
        return self._browser_config

    @property
    def session_config(self) -> SessionConfig:
        return self._session_config
