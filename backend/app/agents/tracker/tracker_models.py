from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class TrackerConfig:
    """Configuration for the TrackerAgent orchestrator."""

    status_after_apply: str = "applied"
    record_history: bool = True
    deduplicate_by_job: bool = True
    auto_cleanup: bool = True
    max_history_entries: int = 1000


@dataclass
class TrackApplicationInput:
    """Input for tracking a new application."""

    job_id: str
    apply_url: Optional[str] = None
    resume_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    initial_status: str = "draft"
    notes: Optional[str] = None
    browser_session_id: Optional[str] = None
    source_collector: Optional[str] = None
    config: TrackerConfig = field(default_factory=TrackerConfig)


@dataclass
class ApplicationStatusData:
    """Full status data for an application record."""

    application_id: str
    job_id: str
    job_title: str = ""
    company_name: str = ""
    status: str = "draft"
    resume_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    apply_url: Optional[str] = None
    confirmation_code: Optional[str] = None
    screenshot_path: Optional[str] = None
    browser_session_id: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    offer_details: Optional[dict] = None
    rejection_reason: Optional[str] = None
    interview_dates: Optional[list] = None
    applied_date: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if isinstance(v, datetime):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result


@dataclass
class StatusChangeEvent:
    """A single status change event in the application history."""

    application_id: str
    from_status: Optional[str]
    to_status: str
    changed_by: str = "system"
    reason: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    event_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "application_id": self.application_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_by": self.changed_by,
        }
        if self.reason:
            result["reason"] = self.reason
        if self.metadata:
            result["metadata"] = self.metadata
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        if self.event_id:
            result["event_id"] = self.event_id
        return result


@dataclass
class HistoryEntry:
    """A single recorded history entry (persisted)."""

    entry_id: str
    application_id: str
    from_status: Optional[str]
    to_status: str
    changed_by: str
    reason: Optional[str]
    metadata: Optional[dict]
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "application_id": self.application_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_by": self.changed_by,
            "reason": self.reason,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TrackerMetrics:
    """Aggregate metrics computed over all tracked applications."""

    total_applications: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    by_company: dict[str, int] = field(default_factory=dict)

    success_count: int = 0
    success_rate: float = 0.0

    failure_count: int = 0
    failure_rate: float = 0.0

    interview_count: int = 0
    interview_rate: float = 0.0

    offer_count: int = 0
    offer_rate: float = 0.0

    rejection_count: int = 0

    pending_count: int = 0

    applications_per_day: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_applications": self.total_applications,
            "by_status": self.by_status,
            "by_source": self.by_source,
            "by_company": self.by_company,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 2),
            "failure_count": self.failure_count,
            "failure_rate": round(self.failure_rate, 2),
            "interview_count": self.interview_count,
            "interview_rate": round(self.interview_rate, 2),
            "offer_count": self.offer_count,
            "offer_rate": round(self.offer_rate, 2),
            "rejection_count": self.rejection_count,
            "pending_count": self.pending_count,
            "applications_per_day": self.applications_per_day,
        }


@dataclass
class TimelineEntry:
    """A single entry in the application timeline."""

    event_type: str  # "status_change", "note", "interview", "offer"
    timestamp: datetime
    title: str
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "description": self.description,
            "metadata": self.metadata or {},
        }


@dataclass
class ApplicationTimeline:
    """Complete timeline for a single application."""

    application_id: str
    entries: list[TimelineEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "entries": [e.to_dict() for e in self.entries],
        }


@dataclass
class ApplyAgentIntegration:
    """Data from the Apply Agent to be recorded by the Tracker."""

    success: bool
    final_state: Optional[str]
    confirmation_code: Optional[str]
    screenshot_path: Optional[str]
    errors: list[str]
    duration_seconds: float
    state_history: list[tuple[str, str, Optional[str]]]
