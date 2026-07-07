from __future__ import annotations

from typing import Any, Optional

from app.agents.apply_agent.exceptions import BrowserCleanupError, NavigationError
from app.collectors.logging import CollectorLoggerProtocol


class ApplicationSession:
    """Manages a Playwright browser session for a single application.

    Wraps BrowserSession with application-specific lifecycle,
    including navigation, page management, and cleanup.

    Usage::

        session = ApplicationSession(browser_session, logger=logger)
        await session.navigate(job_url)
        page = session.current_page
        await session.close()
    """

    DEFAULT_TIMEOUT: int = 60000
    NAVIGATION_TIMEOUT: int = 30000

    def __init__(
        self,
        browser_session: Any,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._browser_session = browser_session
        self._logger = logger
        self._current_url: Optional[str] = None
        self._navigation_count: int = 0

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    @property
    def current_page(self) -> Any:
        """Get the current Playwright page from the browser session."""
        return self._browser_session.current_page()

    @property
    def is_closed(self) -> bool:
        """Check whether the underlying browser session is closed."""
        return self._browser_session.is_closed()

    @property
    def navigation_count(self) -> int:
        return self._navigation_count

    async def navigate(self, url: str, timeout: Optional[int] = None) -> None:
        """Navigate to a URL and wait for the page to load.

        Args:
            url: The target URL.
            timeout: Navigation timeout in ms (default: 30000).

        Raises:
            NavigationError: If navigation fails or times out.
        """
        try:
            self._log(f"Navigating to {url}")
            await self._browser_session.navigate(
                url=url,
                timeout=timeout or self.NAVIGATION_TIMEOUT,
                wait_until="networkidle",
            )
            self._current_url = url
            self._navigation_count += 1
            self._log(f"Navigation successful: {url}")
        except Exception as exc:
            raise NavigationError(
                message=f"Failed to navigate to {url}: {exc}",
                step="navigate",
                original=exc,
            ) from exc

    async def wait_for_load(self, timeout: Optional[int] = None) -> None:
        """Wait for the current page to reach a stable load state.

        Args:
            timeout: Timeout in ms (default: 30000).
        """
        page = self.current_page
        if page:
            await page.wait_for_load_state(
                "networkidle",
                timeout=timeout or self.DEFAULT_TIMEOUT,
            )

    async def screenshot(self, path: Optional[str] = None) -> Optional[str]:
        """Capture a screenshot of the current page.

        Args:
            path: Optional file path for the screenshot.

        Returns:
            The screenshot file path, or None on failure.
        """
        try:
            if path:
                await self.current_page.screenshot(path=path, full_page=True)
                return path
            return await self._browser_session.screenshot(path)
        except Exception as exc:
            self._log(f"Screenshot failed: {exc}", "warning")
            return None

    async def close(self) -> None:
        """Close the browser session.

        Safe to call multiple times. Logs and swallows cleanup errors.
        """
        try:
            if not self.is_closed:
                await self._browser_session.close()
                self._log("Browser session closed")
        except Exception as exc:
            self._log(f"Error closing browser session: {exc}", "error")
            raise BrowserCleanupError(
                message=f"Failed to close browser session: {exc}",
                step="cleanup",
                original=exc,
            ) from exc

    async def __aenter__(self) -> ApplicationSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
