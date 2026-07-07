# Playwright Scraping Engine

A reusable browser automation engine for the AI Career Agent. Future Playwright-based collectors request a `BrowserSession` without managing Playwright directly.

## Architecture

```
scraping/
├── __init__.py       # Package exports
├── exceptions.py     # BrowserError, NavigationError
├── models.py         # BrowserConfig, SessionConfig, NavigationOptions
├── browser.py        # BrowserManager - low-level browser lifecycle
├── context.py        # ContextManager - browser context management
├── page.py           # PageManager - page navigation utilities
├── session.py        # BrowserSession - DI-ready facade for collectors
├── engine.py         # ScrapingEngine - top-level orchestrator
└── README.md         # This file
```

### Layer Diagram

```
Collector (via DI)          Collector (via DI)
        |                          |
        v                          |
  BrowserSession                   |
   /    |    \                     |
  /     |     \                    v
BM    CM     PM              ScrapingEngine
 |     |      |                    |
 v     v      v                    |
 Playwright  (async API)    CollectorConfigProvider
                                    |
                              settings.job_collection
                              settings.playwright
```

- **BrowserManager (BM):** Playwright process start/stop, browser launch/close.
- **ContextManager (CM):** Browser contexts (isolated sessions with cookies/cache).
- **PageManager (PM):** Page CRUD, navigation, scroll, screenshots, HTML extraction.
- **BrowserSession:** Facade combining BM + CM + PM with retry logic.
- **ScrapingEngine:** Reads centralized config and creates `BrowserSession` instances.

## Browser Lifecycle

```
ScrapingEngine.create_session()
          |
          v
   BrowserSession.start()
     - BrowserManager.initialize()     # async_playwright().start()
     - BrowserManager.create_browser() # chromium/firefox/webkit.launch()
     - ContextManager.create_context() # browser.new_context()
     - PageManager.create_page()       # context.new_page()
          |
          v
   BrowserSession.navigate(url)
     - PageManager.goto()
     - (retry on failure)
          |
          v
   BrowserSession.stop()
     - PageManager.cleanup()           # close all pages
     - ContextManager.cleanup()        # close all contexts
     - BrowserManager.cleanup()        # close browser, stop Playwright
```

`stop()` is safe to call multiple times (idempotent).

## Configuration

All values come from the centralized `settings.playwright` and `settings.job_collection` namespaces via `CollectorConfigProvider`. No hardcoded values.

| Model Field | Config Source | Env Variable |
|---|---|---|
| `headless` | `settings.playwright.headless` | `PLAYWRIGHT_HEADLESS` |
| `browser_type` | `settings.playwright.browser_type` | `PLAYWRIGHT_BROWSER_TYPE` |
| `timeout_ms` | `settings.playwright.timeout_ms` | `PLAYWRIGHT_TIMEOUT_MS` |
| `slow_mo_ms` | `settings.playwright.slow_mo_ms` | `PLAYWRIGHT_SLOW_MO_MS` |
| `viewport_width` | `settings.playwright.viewport_width` | `PLAYWRIGHT_VIEWPORT_WIDTH` |
| `viewport_height` | `settings.playwright.viewport_height` | `PLAYWRIGHT_VIEWPORT_HEIGHT` |
| `user_agent` | `settings.playwright.user_agent` | `PLAYWRIGHT_USER_AGENT` |
| `max_retries` | `settings.job_collection.max_retries` | `JOB_COLLECTION_MAX_RETRIES` |
| `retry_backoff` | `settings.job_collection.retry_backoff_factor` | `JOB_COLLECTION_RETRY_BACKOFF_FACTOR` |

## Extension Points

### Custom BrowserConfig
```python
class MyScrapingEngine(ScrapingEngine):
    def create_browser_config(self) -> BrowserConfig:
        return BrowserConfig(
            headless=False,
            browser_type="firefox",
            timeout_ms=60000,
        )
```

### Custom SessionConfig
```python
class MyScrapingEngine(ScrapingEngine):
    def create_session_config(self) -> SessionConfig:
        return SessionConfig(
            max_retries=5,
            navigation_timeout_s=60.0,
        )
```

## Example Usage

### Basic
```python
from app.scraping import ScrapingEngine

engine = ScrapingEngine()
session = engine.create_session()

await session.start()
page = await session.navigate("https://example.com")
html = await session.get_html()
await session.stop()
```

### With custom options
```python
from app.scraping import NavigationOptions

opts = NavigationOptions(
    url="https://example.com/jobs",
    wait_until="networkidle",
    scroll_to_bottom=True,
    take_screenshot=True,
)
page = await session.navigate(url, options=opts)
```

### Dependency injection in a collector
```python
from app.collectors.base import BaseCollector
from app.scraping import BrowserSession

class MyCollector(BaseCollector):
    def __init__(self, config, logger, browser_session: BrowserSession):
        super().__init__(config, logger)
        self._session = browser_session

    async def collect(self, query):
        await self._session.start()
        page = await self._session.navigate("https://...")
        html = await self._session.get_html()
        # ... parse HTML (in a real collector) ...
        await self._session.stop()
        return CollectorResult(...)
```

## Retry Integration

`BrowserSession.navigate()` uses `RetryStrategy` from the collector framework internally. Configuration is read from `SessionConfig`. Retryable exceptions include `NetworkError` and `NavigationError` with exponential backoff.

## Error Handling

| Exception | When Raised |
|---|---|
| `BrowserError` | Playwright start/stop failure, browser launch failure, missing browser type |
| `NavigationError` | Page creation failure, navigation timeout, HTTP 4xx/5xx, selector timeout |
| `NetworkError` | Underlying network failure (from retry framework) |

All exceptions extend `CollectorError` for consistency with the collector framework.

## Resource Cleanup

Every `BrowserSession.start()` must be paired with `BrowserSession.stop()`. The engine guarantees:

1. `stop()` closes all pages, contexts, browser, and Playwright process.
2. All `cleanup()` methods are idempotent (safe to call multiple times).
3. Python's `asyncio` cancellation propagates correctly through `RetryStrategy`.

## Managed Utils via BrowserSession

| Method | Description |
|---|---|
| `start()` | Playwright → browser → context → page |
| `navigate(url)` | goto + retry + optional scroll/screenshot |
| `goto(page, opts)` | Low-level goto for multi-page use |
| `reload()` | Reload current page |
| `create_page()` | New page in current context |
| `switch_page(page)` | Change active page |
| `close_page(page)` | Close a page |
| `stop()` | Release all resources |
| `wait_for_selector(sel)` | Wait for CSS selector |
| `wait_for_load_state(st)` | Wait for load state |
| `wait_for_network_idle()` | Wait for network quiet |
| `scroll_to_bottom()` | Scroll full height |
| `scroll_to_element(sel)` | Scroll to element |
| `take_screenshot(path)` | Screenshot (full page) |
| `get_html()` | Page HTML |
| `get_title()` | Page title |
| `get_url()` | Current URL |

## Multiple Browser Support

Set `browser_type` in `BrowserConfig` to one of: `"chromium"`, `"firefox"`, `"webkit"`. All three are supported through Playwright's unified API. The engine resolves the correct launcher via `getattr(playwright, browser_type)`.
