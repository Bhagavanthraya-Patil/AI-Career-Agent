from __future__ import annotations

from typing import Optional


class TrackerError(Exception):
    """Base exception for all Tracker Agent errors."""

    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.step = step
        self.original = original
        super().__init__(message)


class ApplicationNotFoundError(TrackerError):
    """Raised when an application record is not found."""

    def __init__(
        self,
        application_id: str = "",
        job_id: str = "",
    ) -> None:
        self.application_id = application_id
        self.job_id = job_id
        msg = f"Application not found"
        if application_id:
            msg += f": {application_id}"
        if job_id:
            msg += f" for job: {job_id}"
        super().__init__(msg, step="repository")


class DuplicateApplicationError(TrackerError):
    """Raised when attempting to track a job that is already tracked."""

    def __init__(self, job_id: str, existing_id: str) -> None:
        self.job_id = job_id
        self.existing_id = existing_id
        super().__init__(
            message=f"Job {job_id} already tracked as application {existing_id}",
            step="track",
        )


class InvalidStatusTransitionError(TrackerError):
    """Raised when a status transition is not allowed."""

    def __init__(
        self,
        from_status: str,
        to_status: str,
        reason: Optional[str] = None,
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        msg = f"Invalid transition: {from_status} -> {to_status}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, step="status_transition")


class InvalidStatusError(TrackerError):
    """Raised when an unknown status value is used."""

    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(
            message=f"Unknown status: {status}",
            step="status_validation",
        )


class DuplicateHistoryEntryError(TrackerError):
    """Raised when a duplicate history entry is detected."""


class MetricsComputationError(TrackerError):
    """Raised when metrics computation fails."""


class TimelineBuildError(TrackerError):
    """Raised when timeline building fails."""


class CleanupError(TrackerError):
    """Raised when tracker cleanup fails."""
