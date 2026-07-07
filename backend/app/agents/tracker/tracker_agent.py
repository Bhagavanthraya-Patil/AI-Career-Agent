from __future__ import annotations

from typing import Any, Optional

from app.agents.tracker.application_tracker import ApplicationTracker
from app.agents.tracker.exceptions import CleanupError, TrackerError
from app.agents.tracker.tracker_models import (
    ApplicationStatusData,
    ApplicationTimeline,
    ApplyAgentIntegration,
    HistoryEntry,
    StatusChangeEvent,
    TrackerConfig,
    TrackerMetrics,
)
from app.collectors.logging import CollectorLoggerProtocol


class TrackerAgent:
    """Primary orchestrator for the Application Tracker.

    Manages the complete lifecycle of application tracking:
    initialize, track, update, record, query, metrics, and cleanup.

    Usage::

        agent = TrackerAgent(session=db_session, logger=logger)
        await agent.initialize()
        app = await agent.track_application(job_id="...")
        app = await agent.update_status(app_id, "applied")
        metrics = await agent.get_metrics()
        await agent.cleanup()
    """

    def __init__(
        self,
        session: Any,
        config: Optional[TrackerConfig] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._session = session
        self._config = config or TrackerConfig()
        self._logger = logger
        self._initialized = False
        self._app_tracker: Optional[ApplicationTracker] = None

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def initialize(self) -> None:
        """Initialize the tracker agent.

        Creates the underlying ApplicationTracker instance and
        verifies the database session is operational.
        """
        if self._initialized:
            return

        try:
            from sqlalchemy import text

            await self._session.execute(text("SELECT 1"))
            self._app_tracker = ApplicationTracker(
                session=self._session,
                config=self._config,
                logger=self._logger,
            )
            self._initialized = True
            self._log("TrackerAgent initialized")
        except Exception as exc:
            raise TrackerError(
                message=f"Failed to initialize TrackerAgent: {exc}",
                step="initialize",
                original=exc,
            ) from exc

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._app_tracker is None:
            raise TrackerError(
                message="TrackerAgent not initialized. Call initialize() first.",
                step="lifecycle",
            )

    async def track_application(
        self,
        job_id: str,
        status: str = "draft",
        apply_url: Optional[str] = None,
        resume_version: Optional[str] = None,
        cover_letter_version: Optional[str] = None,
        notes: Optional[str] = None,
        browser_session_id: Optional[str] = None,
    ) -> ApplicationStatusData:
        """Track a new application.

        Args:
            job_id: Job UUID to track.
            status: Initial status.
            apply_url: Application URL.
            resume_version: Resume version.
            cover_letter_version: Cover letter version.
            notes: Optional notes.
            browser_session_id: Browser session ID.

        Returns:
            ApplicationStatusData for the new application.
        """
        self._ensure_initialized()
        return await self._app_tracker.track(
            job_id=job_id,
            status=status,
            apply_url=apply_url,
            resume_version=resume_version,
            cover_letter_version=cover_letter_version,
            notes=notes,
            browser_session_id=browser_session_id,
        )

    async def update_status(
        self,
        application_id: str,
        new_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ApplicationStatusData:
        """Update application status.

        Args:
            application_id: Application UUID.
            new_status: Target status.
            changed_by: Who/what changed it.
            reason: Optional reason.
            metadata: Optional metadata.

        Returns:
            Updated ApplicationStatusData.
        """
        self._ensure_initialized()
        return await self._app_tracker.update_status(
            application_id=application_id,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
            metadata=metadata,
        )

    async def record_event(
        self,
        application_id: str,
        event: StatusChangeEvent,
    ) -> HistoryEntry:
        """Record a status change event.

        Args:
            application_id: Application UUID.
            event: The event to record.

        Returns:
            The recorded HistoryEntry.
        """
        self._ensure_initialized()
        return await self._app_tracker.record_event(
            application_id=application_id,
            event=event,
        )

    async def record_apply_result(
        self,
        application_id: str,
        result: ApplyAgentIntegration,
    ) -> ApplicationStatusData:
        """Record an Apply Agent result for an application.

        Args:
            application_id: Application UUID.
            result: Apply Agent integration data.

        Returns:
            Updated ApplicationStatusData.
        """
        self._ensure_initialized()
        return await self._app_tracker.record_apply_result(
            application_id=application_id,
            result=result,
        )

    async def get_history(
        self,
        application_id: str,
    ) -> list[HistoryEntry]:
        """Get status change history for an application.

        Args:
            application_id: Application UUID.

        Returns:
            List of HistoryEntry ordered by creation time.
        """
        self._ensure_initialized()
        return await self._app_tracker.get_history(application_id)

    async def get_timeline(
        self,
        application_id: str,
    ) -> ApplicationTimeline:
        """Get the full timeline for an application.

        Args:
            application_id: Application UUID.

        Returns:
            ApplicationTimeline with all events.
        """
        self._ensure_initialized()
        return await self._app_tracker.get_timeline(application_id)

    async def get_metrics(self) -> TrackerMetrics:
        """Compute aggregate metrics across all applications.

        Returns:
            TrackerMetrics with counts, rates, and breakdowns.
        """
        self._ensure_initialized()
        return await self._app_tracker.compute_metrics()

    async def get_application(
        self,
        application_id: str,
    ) -> ApplicationStatusData:
        """Get application details.

        Args:
            application_id: Application UUID.

        Returns:
            ApplicationStatusData.
        """
        self._ensure_initialized()
        return await self._app_tracker.get_application(application_id)

    async def find_by_job(
        self,
        job_id: str,
    ) -> Optional[ApplicationStatusData]:
        """Find an application by job ID.

        Returns None if not tracked.
        """
        self._ensure_initialized()
        return await self._app_tracker.find_by_job(job_id)

    async def list_applications(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ApplicationStatusData]:
        """List all tracked applications."""
        self._ensure_initialized()
        return await self._app_tracker.list_applications(
            status=status,
            limit=limit,
            offset=offset,
        )

    async def delete_application(
        self,
        application_id: str,
    ) -> None:
        """Soft-delete an application."""
        self._ensure_initialized()
        await self._app_tracker.delete_application(application_id)

    async def cleanup(self) -> None:
        """Clean up resources and inactive applications.

        Closes the session if configured for auto-cleanup.
        """
        if not self._initialized:
            return
        try:
            if self._config.auto_cleanup:
                count = await self._app_tracker.cleanup_inactive()
                self._log(f"Cleaned up {count} inactive applications")

            self._initialized = False
            self._app_tracker = None
            self._log("TrackerAgent cleaned up")
        except Exception as exc:
            raise CleanupError(
                message=f"Cleanup failed: {exc}",
                step="cleanup",
                original=exc,
            ) from exc
