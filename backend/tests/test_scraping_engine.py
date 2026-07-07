from __future__ import annotations

from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.collectors.exceptions import NetworkError
from app.collectors.logging import CollectorLoggerProtocol
from app.scraping.browser import BrowserManager
from app.scraping.context import ContextManager
from app.scraping.engine import ScrapingEngine
from app.scraping.exceptions import BrowserError, NavigationError
from app.scraping.models import BrowserConfig, NavigationOptions, SessionConfig
from app.scraping.page import PageManager
from app.scraping.session import BrowserSession


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def browser_config() -> BrowserConfig:
    return BrowserConfig(
        headless=True,
        browser_type="chromium",
        timeout_ms=5000,
        slow_mo_ms=0,
        viewport_width=1280,
        viewport_height=720,
    )


@pytest.fixture
def session_config() -> SessionConfig:
    return SessionConfig(
        max_retries=2,
        retry_base_delay_s=0.1,
        retry_max_delay_s=1.0,
        retry_backoff=2.0,
        navigation_timeout_s=5.0,
    )


@pytest.fixture
def logger() -> CollectorLoggerProtocol:
    return MagicMock(spec=CollectorLoggerProtocol)


@pytest.fixture
def mock_playwright() -> MagicMock:
    pw = MagicMock()
    pw.start = AsyncMock()
    pw.stop = AsyncMock()
    return pw


@pytest.fixture
def mock_browser() -> MagicMock:
    browser = MagicMock()
    browser.close = AsyncMock()
    browser.new_context = AsyncMock()
    return browser


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.close = AsyncMock()
    ctx.new_page = AsyncMock()
    ctx.set_extra_http_headers = AsyncMock()
    tracing = MagicMock()
    tracing.start = AsyncMock()
    tracing.stop = AsyncMock()
    ctx.tracing = tracing
    return ctx


@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.goto = AsyncMock()
    page.close = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    page.title = AsyncMock(return_value="Test Page")
    page.url = "https://example.com"
    page.reload = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.evaluate = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake-png")
    page.set_extra_http_headers = AsyncMock()
    return page


@pytest.fixture
def mock_browser_type() -> MagicMock:
    bt = MagicMock()
    bt.launch = AsyncMock()
    return bt


# ---------------------------------------------------------------------------
# Test BrowserConfig
# ---------------------------------------------------------------------------

class TestBrowserConfig:
    def test_defaults(self) -> None:
        config = BrowserConfig()
        assert config.headless is True
        assert config.browser_type == "chromium"
        assert config.timeout_ms == 30000
        assert config.slow_mo_ms == 50
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080

    def test_custom_values(self) -> None:
        config = BrowserConfig(
            headless=False,
            browser_type="firefox",
            timeout_ms=10000,
            slow_mo_ms=100,
            viewport_width=1024,
            viewport_height=768,
            user_agent="CustomAgent/1.0",
            proxy_url="http://proxy:8080",
        )
        assert config.headless is False
        assert config.browser_type == "firefox"
        assert config.user_agent == "CustomAgent/1.0"
        assert config.proxy_url == "http://proxy:8080"

    def test_viewport_minimums(self) -> None:
        config = BrowserConfig(viewport_width=320, viewport_height=240)
        assert config.viewport_width == 320
        assert config.viewport_height == 240

    def test_max_pages_bounds(self) -> None:
        config = BrowserConfig(max_pages=1)
        assert config.max_pages == 1
        config = BrowserConfig(max_pages=50)
        assert config.max_pages == 50


# ---------------------------------------------------------------------------
# Test SessionConfig
# ---------------------------------------------------------------------------

class TestSessionConfig:
    def test_defaults(self) -> None:
        config = SessionConfig()
        assert config.max_retries == 3
        assert config.retry_base_delay_s == 1.0
        assert config.retry_max_delay_s == 60.0
        assert config.retry_backoff == 2.0
        assert config.navigation_timeout_s == 30.0

    def test_custom_values(self) -> None:
        config = SessionConfig(
            max_retries=5,
            retry_base_delay_s=2.0,
            retry_max_delay_s=30.0,
            retry_backoff=1.5,
            navigation_timeout_s=60.0,
        )
        assert config.max_retries == 5
        assert config.navigation_timeout_s == 60.0


