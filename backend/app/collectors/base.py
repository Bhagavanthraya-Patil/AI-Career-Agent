from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.collectors.models import CollectorQuery, CollectorResult, JobData
from app.collectors.logging import CollectorLoggerProtocol


class BaseCollector(ABC):
    """Abstract base class for all job collectors.

    Every job source collector (LinkedIn, Indeed, Greenhouse, etc.)
    must subclass this and implement all abstract methods.
    """

    def __init__(
        self,
        config: Any,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable collector name (e.g., 'linkedin', 'greenhouse')."""
        ...

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique source identifier matching the job_sources table."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Set up collector resources (browser, session, API client, etc.).

        Called once before collect(). Must set self._initialized = True
        on success.
        """
        ...

    @abstractmethod
    async def collect(self, query: CollectorQuery) -> CollectorResult:
        """Execute the collection against the job source.

        Args:
            query: Search parameters (keywords, location, filters).

        Returns:
            CollectorResult containing collected jobs and metadata.
        """
        ...

    @abstractmethod
    async def normalize(self, raw_data: Any) -> list[JobData]:
        """Convert raw source data into normalized JobData models.

        Args:
            raw_data: Unstructured data from the collect step.

        Returns:
            List of validated, normalized JobData objects.
        """
        ...

    @abstractmethod
    async def validate(self, jobs: list[JobData]) -> list[JobData]:
        """Validate a list of normalized JobData objects.

        Removes or flags entries that fail validation rules.

        Args:
            jobs: Normalized job data.

        Returns:
            Validated subset of job data.
        """
        ...

    @abstractmethod
    async def deduplicate(
        self,
        jobs: list[JobData],
        existing_source_ids: list[str],
    ) -> list[JobData]:
        """Remove jobs already present in the database.

        Args:
            jobs: Validated job data.
            existing_source_ids: List of source_job_id values already stored.

        Returns:
            Jobs that are new (not duplicates).
        """
        ...

    @abstractmethod
    async def save(self, jobs: list[JobData]) -> CollectorResult:
        """Persist collected and normalized jobs.

        Args:
            jobs: Final list of jobs to persist.

        Returns:
            CollectorResult with save statistics.
        """
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Release collector resources.

        Called after collect() completes or on failure.
        Must be safe to call multiple times.
        """
        ...

    async def execute(self, query: CollectorQuery) -> CollectorResult:
        """Full collection lifecycle as a single call.

        Calls initialize -> collect -> normalize -> validate
        -> deduplicate -> save -> cleanup in order.

        Args:
            query: Search parameters.

        Returns:
            CollectorResult from the save step.
        """
        try:
            await self.initialize()
            raw_result = await self.collect(query)
            normalized = await self.normalize(raw_result.raw_data)
            validated = await self.validate(normalized)
            deduped = await self.deduplicate(
                validated, raw_result.existing_source_ids
            )
            result = await self.save(deduped)
            return result
        finally:
            await self.cleanup()
