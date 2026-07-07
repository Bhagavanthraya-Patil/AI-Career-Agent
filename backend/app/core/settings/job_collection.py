from __future__ import annotations

from typing import Optional

from pydantic import Field

from . import BaseConfig


class JobCollectionSettings(BaseConfig):
    max_daily: int = Field(
        default=50,
        description="Maximum job listings to collect per day",
    )
    delay_between_requests_ms: int = Field(
        default=3000,
        description="Delay between consecutive scrape requests (ms)",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed scrapes",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff multiplier for retries",
    )
    sources_enabled: list[str] = Field(
        default=["linkedin", "indeed"],
        description="Comma-separated list of enabled job sources",
    )
    search_keywords: list[str] = Field(
        default=[],
        description="Default search keywords (comma-separated in env var)",
    )
    search_locations: list[str] = Field(
        default=[],
        description="Default search locations (comma-separated in env var)",
    )
    search_radius_km: int = Field(
        default=50,
        description="Search radius in kilometers",
    )
    dedup_window_hours: int = Field(
        default=72,
        description="Time window for duplicate detection (hours)",
    )
    max_pages_per_source: int = Field(
        default=5,
        description="Maximum pages to scrape per source per search",
    )
    respect_robots_txt: bool = Field(
        default=True,
        description="Respect robots.txt when scraping",
    )
    proxy_url: str = Field(
        default="",
        description="Optional proxy URL for scraping (empty = no proxy)",
    )
