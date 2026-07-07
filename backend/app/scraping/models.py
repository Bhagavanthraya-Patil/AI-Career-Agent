from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class BrowserConfig(BaseModel):
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode",
    )
    browser_type: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium",
        description="Browser engine to use",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        description="Default timeout for Playwright operations in milliseconds",
    )
    slow_mo_ms: int = Field(
        default=50,
        ge=0,
        description="Slow down operations by this many milliseconds",
    )
    viewport_width: int = Field(
        default=1920,
        ge=320,
        description="Browser viewport width in pixels",
    )
    viewport_height: int = Field(
        default=1080,
        ge=240,
        description="Browser viewport height in pixels",
    )
    user_agent: str = Field(
        default="",
        description="Custom user agent string (empty = browser default)",
    )
    proxy_url: str = Field(
        default="",
        description="Optional proxy URL (e.g. http://proxy:8080)",
    )
    downloads_path: str = Field(
        default="",
        description="Path for downloaded files (empty = system default)",
    )
    screenshots_path: str = Field(
        default="",
        description="Path for saving screenshots",
    )
    tracing_path: str = Field(
        default="",
        description="Path for Playwright trace files (empty = disabled)",
    )
    max_pages: int = Field(
        default=4,
        ge=1,
        le=50,
        description="Maximum number of concurrent pages",
    )
    rate_limit_ms: int = Field(
        default=2000,
        ge=0,
        description="Minimum delay between navigations in milliseconds",
    )


class SessionConfig(BaseModel):
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for navigation",
    )
    retry_base_delay_s: float = Field(
        default=1.0,
        ge=0.1,
        description="Base delay in seconds for exponential backoff",
    )
    retry_max_delay_s: float = Field(
        default=60.0,
        ge=1.0,
        description="Maximum delay in seconds between retries",
    )
    retry_backoff: float = Field(
        default=2.0,
        ge=1.0,
        description="Exponential backoff multiplier",
    )
    navigation_timeout_s: float = Field(
        default=30.0,
        ge=1.0,
        description="Per-navigation timeout in seconds",
    )


class NavigationOptions(BaseModel):
    url: str = Field(
        description="Target URL to navigate to",
    )
    wait_until: Literal[
        "load", "domcontentloaded", "networkidle", "commit"
    ] = Field(
        default="load",
        description="When to consider navigation succeeded",
    )
    timeout_ms: Optional[int] = Field(
        default=None,
        description="Override the default timeout for this navigation",
    )
    retry_on_failure: bool = Field(
        default=True,
        description="Whether to retry on navigation failure",
    )
    scroll_to_bottom: bool = Field(
        default=False,
        description="Scroll to bottom after page loads",
    )
    wait_for_selector: Optional[str] = Field(
        default=None,
        description="CSS selector to wait for after navigation",
    )
    wait_for_selector_timeout_ms: Optional[int] = Field(
        default=None,
        description="Timeout for the selector wait",
    )
    take_screenshot: bool = Field(
        default=False,
        description="Take a screenshot after navigation",
    )
    extra_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Extra HTTP headers for this navigation",
    )
