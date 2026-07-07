from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class TrackerEvent:
    """Base event emitted by the TrackerAgent during its lifecycle."""

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    application_id: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationTrackedEvent(TrackerEvent):
    """Emitted when a new application is tracked."""

    def __init__(
        self,
        application_id: str,
        job_id: str,
        initial_status: str,
    ) -> None:
        super().__init__(
            event_type="application_tracked",
            application_id=application_id,
            data={
                "job_id": job_id,
                "initial_status": initial_status,
            },
        )


@dataclass
class StatusChangedEvent(TrackerEvent):
    """Emitted when an application status changes."""

    def __init__(
        self,
        application_id: str,
        from_status: Optional[str],
        to_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(
            event_type="status_changed",
            application_id=application_id,
            data={
                "from_status": from_status,
                "to_status": to_status,
                "changed_by": changed_by,
                "reason": reason,
            },
        )


@dataclass
class MetricsUpdatedEvent(TrackerEvent):
    """Emitted when metrics are recomputed."""

    def __init__(self, metrics: dict[str, Any]) -> None:
        super().__init__(
            event_type="metrics_updated",
            data={"metrics": metrics},
        )


@dataclass
class DuplicateDetectedEvent(TrackerEvent):
    """Emitted when a duplicate application is detected."""

    def __init__(self, job_id: str, existing_id: str) -> None:
        super().__init__(
            event_type="duplicate_detected",
            data={
                "job_id": job_id,
                "existing_id": existing_id,
            },
        )


@dataclass
class CleanupCompletedEvent(TrackerEvent):
    """Emitted when cleanup finishes."""

    def __init__(self, records_affected: int = 0) -> None:
        super().__init__(
            event_type="cleanup_completed",
            data={"records_affected": records_affected},
        )
