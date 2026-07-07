from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.agents.apply_agent.state_machine import ApplicationState
from app.collectors.models import JobData


@dataclass
class ApplicationResult:
    """Result of a complete or partial application run.

    Contains the final state, any output artifacts, and error
    information for downstream processing or display.
    """

    success: bool = False
    job: Optional[JobData] = None
    final_state: Optional[ApplicationState] = None
    screenshot_path: Optional[str] = None
    confirmation_code: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    state_history: list[tuple[str, str, Optional[str]]] = field(default_factory=list)
    review_screenshots: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.success and self.confirmation_code:
            return (
                f"Application submitted successfully. "
                f"Confirmation: {self.confirmation_code}"
            )
        if self.success:
            return "Application completed (review/dry-run mode)."
        return f"Application failed: {self.errors[0] if self.errors else 'Unknown error'}"

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "final_state": self.final_state.value if self.final_state else None,
            "screenshot_path": self.screenshot_path,
            "confirmation_code": self.confirmation_code,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
        }
