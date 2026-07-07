from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from . import BaseConfig


class PlaywrightSettings(BaseConfig):
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
        description="Default timeout for Playwright operations (ms)",
    )
    slow_mo_ms: int = Field(
        default=50,
        description="Slow down operations by this many ms (human mimicry)",
    )
    viewport_width: int = Field(
        default=1920,
        description="Browser viewport width in pixels",
    )
    viewport_height: int = Field(
        default=1080,
        description="Browser viewport height in pixels",
    )
    user_data_dir: str = Field(
        default="",
        description="Path to browser user data directory (persistent sessions)",
    )
    max_pages: int = Field(
        default=4,
        description="Maximum concurrent browser pages in pool",
    )
    rate_limit_ms: int = Field(
        default=2000,
        description="Minimum delay between page navigations (ms)",
    )
    retry_count: int = Field(
        default=3,
        description="Number of retries on failed page loads",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff multiplier for retries",
    )
    stealth_mode: bool = Field(
        default=True,
        description="Enable anti-detection stealth measures",
    )
    user_agent: str = Field(
        default="",
        description="Custom user agent string (empty = browser default)",
    )
