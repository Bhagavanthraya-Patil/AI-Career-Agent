from __future__ import annotations

from typing import Any, Optional

from app.agents.apply_agent.application_context import FormField, UserProfile
from app.agents.apply_agent.exceptions import ValidationError


REQUIRED_PERSONAL_FIELDS = {
    "first_name": "First name",
    "last_name": "Last name",
    "email": "Email address",
}


def validate_user_profile(profile: UserProfile) -> list[str]:
    """Validate that the user profile has minimum required fields.

    Returns a list of missing/invalid field descriptions.
    """
    errors: list[str] = []
    details = profile.personal_details

    for key, display_name in REQUIRED_PERSONAL_FIELDS.items():
        if key not in details or not details[key]:
            errors.append(f"Missing required profile field: {display_name}")

    if "email" in details and details["email"]:
        email = str(details["email"])
        if "@" not in email or "." not in email:
            errors.append(f"Invalid email format: {email}")

    if not profile.work_history:
        errors.append("Work history is empty; at least one entry recommended")

    return errors


def validate_form_fields(fields: list[FormField]) -> list[str]:
    """Validate detected form fields for unsupported or problematic types.

    Returns a list of warning/error messages.
    """
    errors: list[str] = []
    for field in fields:
        if field.element_type == "hidden" and field.required:
            errors.append(f"Hidden required field detected: {field.label or field.name}")
    return errors


def validate_required_fields_filled(
    canonical_fields: dict[str, FormField],
    field_values: dict[str, Any],
) -> list[str]:
    """Check that all required canonical fields have been filled.

    Returns a list of missing field descriptions.
    """
    missing: list[str] = []
    for canon, field in canonical_fields.items():
        if field.required:
            value = field_values.get(canon)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(f"Required field '{canon}' ({field.label}) is empty")
    return missing


def validate_file_path(file_path: Optional[str], allowed_formats: Optional[list[str]] = None) -> Optional[str]:
    """Validate a file path for upload.

    Returns an error message or None if valid.
    """
    if not file_path:
        return "File path is empty"

    if allowed_formats:
        lower = file_path.lower()
        if not any(lower.endswith(fmt.lower()) for fmt in allowed_formats):
            return f"File format not supported. Allowed: {', '.join(allowed_formats)}"

    return None


def check_preconditions(step: str, ctx: Any) -> None:
    """Run pre-flight checks before a lifecycle step.

    Args:
        step: The lifecycle step name (e.g., 'fill_application').
        ctx: The ApplicationContext.

    Raises:
        ValidationError: If preconditions are not met.
    """
    errors: list[str] = []

    if step == "fill_application":
        if not ctx.form_fields:
            errors.append("No form fields detected; run analyze_page first")

    elif step == "upload_documents":
        if not ctx.resume_path and not ctx.cover_letter_path:
            errors.append("No documents to upload")

    elif step == "submit":
        missing = validate_required_fields_filled(ctx.canonical_fields, ctx.field_values)
        errors.extend(missing)

    if errors:
        raise ValidationError(
            message=f"Preconditions failed for step '{step}'",
            errors=errors,
            step=step,
        )
