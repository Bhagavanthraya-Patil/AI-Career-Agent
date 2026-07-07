from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.agents.tracker.exceptions import (
    ApplicationNotFoundError,
    DuplicateApplicationError,
    InvalidStatusTransitionError,
    TrackerError,
)
from app.agents.tracker.history_manager import HistoryManager
from app.agents.tracker.metrics import Metrics
from app.agents.tracker.status_manager import StatusManager
from app.agents.tracker.timeline import Timeline
from app.agents.tracker.tracker_models import (
    ApplicationStatusData,
    ApplicationTimeline,
    ApplyAgentIntegration,
    HistoryEntry,
    StatusChangeEvent,
    TrackerConfig,
    TrackerMetrics,
)
from app.agents.tracker.tracker_repository import ApplicationRepository
from app.collectors.logging import CollectorLoggerProtocol


class ApplicationTracker:
    """Core service for tracking job application lifecycles.

    Orchestrates the repository, status manager, history manager,
    metrics, and timeline components into a unified tracking API.

    Usage::

        tracker = ApplicationTracker(session=db_session, logger=logger)
        app = await tracker.track(job_id="...")
        app = await tracker.update_status(app_id, "applied", ...)
        metrics = await tracker.compute_metrics()
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

        self._repository = ApplicationRepository(
            session=session,
            logger=logger,
        )
        self._history_mgr = HistoryManager(
            max_entries=self._config.max_history_entries,
        )
        self._metrics = Metrics()
        self._timeline = Timeline()

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    # --- Lifecycle ---

    async def track(
        self,
        job_id: str,
        status: str = "draft",
        apply_url: Optional[str] = None,
        resume_version: Optional[str] = None,
        cover_letter_version: Optional[str] = None,
        notes: Optional[str] = None,
        browser_session_id: Optional[str] = None,
    ) -> ApplicationStatusData:
        """Start tracking a new application for a job.

        Args:
            job_id: UUID of the job.
            status: Initial status (default: "draft").
            apply_url: Direct application URL.
            resume_version: Resume version identifier.
            cover_letter_version: Cover letter version identifier.
            notes: Optional notes.
            browser_session_id: Browser session ID.

        Returns:
            ApplicationStatusData for the new application.

        Raises:
            DuplicateApplicationError: If already tracked.
            InvalidStatusError: If the initial status is invalid.
        """
        try:
            app = await self._repository.create_application(
                job_id=job_id,
                status=status,
                apply_url=apply_url,
                resume_version=resume_version,
                cover_letter_version=cover_letter_version,
                notes=notes,
                browser_session_id=browser_session_id,
            )

            self._log(f"Tracking application {app.id} for job {job_id}")

            if self._config.record_history:
                event = self._history_mgr.build_event(
                    application_id=str(app.id),
                    from_status=None,
                    to_status=status,
                    changed_by="system",
                    reason="Application tracking started",
                )
                await self._history_mgr.record_event(
                    self._session,
                    event,
                )

            return await self._repository.get_status_data(str(app.id))

        except TrackerError:
            raise
        except Exception as exc:
            raise TrackerError(
                message=f"Failed to track application: {exc}",
                step="track",
                original=exc,
            ) from exc

    async def update_status(
        self,
        application_id: str,
        new_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ApplicationStatusData:
        """Update the status of a tracked application.

        Args:
            application_id: Application UUID.
            new_status: Target status.
            changed_by: Who/what initiated the change.
            reason: Optional reason.
            metadata: Optional metadata.

        Returns:
            Updated ApplicationStatusData.

        Raises:
            ApplicationNotFoundError: If application not found.
            InvalidStatusTransitionError: If transition is invalid.
        """
        try:
            app = await self._repository.update_status(
                application_id=application_id,
                new_status=new_status,
                changed_by=changed_by,
                reason=reason,
                metadata=metadata,
            )

            self._log(
                f"Updated application {application_id} status to {new_status}",
            )
            return await self._repository.get_status_data(application_id)

        except TrackerError:
            raise
        except Exception as exc:
            raise TrackerError(
                message=f"Failed to update status: {exc}",
                step="update_status",
                original=exc,
            ) from exc

    async def record_event(
        self,
        application_id: str,
        event: StatusChangeEvent,
    ) -> HistoryEntry:
        """Record a custom status change event.

        Use this for external systems (e.g., Apply Agent) to record
        status changes they initiated.

        Args:
            application_id: Application UUID.
            event: The status change event.

        Returns:
            The recorded HistoryEntry.
        """
        return await self._history_mgr.record_event(self._session, event)

    async def record_apply_result(
        self,
        application_id: str,
        result: ApplyAgentIntegration,
    ) -> ApplicationStatusData:
        """Record the result of an Apply Agent run.

        Updates the application status and stores the result data.

        Args:
            application_id: Application UUID.
            result: ApplyAgentIntegration data.

        Returns:
            Updated ApplicationStatusData.
        """
        kwargs: dict[str, Any] = {}
        if result.confirmation_code:
            kwargs["confirmation_code"] = result.confirmation_code
        if result.screenshot_path:
            kwargs["screenshot_path"] = result.screenshot_path
        kwargs["apply_agent_result"] = {
            "success": result.success,
            "final_state": result.final_state,
            "errors": result.errors,
            "duration_seconds": result.duration_seconds,
            "state_history": result.state_history,
        }

        await self._repository.update_application(
            application_id,
            **kwargs,
        )

        status = "submitted" if result.success else "failed"
        await self.update_status(
            application_id=application_id,
            new_status=status,
            changed_by="agent:apply",
            reason=f"Apply Agent completed: {result.final_state or 'unknown'}",
        )

        return await self._repository.get_status_data(application_id)

    # --- Queries ---

    async def get_application(
        self,
        application_id: str,
    ) -> ApplicationStatusData:
        """Get application status data by ID."""
        return await self._repository.get_status_data(application_id)

    async def find_by_job(self, job_id: str) -> Optional[ApplicationStatusData]:
        """Find an application by job ID.

        Returns None if not tracked.
        """
        app = await self._repository.find_by_job(job_id)
        if app is None:
            return None
        return await self._repository.get_status_data(str(app.id))

    async def list_applications(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ApplicationStatusData]:
        """List all tracked applications with optional status filter."""
        apps = await self._repository.list_applications_with_relations(
            status=status,
            is_active=True,
            limit=limit,
            offset=offset,
        )
        return [
            ApplicationStatusData(
                application_id=str(a.id),
                job_id=str(a.job_id),
                job_title=a.job.title if a.job else "",
                company_name=a.job.company.name
                if a.job and a.job.company
                else "",
                status=a.status,
                resume_version=a.resume_version,
                cover_letter_version=a.cover_letter_version,
                apply_url=a.apply_url,
                confirmation_code=a.confirmation_code,
                screenshot_path=a.screenshot_path,
                browser_session_id=a.browser_session_id,
                notes=a.notes,
                rating=a.rating,
                offer_details=a.offer_details,
                rejection_reason=a.rejection_reason,
                interview_dates=a.interview_dates,
                applied_date=a.applied_date,
                is_active=a.is_active,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in apps
        ]

    async def get_history(
        self,
        application_id: str,
    ) -> list[HistoryEntry]:
        """Get the status change history for an application."""
        return await self._history_mgr.get_history(
            self._session,
            application_id,
        )

    async def get_timeline(
        self,
        application_id: str,
    ) -> ApplicationTimeline:
        """Get the full timeline for an application."""
        app = await self._repository.get_application_with_relations(
            application_id,
        )
        return await self._timeline.build(self._session, app)

    async def compute_metrics(self) -> TrackerMetrics:
        """Compute aggregate metrics over all active applications."""
        apps = await self._repository.get_all_for_metrics()
        return await self._metrics.compute(apps)

    async def count_by_status(self) -> dict[str, int]:
        """Count applications grouped by status."""
        metrics = await self.compute_metrics()
        return metrics.by_status

    async def get_status_counts(self) -> dict[str, int]:
        """Alias for count_by_status."""
        return await self.count_by_status()

    # --- Management ---

    async def update_application(
        self,
        application_id: str,
        **kwargs: Any,
    ) -> ApplicationStatusData:
        """Update arbitrary fields on an application."""
        await self._repository.update_application(
            application_id,
            **kwargs,
        )
        return await self._repository.get_status_data(application_id)

    async def delete_application(
        self,
        application_id: str,
    ) -> None:
        """Soft-delete an application."""
        await self._repository.delete_application(application_id)
        self._log(f"Deleted application {application_id}")

    async def hard_delete(self, application_id: str) -> None:
        """Permanently remove an application."""
        await self._repository.hard_delete_application(application_id)

    async def cleanup_inactive(self) -> int:
        """Clean up inactive applications (expired, cancelled).

        Returns the number of records affected.
        """
        apps = await self._repository.list_applications(
            is_active=True,
            limit=10000,
        )
        count = 0
        for app in apps:
            if StatusManager.is_terminal(app.status):
                await self._repository.delete_application(
                    str(app.id),
                )
                count += 1
        return count
