from __future__ import annotations

from typing import Any, Optional

from app.collectors.config import CollectorConfigProvider
from app.collectors.logging import CollectorLoggerProtocol
from app.scraping.models import BrowserConfig, SessionConfig
from app.scraping.session import BrowserSession


class ScrapingEngine:
    """Top-level orchestrator for browser-based scraping.

    Reads configuration from the centralized settings layer and
    creates BrowserSession instances.

    Future collectors use this to request a browser session:

        engine = ScrapingEngine(logger=logger)
        session = await engine.create_session()
        await session.start()
        page = await session.navigate("https://...")
        # ...
        await session.stop()

    Extension points:
    - Override create_browser_config() for custom config sources
    - Override create_session_config() for custom retry/timeout settings
    - Override create_logger() for custom logging
    """

    def __init__(
        self,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._logger = logger
        self._config_provider = CollectorConfigProvider()

    def create_browser_config(self) -> BrowserConfig:
        """Create a BrowserConfig from centralized settings.

        Reads from settings.playwright via CollectorConfigProvider.

        Override this method to customize config sources.
        """
        pw_settings = self._config_provider.get_playwright_settings()
        return BrowserConfig(
            headless=pw_settings.get("headless", True),
            browser_type=pw_settings.get("browser_type", "chromium"),
            timeout_ms=pw_settings.get("timeout_ms", 30000),
            slow_mo_ms=pw_settings.get("slow_mo_ms", 50),
            viewport_width=pw_settings.get("viewport_width", 1920),
            viewport_height=pw_settings.get("viewport_height", 1080),
            user_agent=pw_settings.get("user_agent", ""),
        )

    def create_session_config(self) -> SessionConfig:
        """Create a SessionConfig from centralized settings.

        Reads retry/timeout settings from CollectorConfigProvider.

        Override this method to customize retry/backoff config.
        """
        global_settings = self._config_provider.get_global_settings()
        return SessionConfig(
            max_retries=global_settings.get("max_retries", 3),
            retry_base_delay_s=1.0,
            retry_max_delay_s=60.0,
            retry_backoff=global_settings.get(
                "retry_backoff_factor", 2.0
            ),
            navigation_timeout_s=30.0,
        )

    def create_session(
        self,
        browser_config: Optional[BrowserConfig] = None,
        session_config: Optional[SessionConfig] = None,
    ) -> BrowserSession:
        """Create a new BrowserSession.

        Args:
            browser_config: Optional override. Uses centralized
                config if not provided.
            session_config: Optional override. Uses centralized
                config if not provided.

        Returns:
            A configured BrowserSession ready for start().
        """
        return BrowserSession(
            browser_config=browser_config or self.create_browser_config(),
            session_config=session_config or self.create_session_config(),
            logger=self._logger,
        )

    @property
    def logger(self) -> Optional[CollectorLoggerProtocol]:
        return self._logger