# ---------------------------------------------------------------------------
# Test NavigationOptions
# ---------------------------------------------------------------------------

class TestNavigationOptions:
    def test_defaults(self) -> None:
        opts = NavigationOptions(url="https://example.com")
        assert opts.url == "https://example.com"
        assert opts.wait_until == "load"
        assert opts.retry_on_failure is True
        assert opts.scroll_to_bottom is False
        assert opts.take_screenshot is False

    def test_full_options(self) -> None:
        opts = NavigationOptions(
            url="https://example.com/jobs",
            wait_until="networkidle",
            timeout_ms=10000,
            retry_on_failure=False,
            scroll_to_bottom=True,
            wait_for_selector=".job-listing",
            wait_for_selector_timeout_ms=5000,
            take_screenshot=True,
            extra_headers={"Authorization": "Bearer test"},
        )
        assert opts.wait_until == "networkidle"
        assert opts.wait_for_selector == ".job-listing"
        assert opts.extra_headers["Authorization"] == "Bearer test"


# ---------------------------------------------------------------------------
# Test BrowserManager
# ---------------------------------------------------------------------------

class TestBrowserManager:
    @patch("app.scraping.browser.async_playwright")
    async def test_initialize_success(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        logger: CollectorLoggerProtocol,
        mock_playwright: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        manager = BrowserManager(browser_config, logger)
        assert manager.is_initialized is False
        await manager.initialize()
        assert manager.is_initialized is True
        mock_async_pw.return_value.start.assert_awaited_once()

    @patch("app.scraping.browser.async_playwright")
    async def test_initialize_idempotent(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        manager = BrowserManager(browser_config)
        await manager.initialize()
        await manager.initialize()
        assert mock_async_pw.return_value.start.call_count == 1

    @patch("app.scraping.browser.async_playwright")
    async def test_create_browser_before_initialize_raises(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
    ) -> None:
        manager = BrowserManager(browser_config)
        with pytest.raises(BrowserError, match="Playwright not initialized"):
            await manager.create_browser()

    @patch("app.scraping.browser.async_playwright")
    async def test_create_browser_success(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type

        manager = BrowserManager(browser_config)
        await manager.initialize()
        browser = await manager.create_browser()

        assert browser is mock_browser
        assert manager.is_browser_running is True
        mock_browser_type.launch.assert_awaited_once_with(
            headless=True,
            slow_mo=0,
        )

    @patch("app.scraping.browser.async_playwright")
    async def test_create_browser_with_proxy(
        self,
        mock_async_pw: MagicMock,
        logger: CollectorLoggerProtocol,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
    ) -> None:
        config = BrowserConfig(
            headless=True,
            proxy_url="http://proxy:8080",
        )
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type

        manager = BrowserManager(config, logger)
        await manager.initialize()
        await manager.create_browser()

        mock_browser_type.launch.assert_awaited_once_with(
            headless=True,
            slow_mo=50,
            proxy={"server": "http://proxy:8080"},
        )

    @patch("app.scraping.browser.async_playwright")
    async def test_create_browser_invalid_type(
        self,
        mock_async_pw: MagicMock,
        mock_playwright: MagicMock,
    ) -> None:
        config = BrowserConfig(browser_type="webkit")
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium = MagicMock()
        del mock_playwright.webkit

        manager = BrowserManager(config)
        await manager.initialize()
        with pytest.raises(BrowserError, match="Unsupported browser type"):
            await manager.create_browser()

    @patch("app.scraping.browser.async_playwright")
    async def test_create_browser_launch_failure(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(side_effect=Exception("Launch failed"))
        mock_playwright.chromium = mock_browser_type

        manager = BrowserManager(browser_config)
        await manager.initialize()
        with pytest.raises(BrowserError, match="Failed to launch"):
            await manager.create_browser()

    @patch("app.scraping.browser.async_playwright")
    async def test_close_browser(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type

        manager = BrowserManager(browser_config)
        await manager.initialize()
        await manager.create_browser()
        assert manager.is_browser_running is True

        await manager.close_browser()
        assert manager.is_browser_running is False
        mock_browser.close.assert_awaited_once()

    @patch("app.scraping.browser.async_playwright")
    async def test_close_browser_idempotent(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        manager = BrowserManager(browser_config)
        await manager.initialize()
        await manager.close_browser()
        await manager.close_browser()

    @patch("app.scraping.browser.async_playwright")
    async def test_cleanup(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type

        manager = BrowserManager(browser_config)
        await manager.initialize()
        await manager.create_browser()
        await manager.cleanup()

        assert manager.is_initialized is False
        assert manager.is_browser_running is False
        mock_browser.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()

    @patch("app.scraping.browser.async_playwright")
    async def test_cleanup_idempotent(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        manager = BrowserManager(browser_config)
        await manager.initialize()
        await manager.cleanup()
        await manager.cleanup()

    @patch("app.scraping.browser.async_playwright")
    async def test_initialize_failure(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(
            side_effect=Exception("PW start failed"),
        )
        manager = BrowserManager(browser_config)
        with pytest.raises(BrowserError, match="Failed to start Playwright"):
            await manager.initialize()

    @patch("app.scraping.browser.async_playwright")
    async def test_logger_called(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        logger: CollectorLoggerProtocol,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type

        manager = BrowserManager(browser_config, logger)
        await manager.initialize()
        logger.info.assert_called_with(
            "Playwright started",
            browser_type="chromium",
        )


# ---------------------------------------------------------------------------
# Test ContextManager
# ---------------------------------------------------------------------------

class TestContextManager:
    async def test_create_context(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager = ContextManager(browser_config)
        context = await manager.create_context(mock_browser)
        assert context is mock_context
        assert manager.context_count == 1

    async def test_create_context_with_headers(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager = ContextManager(browser_config)
        context = await manager.create_context(
            mock_browser,
            extra_headers={"X-Custom": "test"},
        )
        context.set_extra_http_headers.assert_awaited_once_with(
            {"X-Custom": "test"},
        )

    async def test_create_context_failure(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(
            side_effect=Exception("Context error"),
        )
        manager = ContextManager(browser_config)
        with pytest.raises(BrowserError, match="Failed to create browser context"):
            await manager.create_context(mock_browser)

    async def test_close_single_context(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager = ContextManager(browser_config)
        ctx = await manager.create_context(mock_browser)
        assert manager.context_count == 1

        await manager.close_context(ctx)
        assert manager.context_count == 0
        mock_context.close.assert_awaited_once()

    async def test_close_all_contexts(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager = ContextManager(browser_config)
        await manager.create_context(mock_browser)
        await manager.create_context(mock_browser)
        assert manager.context_count == 2

        await manager.close_context()
        assert manager.context_count == 0

    async def test_cleanup(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager = ContextManager(browser_config)
        await manager.create_context(mock_browser)
        await manager.cleanup()
        assert manager.context_count == 0

    async def test_cleanup_idempotent(
        self,
        browser_config: BrowserConfig,
    ) -> None:
        manager = ContextManager(browser_config)
        await manager.cleanup()
        await manager.cleanup()

    async def test_contexts_property(
        self,
        browser_config: BrowserConfig,
        mock_browser: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        manager = ContextManager(browser_config)
        await manager.create_context(mock_browser)
        assert len(manager.contexts) == 1
        assert manager.contexts[0] is mock_context


# ---------------------------------------------------------------------------
# Test PageManager
# ---------------------------------------------------------------------------

class TestPageManager:
    async def test_create_page(
        self,
        browser_config: BrowserConfig,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager = PageManager(browser_config)
        page = await manager.create_page(mock_context)
        assert page is mock_page
        assert manager.page_count == 1

    async def test_create_page_failure(
        self,
        browser_config: BrowserConfig,
        mock_context: MagicMock,
    ) -> None:
        mock_context.new_page = AsyncMock(side_effect=Exception("Page error"))
        manager = PageManager(browser_config)
        with pytest.raises(NavigationError, match="Failed to create page"):
            await manager.create_page(mock_context)

    async def test_goto(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        manager = PageManager(browser_config)
        options = NavigationOptions(url="https://example.com")
        result = await manager.goto(mock_page, options)

        assert result is mock_page
        mock_page.goto.assert_awaited_once_with(
            url="https://example.com",
            wait_until="load",
            timeout=5000,
        )

    async def test_goto_http_error(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status = 404
        mock_page.goto = AsyncMock(return_value=mock_response)

        manager = PageManager(browser_config)
        options = NavigationOptions(url="https://example.com/notfound")
        with pytest.raises(NavigationError, match="HTTP 404"):
            await manager.goto(mock_page, options)

    async def test_goto_timeout(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        mock_page.goto = AsyncMock(
            side_effect=PlaywrightTimeout("Navigation timed out"),
        )

        manager = PageManager(browser_config)
        options = NavigationOptions(url="https://example.com")
        with pytest.raises(NavigationError, match="Navigation timed out"):
            await manager.goto(mock_page, options)

    async def test_goto_with_selector(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        manager = PageManager(browser_config)
        options = NavigationOptions(
            url="https://example.com",
            wait_for_selector=".content",
            wait_for_selector_timeout_ms=3000,
        )
        await manager.goto(mock_page, options)
        mock_page.wait_for_selector.assert_awaited_once_with(
            selector=".content",
            timeout=3000,
        )

    async def test_goto_selector_timeout(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.wait_for_selector = AsyncMock(
            side_effect=PlaywrightTimeout("Selector not found"),
        )

        manager = PageManager(browser_config)
        options = NavigationOptions(
            url="https://example.com",
            wait_for_selector=".missing",
        )
        with pytest.raises(NavigationError, match="not found"):
            await manager.goto(mock_page, options)

    async def test_reload(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.reload(mock_page)
        mock_page.reload.assert_awaited_once()

    async def test_reload_failure(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        mock_page.reload = AsyncMock(side_effect=Exception("Reload failed"))
        manager = PageManager(browser_config)
        with pytest.raises(NavigationError, match="Page reload failed"):
            await manager.reload(mock_page)

    async def test_wait_for_selector(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        result = await manager.wait_for_selector(mock_page, ".my-element")
        mock_page.wait_for_selector.assert_awaited_once_with(
            selector=".my-element",
            timeout=5000,
        )

    async def test_wait_for_load_state(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.wait_for_load_state(mock_page, "networkidle")
        mock_page.wait_for_load_state.assert_awaited_once_with(
            state="networkidle",
            timeout=5000,
        )

    async def test_wait_for_network_idle(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.wait_for_network_idle(mock_page)
        mock_page.wait_for_load_state.assert_awaited_once_with(
            state="networkidle",
            timeout=5000,
        )

    async def test_get_html(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        html = await manager.get_html(mock_page)
        assert html == "<html></html>"

    async def test_get_title(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        title = await manager.get_title(mock_page)
        assert title == "Test Page"

    async def test_get_url(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        url = await manager.get_url(mock_page)
        assert url == "https://example.com"

    async def test_scroll_to_bottom(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.scroll_to_bottom(mock_page)
        mock_page.evaluate.assert_awaited_once_with(
            "window.scrollTo(0, document.body.scrollHeight)",
        )

    async def test_scroll_to_element(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.scroll_to_element(mock_page, "#footer")
        mock_page.evaluate.assert_awaited_once()

    async def test_take_screenshot(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        result = await manager.take_screenshot(mock_page)
        assert result == b"fake-png"
        mock_page.screenshot.assert_awaited_once_with(full_page=True)

    async def test_take_screenshot_with_path(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        result = await manager.take_screenshot(mock_page, path="/tmp/shot.png")
        mock_page.screenshot.assert_awaited_once_with(
            full_page=True,
            path="/tmp/shot.png",
        )

    async def test_close_page(
        self,
        browser_config: BrowserConfig,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager = PageManager(browser_config)
        page = await manager.create_page(mock_context)
        assert manager.page_count == 1

        await manager.close_page(page)
        assert manager.page_count == 0
        mock_page.close.assert_awaited_once()

    async def test_close_page_idempotent(
        self,
        browser_config: BrowserConfig,
        mock_page: MagicMock,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.close_page(mock_page)
        await manager.close_page(mock_page)

    async def test_cleanup(
        self,
        browser_config: BrowserConfig,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager = PageManager(browser_config)
        await manager.create_page(mock_context)
        await manager.create_page(mock_context)
        assert manager.page_count == 2

        await manager.cleanup()
        assert manager.page_count == 0

    async def test_cleanup_idempotent(
        self,
        browser_config: BrowserConfig,
    ) -> None:
        manager = PageManager(browser_config)
        await manager.cleanup()
        await manager.cleanup()

    async def test_pages_property(
        self,
        browser_config: BrowserConfig,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager = PageManager(browser_config)
        await manager.create_page(mock_context)
        assert len(manager.pages) == 1
        assert manager.pages[0] is mock_page


# ---------------------------------------------------------------------------
# Test BrowserSession (DI-ready facade)
# ---------------------------------------------------------------------------

class TestBrowserSession:
    @patch("app.scraping.browser.async_playwright")
    async def test_start(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        session_config: SessionConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        session = BrowserSession(browser_config, session_config)
        assert session.is_started is False

        await session.start()
        assert session.is_started is True
        assert session.browser is mock_browser
        assert session.context is mock_context
        assert session.current_page is mock_page

    @patch("app.scraping.browser.async_playwright")
    async def test_navigate(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        session_config: SessionConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        session = BrowserSession(browser_config, session_config)
        await session.start()
        result = await session.navigate("https://example.com")

        assert result is mock_page
        mock_page.goto.assert_awaited()

    @patch("app.scraping.browser.async_playwright")
    async def test_navigate_without_start_raises(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
    ) -> None:
        session = BrowserSession(browser_config)
        with pytest.raises(BrowserError, match="Session not started"):
            await session.navigate("https://example.com")

    @patch("app.scraping.browser.async_playwright")
    async def test_stop(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        session_config: SessionConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        session = BrowserSession(browser_config, session_config)
        await session.start()
        assert session.is_started is True

        await session.stop()
        assert session.is_started is False
        assert session.current_page is None
        assert session.context is None

    @patch("app.scraping.browser.async_playwright")
    async def test_stop_idempotent(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
    ) -> None:
        session = BrowserSession(browser_config)
        await session.stop()
        await session.stop()

    @patch("app.scraping.browser.async_playwright")
    async def test_goto_delegation(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        session = BrowserSession(browser_config)
        await session.start()

        options = NavigationOptions(url="https://example.com/page2")
        result = await session.goto(mock_page, options)
        assert result is mock_page

    @patch("app.scraping.browser.async_playwright")
    async def test_create_and_switch_page(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        session = BrowserSession(browser_config)
        await session.start()

        second_page = MagicMock()
        mock_context.new_page = AsyncMock(return_value=second_page)
        new_page = await session.create_page()
        assert new_page is second_page

        session.switch_page(new_page)
        assert session.current_page is new_page

    @patch("app.scraping.browser.async_playwright")
    async def test_close_page(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        session_config: SessionConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        session = BrowserSession(browser_config, session_config)
        await session.start()
        await session.close_page()
        assert session.current_page is None
        mock_page.close.assert_awaited_once()

    @patch("app.scraping.browser.async_playwright")
    async def test_page_utilities(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
        mock_playwright: MagicMock,
        mock_browser: MagicMock,
        mock_context: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_browser_type = MagicMock()
        mock_browser_type.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.chromium = mock_browser_type
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.title = AsyncMock(return_value="Test")
        mock_page.content = AsyncMock(return_value="<html/>")

        session = BrowserSession(browser_config)
        await session.start()

        assert await session.get_title() == "Test"
        assert await session.get_html() == "<html/>"
        assert await session.get_url() == "https://example.com"

    @patch("app.scraping.browser.async_playwright")
    async def test_page_utilities_without_page(
        self,
        mock_async_pw: MagicMock,
        browser_config: BrowserConfig,
    ) -> None:
        session = BrowserSession(browser_config)
        with pytest.raises(BrowserError, match="No active page"):
            await session.get_title()


# ---------------------------------------------------------------------------
# Test ScrapingEngine
# ---------------------------------------------------------------------------

class TestScrapingEngine:
    def test_create_browser_config_defaults(self) -> None:
        engine = ScrapingEngine()
        config = engine.create_browser_config()
        assert isinstance(config, BrowserConfig)
        assert config.headless is True
        assert config.browser_type == "chromium"

    def test_create_session_config_defaults(self) -> None:
        engine = ScrapingEngine()
        config = engine.create_session_config()
        assert isinstance(config, SessionConfig)
        assert config.max_retries >= 0

    def test_create_session(self) -> None:
        engine = ScrapingEngine()
        session = engine.create_session()
        assert isinstance(session, BrowserSession)
        assert session.is_started is False

    def test_create_session_with_overrides(self) -> None:
        engine = ScrapingEngine()
        bc = BrowserConfig(headless=False, browser_type="firefox")
        sc = SessionConfig(max_retries=5)
        session = engine.create_session(
            browser_config=bc,
            session_config=sc,
        )
        assert session.browser_config.headless is False
        assert session.browser_config.browser_type == "firefox"
        assert session.session_config.max_retries == 5


# ---------------------------------------------------------------------------
# Test Exceptions
# ---------------------------------------------------------------------------

class TestBrowserError:
    def test_basic(self) -> None:
        err = BrowserError("Browser crashed")
        assert str(err) == "Browser crashed"
        assert err.browser_type is None

    def test_with_browser_type(self) -> None:
        err = BrowserError(
            "Failed to launch",
            browser_type="chromium",
        )
        assert err.browser_type == "chromium"

    def test_with_source_and_original(self) -> None:
        original = ValueError("inner")
        err = BrowserError(
            "Browser error",
            browser_type="firefox",
            source="test",
            original=original,
        )
        assert err.source == "test"
        assert err.original is original


class TestNavigationError:
    def test_basic(self) -> None:
        err = NavigationError("Navigation failed")
        assert str(err) == "Navigation failed"
        assert err.url is None

    def test_with_url_and_status(self) -> None:
        err = NavigationError(
            "404 Not Found",
            url="https://example.com/404",
            status_code=404,
        )
        assert err.url == "https://example.com/404"
        assert err.status_code == 404

    def test_exception_hierarchy(self) -> None:
        from app.collectors.exceptions import CollectorError

        err = NavigationError("test")
        assert isinstance(err, CollectorError)


# ---------------------------------------------------------------------------
# Test Dependency Injection pattern
# ---------------------------------------------------------------------------

class TestDependencyInjection:
    """Test that the DI pattern works: a mock collector receiving a BrowserSession."""

    async def test_collector_receives_session(self) -> None:
        config = BrowserConfig()
        session = BrowserSession(config)

        class MockCollector:
            def __init__(
                self,
                browser_session: BrowserSession,
            ) -> None:
                self.browser_session = browser_session

        collector = MockCollector(browser_session=session)
        assert collector.browser_session is session
        assert collector.browser_session.is_started is False

    async def test_session_di_with_engine(self) -> None:
        engine = ScrapingEngine()

        class MockPlugin:
            def __init__(self, session: BrowserSession) -> None:
                self.session = session

        session = engine.create_session()
        plugin = MockPlugin(session=session)
        assert isinstance(plugin.session, BrowserSession)
