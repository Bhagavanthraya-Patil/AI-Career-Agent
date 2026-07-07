from __future__ import annotations

from typing import Optional

from app.agents.tracker.exceptions import InvalidStatusError, InvalidStatusTransitionError

# All valid application statuses
VALID_STATUSES: set[str] = {
    "draft",
    "ready",
    "applied",
    "submitted",
    "viewed",
    "assessment",
    "interview",
    "technical_interview",
    "hr_interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "expired",
    "failed",
    "cancelled",
}

# Terminal states — no transitions allowed from these
TERMINAL_STATUSES: set[str] = {
    "accepted",
    "rejected",
    "withdrawn",
    "expired",
    "cancelled",
}

# Valid transitions: mapping from → set of allowed to-states
# Each transition lists the explicit valid destinations.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"ready", "cancelled"},
    "ready": {"applied", "withdrawn", "cancelled"},
    "applied": {"submitted", "failed", "withdrawn", "cancelled"},
    "submitted": {"viewed", "failed", "withdrawn", "cancelled"},
    "viewed": {"assessment", "rejected", "withdrawn", "cancelled"},
    "assessment": {"interview", "rejected", "withdrawn", "cancelled"},
    "interview": {
        "technical_interview",
        "hr_interview",
        "offer",
        "rejected",
        "withdrawn",
        "cancelled",
    },
    "technical_interview": {
        "hr_interview",
        "offer",
        "rejected",
        "withdrawn",
        "cancelled",
    },
    "hr_interview": {
        "offer",
        "rejected",
        "withdrawn",
        "cancelled",
    },
    "offer": {"accepted", "rejected", "withdrawn", "expired", "cancelled"},
    "accepted": set(),
    "rejected": set(),
    "withdrawn": set(),
    "expired": set(),
    "failed": {"ready", "applied", "draft", "cancelled"},
    "cancelled": set(),
}

SUCCESS_STATUSES: set[str] = {"accepted"}
FAILURE_STATUSES: set[str] = {"rejected", "failed"}
INTERVIEW_STATUSES: set[str] = {
    "interview",
    "technical_interview",
    "hr_interview",
}
OFFER_STATUSES: set[str] = {"offer", "accepted"}
PENDING_STATUSES: set[str] = {
    "draft",
    "ready",
    "applied",
    "submitted",
    "viewed",
    "assessment",
}
ACTIVE_STATUSES: set[str] = {
    "draft",
    "ready",
    "applied",
    "submitted",
    "viewed",
    "assessment",
    "interview",
    "technical_interview",
    "hr_interview",
    "offer",
}


class StatusManager:
    """Validates and manages application status transitions.

    Ensures every status change follows the defined transition rules.
    Provides helpers for categorizing statuses.

    Usage::

        mgr = StatusManager()
        mgr.validate_transition("draft", "ready")  # OK
        mgr.validate_transition("draft", "accepted")  # raises
    """

    @classmethod
    def validate_transition(
        cls,
        from_status: str,
        to_status: str,
    ) -> None:
        """Validate a status transition.

        Args:
            from_status: The current status.
            to_status: The target status.

        Raises:
            InvalidStatusError: If either status is not recognized.
            InvalidStatusTransitionError: If the transition is not allowed.
        """
        cls.validate_status(from_status)
        cls.validate_status(to_status)

        allowed = VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidStatusTransitionError(
                from_status=from_status,
                to_status=to_status,
            )

    @classmethod
    def validate_status(cls, status: str) -> None:
        """Validate that a status string is a known status.

        Raises InvalidStatusError if unknown.
        """
        if status not in VALID_STATUSES:
            raise InvalidStatusError(status=status)

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check whether a status is terminal (no further transitions)."""
        return status in TERMINAL_STATUSES

    @classmethod
    def is_success(cls, status: str) -> bool:
        return status in SUCCESS_STATUSES

    @classmethod
    def is_failure(cls, status: str) -> bool:
        return status in FAILURE_STATUSES

    @classmethod
    def is_interview(cls, status: str) -> bool:
        return status in INTERVIEW_STATUSES

    @classmethod
    def is_offer(cls, status: str) -> bool:
        return status in OFFER_STATUSES

    @classmethod
    def is_pending(cls, status: str) -> bool:
        return status in PENDING_STATUSES

    @classmethod
    def is_active(cls, status: str) -> bool:
        return status in ACTIVE_STATUSES

    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> set[str]:
        """Get all valid target statuses from a given status."""
        cls.validate_status(from_status)
        return VALID_TRANSITIONS.get(from_status, set())
