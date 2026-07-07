from __future__ import annotations

from typing import Optional

from playwright.async_api import Browser, BrowserContext

from app.scraping.exceptions import BrowserError
from app.scraping.models import BrowserConfig
from app.collectors.logging import CollectorLoggerProtocol


class ContextManager:
    """Manages browser contexts (isolated browsing sessions).

    Each context has its own cookies, cache, and storage.
    Useful for multi-tenant isolation or parallel scraping.

    Usage:
        cm = ContextManager(config, logger)
        context = await cm.create_context(browser)
        # ... use context ...
        await cm.close_context()
    """

    def __init__(
        self,
        config: BrowserConfig,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._contexts: list[BrowserContext] = []

    async def create_context(
        self,
        browser: Browser,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> BrowserContext:
        """Create a new browser context.

        Args:
            browser: A running Playwright Browser instance.
            extra_headers: Optional extra HTTP headers for all pages.

        Returns:
            A new BrowserContext.

        Raises:
            BrowserError: If context creation fails.
        """
        context_options: dict = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            "user_agent": self._config.user_agent or None,
            "ignore_https_errors": True,
        }

        if self._config.proxy_url:
            context_options["proxy"] = {"server": self._config.proxy_url}

        if self._config.downloads_path:
            context_options["accept_downloads"] = True

        try:
            context = await browser.new_context(**context_options)

            if extra_headers:
                await context.set_extra_http_headers(extra_headers)

            if self._config.tracing_path:
                await context.tracing.start(
                    screenshots=True,
                    snapshots=True,
                    sources=True,
                )

            self._contexts.append(context)
            if self._logger:
                self._logger.info(
                    "Browser context created",
                    viewport=f"{self._config.viewport_width}x{self._config.viewport_height}",
                    context_index=len(self._contexts),
                )
            return context
        except Exception as e:
            raise BrowserError(
                message=f"Failed to create browser context: {e}",
                browser_type=self._config.browser_type,
                original=e,
            ) from e

    async def close_context(self, context: Optional[BrowserContext] = None) -> None:
        """Close a specific context or all contexts.

        Args:
            context: The context to close. If None, closes all.
        """
        if context is not None:
            await self._close_single(context)
        else:
            for ctx in list(self._contexts):
                await self._close_single(ctx)

    async def _close_single(self, context: BrowserContext) -> None:
        """Close a single context and remove it from tracking."""
        try:
            if self._config.tracing_path and context in self._contexts:
                trace_name = f"trace_{id(context)}"
                trace_path = f"{self._config.tracing_path}/{trace_name}.zip"
                await context.tracing.stop(path=trace_path)

            await context.close()
            if self._logger:
                self._logger.info("Browser context closed")
        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Error closing browser context",
                    exception=e,
                )
        finally:
            if context in self._contexts:
                self._contexts.remove(context)

    async def cleanup(self) -> None:
        """Close all contexts and release resources.

        Safe to call multiple times.
        """
        await self.close_context()

    @property
    def contexts(self) -> list[BrowserContext]:
        return list(self._contexts)

    @property
    def context_count(self) -> int:
        return len(self._contexts)
