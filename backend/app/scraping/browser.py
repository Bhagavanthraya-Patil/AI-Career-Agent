from __future__ import annotations

from typing import Optional

from playwright.async_api import Browser, Playwright, async_playwright

from app.scraping.exceptions import BrowserError
from app.scraping.models import BrowserConfig
from app.collectors.logging import CollectorLoggerProtocol


class BrowserManager:
    """Manages the Playwright browser lifecycle.

    Responsibilities:
    - Starting and stopping the Playwright process
    - Launching and closing browser instances
    - Reading configuration from BrowserConfig

    Usage:
        manager = BrowserManager(config, logger)
        await manager.initialize()
        browser = await manager.create_browser()
        # ... use browser ...
        await manager.close_browser()
        await manager.cleanup()
    """

    def __init__(
        self,
        config: BrowserConfig,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def initialize(self) -> None:
        """Start the Playwright process.

        Must be called before create_browser().
        Safe to call multiple times (idempotent after first call).
        """
        if self._playwright is not None:
            return
        try:
            self._playwright = await async_playwright().start()
            if self._logger:
                self._logger.info(
                    "Playwright started",
                    browser_type=self._config.browser_type,
                )
        except Exception as e:
            raise BrowserError(
                message=f"Failed to start Playwright: {e}",
                browser_type=self._config.browser_type,
                original=e,
            ) from e

    async def create_browser(self) -> Browser:
        """Launch a browser instance.

        Returns:
            A Playwright Browser instance.

        Raises:
            BrowserError: If browser launch fails.
        """
        if self._playwright is None:
            raise BrowserError(
                message="Playwright not initialized. Call initialize() first.",
                browser_type=self._config.browser_type,
            )

        launch_options: dict = {
            "headless": self._config.headless,
            "slow_mo": self._config.slow_mo_ms,
        }

        if self._config.proxy_url:
            launch_options["proxy"] = {"server": self._config.proxy_url}

        browser_type_name = self._config.browser_type
        browser_launcher = getattr(self._playwright, browser_type_name, None)
        if browser_launcher is None:
            raise BrowserError(
                message=f"Unsupported browser type: {browser_type_name}",
                browser_type=browser_type_name,
            )

        try:
            self._browser = await browser_launcher.launch(**launch_options)
            if self._logger:
                self._logger.info(
                    "Browser launched",
                    browser_type=browser_type_name,
                    headless=self._config.headless,
                )
            return self._browser
        except Exception as e:
            raise BrowserError(
                message=f"Failed to launch {browser_type_name}: {e}",
                browser_type=browser_type_name,
                original=e,
            ) from e

    async def close_browser(self) -> None:
        """Close the browser instance.

        Safe to call multiple times (idempotent).
        """
        if self._browser is None:
            return
        try:
            await self._browser.close()
            if self._logger:
                self._logger.info("Browser closed")
        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Error closing browser",
                    exception=e,
                )
        finally:
            self._browser = None

    async def cleanup(self) -> None:
        """Release all Playwright resources.

        Closes the browser and stops the Playwright process.
        Must be the last call. Safe to call multiple times.
        """
        await self.close_browser()

        if self._playwright is not None:
            try:
                await self._playwright.stop()
                if self._logger:
                    self._logger.info("Playwright stopped")
            except Exception as e:
                if self._logger:
                    self._logger.error(
                        "Error stopping Playwright",
                        exception=e,
                    )
            finally:
                self._playwright = None

    @property
    def is_initialized(self) -> bool:
        return self._playwright is not None

    @property
    def is_browser_running(self) -> bool:
        return self._browser is not None

    @property
    def config(self) -> BrowserConfig:
        return self._config

    @property
    def browser(self) -> Optional[Browser]:
        return self._browser
