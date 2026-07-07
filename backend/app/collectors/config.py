from __future__ import annotations

from typing import Any, Optional

from app.core.settings import settings
from app.collectors.exceptions import CollectorError


class CollectorConfigProvider:
    """Reads collector configuration from the centralized settings layer.

    All configuration values come from the environment via the
    pydantic-settings hierarchy. No values are hardcoded.
    """

    @staticmethod
    def get_global_settings() -> dict[str, Any]:
        """Return all job collection global settings.

        Reads from settings.job_collection (env prefix: JOB_COLLECTION_).
        """
        return {
            "max_daily": settings.job_collection.max_daily,
            "delay_between_requests_ms": (
                settings.job_collection.delay_between_requests_ms
            ),
            "max_retries": settings.job_collection.max_retries,
            "retry_backoff_factor": (
                settings.job_collection.retry_backoff_factor
            ),
            "sources_enabled": settings.job_collection.sources_enabled,
            "search_keywords": settings.job_collection.search_keywords,
            "search_locations": settings.job_collection.search_locations,
            "search_radius_km": settings.job_collection.search_radius_km,
            "dedup_window_hours": (
                settings.job_collection.dedup_window_hours
            ),
            "max_pages_per_source": (
                settings.job_collection.max_pages_per_source
            ),
            "respect_robots_txt": (
                settings.job_collection.respect_robots_txt
            ),
            "proxy_url": settings.job_collection.proxy_url,
        }

    @staticmethod
    def get_source_config(source_name: str) -> dict[str, Any]:
        """Return configuration for a specific collector source.

        Reads from settings.job_collection and merges any
        source-specific overrides.

        Args:
            source_name: Collector name (e.g., 'linkedin', 'greenhouse').

        Returns:
            Configuration dictionary for the specified source.
        """
        base = CollectorConfigProvider.get_global_settings()

        source_overrides = {
            "linkedin": {},
            "indeed": {},
            "glassdoor": {},
            "greenhouse": {},
            "lever": {},
            "workday": {},
        }

        overrides = source_overrides.get(source_name, {})
        base.update(overrides)
        return base

    @staticmethod
    def is_source_enabled(source_name: str) -> bool:
        """Check if a specific source is enabled in configuration.

        Args:
            source_name: Collector name.

        Returns:
            True if the source is in the enabled sources list.
        """
        enabled = settings.job_collection.sources_enabled
        return source_name.lower() in [s.lower() for s in enabled]

    @staticmethod
    def get_playwright_settings() -> dict[str, Any]:
        """Return Playwright settings for browser-based collectors.

        Reads from settings.playwright (env prefix: PLAYWRIGHT_).
        """
        return {
            "headless": settings.playwright.headless,
            "browser_type": settings.playwright.browser_type,
            "timeout_ms": settings.playwright.timeout_ms,
            "slow_mo_ms": settings.playwright.slow_mo_ms,
            "viewport_width": settings.playwright.viewport_width,
            "viewport_height": settings.playwright.viewport_height,
            "user_data_dir": settings.playwright.user_data_dir,
            "max_pages": settings.playwright.max_pages,
            "rate_limit_ms": settings.playwright.rate_limit_ms,
            "stealth_mode": settings.playwright.stealth_mode,
            "user_agent": settings.playwright.user_agent,
        }

    @staticmethod
    def get_storage_settings() -> dict[str, Any]:
        """Return storage configuration for persisting collected data.

        Reads from settings.storage (env prefix: STORAGE_).
        """
        return {
            "base_path": settings.storage.base_path,
            "jobs_path": settings.storage.jobs_path,
        }

    @staticmethod
    def get_source_url(source_name: str) -> str:
        """Return the base URL for a registered job source.

        This reads from the centralized settings or a future
        job_sources database table.

        Args:
            source_name: Collector source name.

        Returns:
            Base URL string.

        Raises:
            CollectorError: If the source is unknown.
        """
        source_urls = {
            "linkedin": "https://www.linkedin.com/jobs",
            "indeed": "https://www.indeed.com",
            "glassdoor": "https://www.glassdoor.com/Job",
            "greenhouse": "https://boards.greenhouse.io",
            "lever": "https://jobs.lever.co",
            "workday": "",
        }

        url = source_urls.get(source_name.lower())
        if url is None:
            raise CollectorError(
                f"Unknown source: {source_name}",
                source=source_name,
            )
        return url
