from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select, func

from app.agents.tracker.exceptions import MetricsComputationError
from app.agents.tracker.status_manager import StatusManager
from app.agents.tracker.tracker_models import TrackerMetrics


class Metrics:
    """Computes aggregate metrics from application data.

    Produces a TrackerMetrics dataclass with counts and rates
    for success, failure, interviews, offers, rejections, pending,
    and breakdowns by status, source, company, and date.

    Usage::

        metrics = Metrics()
        result = await metrics.compute(applications)
        print(result.success_rate)
    """

    async def compute(
        self,
        applications: list[Any],
    ) -> TrackerMetrics:
        """Compute metrics from a list of application records.

        Args:
            applications: List of Application ORM objects.

        Returns:
            A populated TrackerMetrics instance.

        Raises:
            MetricsComputationError: If computation fails.
        """
        try:
            total = len(applications)
            if total == 0:
                return TrackerMetrics()

            by_status: dict[str, int] = {}
            by_source: dict[str, int] = {}
            by_company: dict[str, int] = {}
            by_date: dict[str, int] = {}

            success_count = 0
            failure_count = 0
            interview_count = 0
            offer_count = 0
            rejection_count = 0

            for app in applications:
                status = (app.status or "unknown").lower()
                by_status[status] = by_status.get(status, 0) + 1

                if StatusManager.is_success(status):
                    success_count += 1
                if StatusManager.is_failure(status):
                    failure_count += 1
                if StatusManager.is_interview(status):
                    interview_count += 1
                if StatusManager.is_offer(status):
                    offer_count += 1
                if status == "rejected":
                    rejection_count += 1

                company_name = self._get_company_name(app)
                if company_name:
                    by_company[company_name] = (
                        by_company.get(company_name, 0) + 1
                    )

                source = self._get_source_name(app)
                if source:
                    by_source[source] = by_source.get(source, 0) + 1

                day_key = self._get_date_key(app)
                if day_key:
                    by_date[day_key] = by_date.get(day_key, 0) + 1

            pending_count = total - success_count - failure_count

            metrics = TrackerMetrics(
                total_applications=total,
                by_status=by_status,
                by_source=dict(
                    sorted(by_source.items(), key=lambda x: -x[1]),
                ),
                by_company=dict(
                    sorted(by_company.items(), key=lambda x: -x[1]),
                ),
                success_count=success_count,
                success_rate=(success_count / total) * 100,
                failure_count=failure_count,
                failure_rate=(failure_count / total) * 100,
                interview_count=interview_count,
                interview_rate=(interview_count / total) * 100
                if total > 0
                else 0.0,
                offer_count=offer_count,
                offer_rate=(offer_count / total) * 100,
                rejection_count=rejection_count,
                pending_count=pending_count,
                applications_per_day=dict(
                    sorted(by_date.items()),
                ),
            )
            return metrics

        except Exception as exc:
            raise MetricsComputationError(
                message=f"Failed to compute metrics: {exc}",
                original=exc,
            ) from exc

    async def compute_for_application(
        self,
        application: Any,
        db_session: Any = None,
    ) -> dict[str, Any]:
        """Compute individual application stats.

        Args:
            application: The Application ORM object.
            db_session: Optional session for querying history.

        Returns:
            Dict with timing info, status path length, etc.
        """
        history_count = 0
        if db_session is not None:
            from app.db.models.application_status_history import (
                ApplicationStatusHistory,
            )

            stmt = (
                select(func.count())
                .select_from(ApplicationStatusHistory)
                .where(
                    ApplicationStatusHistory.application_id == application.id,
                )
            )
            result = await db_session.execute(stmt)
            history_count = result.scalar() or 0
        elif hasattr(application, "status_history") and application.status_history is not None:
            history_count = len(application.status_history)

        return {
            "application_id": str(application.id),
            "status": application.status,
            "history_count": history_count,
            "is_terminal": StatusManager.is_terminal(application.status),
            "is_success": StatusManager.is_success(application.status),
            "is_failure": StatusManager.is_failure(application.status),
        }

    def _get_company_name(self, app: Any) -> Optional[str]:
        """Extract company name from an application's related job."""
        try:
            if hasattr(app, "job") and app.job is not None:
                if hasattr(app.job, "company") and app.job.company is not None:
                    return app.job.company.name
        except Exception:
            pass
        return None

    def _get_source_name(self, app: Any) -> Optional[str]:
        """Extract source name from an application's related job."""
        try:
            if hasattr(app, "job") and app.job is not None:
                if hasattr(app.job, "source") and app.job.source is not None:
                    return app.job.source.name
        except Exception:
            pass
        return None

    def _get_date_key(self, app: Any) -> Optional[str]:
        """Extract a date key (YYYY-MM-DD) from the application."""
        try:
            dt = None
            if hasattr(app, "applied_date") and app.applied_date:
                dt = app.applied_date
            elif hasattr(app, "created_at") and app.created_at:
                dt = app.created_at

            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%d")
            if isinstance(dt, date):
                return dt.isoformat()
        except Exception:
            pass
        return None
