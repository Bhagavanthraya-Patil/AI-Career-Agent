from __future__ import annotations

from typing import Optional

from pydantic import Field

from . import BaseConfig


class ApplicationSettings(BaseConfig):
    max_daily: int = Field(
        default=10,
        description="Maximum auto-submitted applications per day",
    )
    require_review: bool = Field(
        default=True,
        description="Require user review before application submission",
    )
    auto_submit: bool = Field(
        default=False,
        description="EXPERIMENTAL: Submit applications without user confirmation",
    )
    always_attach_cover_letter: bool = Field(
        default=True,
        description="Always include a tailored cover letter with applications",
    )
    default_status: str = Field(
        default="discovered",
        description="Default status for new job discoveries",
    )
    screenshot_on_submit: bool = Field(
        default=True,
        description="Capture screenshot of the submitted form",
    )
    screenshot_on_review: bool = Field(
        default=True,
        description="Capture screenshot of the pre-filled form for review",
    )
    fill_personal_details: bool = Field(
        default=True,
        description="Auto-fill personal details on application forms",
    )
    fill_work_history: bool = Field(
        default=True,
        description="Auto-fill work history on application forms",
    )
    fill_education: bool = Field(
        default=True,
        description="Auto-fill education on application forms",
    )
    pause_on_unknown_field: bool = Field(
        default=True,
        description="Pause and request user input for unknown form fields",
    )
    max_form_fill_attempts: int = Field(
        default=3,
        description="Maximum attempts to fill a single form field",
    )

    # Tracker settings
    track_applications: bool = Field(
        default=True,
        description="Enable application tracking",
    )
    record_status_history: bool = Field(
        default=True,
        description="Record immutable status change history",
    )
    deduplicate_tracking: bool = Field(
        default=True,
        description="Prevent tracking the same job twice",
    )
    max_history_per_application: int = Field(
        default=1000,
        description="Maximum history entries per application",
    )
    auto_cleanup_inactive: bool = Field(
        default=True,
        description="Automatically deactivate terminal-status applications",
    )
