from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.agents.apply_agent.state_machine import ApplicationState, StateMachine
from app.collectors.models import JobData


@dataclass
class FormField:
    """A single detected form field on an application page."""

    element_type: str = "text"
    selector: str = ""
    label: str = ""
    name: str = ""
    required: bool = False
    field_type: str = "unknown"
    options: list[str] = field(default_factory=list)
    value: Any = None
    placeholder: str = ""
    readonly: bool = False
    autocomplete: str = ""


@dataclass
class UserProfile:
    """Minimal user profile for form filling.

    In production this would be loaded from the database;
    for the framework it accepts a flat dict of field values.
    """

    personal_details: dict[str, Any] = field(default_factory=dict)
    work_history: list[dict[str, Any]] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadedDocument:
    """A document that has been uploaded or is pending upload."""

    field_selector: str = ""
    file_path: str = ""
    file_type: str = ""
    uploaded: bool = False
    error: Optional[str] = None


@dataclass
class ApplicationContext:
    """Complete context for a single application run.

    This object is created at the start of an application lifecycle
    and passed through each step. It accumulates state as the
    application progresses.
    """

    job: JobData
    user_profile: UserProfile = field(default_factory=UserProfile)
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    uploaded_documents: list[UploadedDocument] = field(default_factory=list)
    session_ref: Any = None
    state_machine: StateMachine = field(default_factory=StateMachine)
    form_fields: list[FormField] = field(default_factory=list)
    canonical_fields: dict[str, FormField] = field(default_factory=dict)
    field_values: dict[str, Any] = field(default_factory=dict)
    detected_questions: list[str] = field(default_factory=list)
    answered_questions: dict[str, str] = field(default_factory=dict)
    review_screenshots: list[str] = field(default_factory=list)
    submit_screenshot: Optional[str] = None
    confirmation_code: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    mode: str = "review"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def state(self) -> ApplicationState:
        return self.state_machine.state

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def has_errors(self) -> bool:
        return len(self.errors) > 0
