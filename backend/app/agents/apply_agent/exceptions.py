from __future__ import annotations

from typing import Optional


class ApplyError(Exception):
    """Base exception for all Apply Agent errors."""

    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.step = step
        self.original = original
        super().__init__(message)


class NavigationError(ApplyError):
    """Raised when navigating to the application URL fails."""


class FormDetectionError(ApplyError):
    """Raised when form fields cannot be detected or parsed."""


class FieldFillError(ApplyError):
    """Raised when a specific form field cannot be filled.

    Attributes:
        field_name: The name/label of the field that failed.
        field_type: The canonical type of the field.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_type: Optional[str] = None,
        step: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.field_name = field_name
        self.field_type = field_type
        super().__init__(message, step=step, original=original)


class UploadError(ApplyError):
    """Raised when document upload fails."""


class SubmissionError(ApplyError):
    """Raised when form submission fails."""


class VerificationError(ApplyError):
    """Raised when submission verification fails."""


class ValidationError(ApplyError):
    """Raised when pre-flight validation fails.

    Attributes:
        errors: List of validation error messages.
    """

    def __init__(
        self,
        message: str,
        errors: Optional[list[str]] = None,
        step: Optional[str] = None,
    ) -> None:
        self.errors = errors or []
        super().__init__(message, step=step)


class StateTransitionError(ApplyError):
    """Raised when an invalid state transition is attempted."""

    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        target_state: Optional[str] = None,
    ) -> None:
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(message)


class TimeoutError(ApplyError):
    """Raised when an operation exceeds its timeout."""


class UnsupportedFormError(ApplyError):
    """Raised when the form type is not supported."""


class BrowserCleanupError(ApplyError):
    """Raised when browser cleanup fails."""
