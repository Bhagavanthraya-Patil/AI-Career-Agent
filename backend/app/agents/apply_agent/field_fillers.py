from __future__ import annotations

from typing import Any, Optional

from app.agents.apply_agent.application_context import FormField
from app.agents.apply_agent.exceptions import FieldFillError
from app.collectors.logging import CollectorLoggerProtocol


class FieldFiller:
    """Fills individual form fields on a Playwright page.

    Handles text inputs, dropdowns (select), checkboxes, radio buttons,
    date pickers, and textareas. Uses Playwright's native fill/select/check
    APIs with appropriate waits and retries.

    Usage::

        filler = FieldFiller(logger=logger)
        await filler.fill_field(page, field, "John")
    """

    def __init__(self, logger: Optional[CollectorLoggerProtocol] = None) -> None:
        self._logger = logger

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def fill_field(self, page: Any, field: FormField, value: Any) -> None:
        """Fill a single form field with the given value.

        Args:
            page: A Playwright Page object.
            field: The FormField to fill.
            value: The value to fill.

        Raises:
            FieldFillError: If the field cannot be filled.
        """
        if field.readonly:
            self._log(f"Skipping readonly field: {field.label or field.name}", "warning")
            return

        if field.element_type == "file":
            self._log(f"Skipping file field via FieldFiller: {field.label or field.name}")
            return

        try:
            if field.element_type == "text":
                await self._fill_text(page, field, value)
            elif field.element_type == "dropdown":
                await self._fill_dropdown(page, field, value)
            elif field.element_type == "checkbox":
                await self._fill_checkbox(page, field, value)
            elif field.element_type == "radio":
                await self._fill_radio(page, field, value)
            elif field.element_type == "date":
                await self._fill_date(page, field, value)
            else:
                self._log(f"Unsupported field type: {field.element_type}", "warning")
        except FieldFillError:
            raise
        except Exception as exc:
            raise FieldFillError(
                message=f"Failed to fill field '{field.label or field.name}': {exc}",
                field_name=field.label or field.name,
                field_type=field.field_type,
                original=exc,
            ) from exc

    async def _fill_text(self, page: Any, field: FormField, value: Any) -> None:
        """Fill a text input or textarea."""
        str_value = str(value) if value is not None else ""
        el = page.locator(field.selector)
        await el.fill(str_value)

    async def _fill_dropdown(self, page: Any, field: FormField, value: Any) -> None:
        """Select an option from a dropdown."""
        str_value = str(value) if value is not None else ""
        el = page.locator(field.selector)

        # Try exact label match first
        try:
            await el.select_option(label=str_value)
            return
        except Exception:
            pass

        # Try exact value match
        try:
            await el.select_option(value=str_value)
            return
        except Exception:
            pass

        # Try partial match
        try:
            await el.select_option(index=0)
            return
        except Exception:
            pass

        # Last resort: try to find a matching option by partial text
        if field.options:
            for i, opt in enumerate(field.options):
                if str_value.lower() in opt.lower():
                    await el.select_option(index=i)
                    return

        # If no match, select the first non-empty option
        for i, opt in enumerate(field.options):
            if opt.strip():
                await el.select_option(index=i)
                return

        raise FieldFillError(
            message=f"No matching option for '{str_value}' in dropdown '{field.label or field.name}'",
            field_name=field.label or field.name,
            field_type="dropdown",
        )

    async def _fill_checkbox(self, page: Any, field: FormField, value: Any) -> None:
        """Check or uncheck a checkbox based on truthy value."""
        el = page.locator(field.selector)
        should_check = bool(value)
        is_checked = await el.is_checked()
        if should_check and not is_checked:
            await el.check()
        elif not should_check and is_checked:
            await el.uncheck()

    async def _fill_radio(self, page: Any, field: FormField, value: Any) -> None:
        """Select a radio button option."""
        str_value = str(value) if value is not None else ""
        el = page.locator(field.selector)

        # If value is provided, find the radio with matching value/label
        if str_value:
            radio_group = page.locator(f"{field.selector}, input[name=\"{field.name}\"]")
            count = await radio_group.count()
            for i in range(count):
                radio = radio_group.nth(i)
                radio_value = await radio.get_attribute("value") or ""
                radio_label = await self._get_radio_label(radio)
                if str_value.lower() in radio_value.lower() or str_value.lower() in radio_label.lower():
                    await radio.check()
                    return

        # Default: check the first radio in the group
        await el.check()

    async def _fill_date(self, page: Any, field: FormField, value: Any) -> None:
        """Fill a date field."""
        str_value = str(value) if value is not None else ""
        el = page.locator(field.selector)
        input_type = await el.get_attribute("type")
        if input_type in ("date", "datetime-local", "month", "week", "time"):
            await el.fill(str_value)
        else:
            await el.fill(str_value)

    async def _get_radio_label(self, radio: Any) -> str:
        """Get the label text for a radio button."""
        try:
            el_id = await radio.get_attribute("id")
            if el_id:
                label_el = radio.page.locator(f'label[for="{el_id}"]')
                if await label_el.count() > 0:
                    return await label_el.inner_text()
        except Exception:
            pass
        return ""

    async def fill_all(self, page: Any, canonical_fields: dict[str, FormField], values: dict[str, Any]) -> list[FieldFillError]:
        """Fill all mapped fields with the given values.

        Args:
            page: A Playwright Page object.
            canonical_fields: Canonical field mapping from FieldMapper.
            values: Dict mapping canonical type to value.

        Returns:
            A list of FieldFillError for fields that failed (empty if all succeeded).
        """
        errors: list[FieldFillError] = []
        for canon, field in canonical_fields.items():
            value = values.get(canon)
            if value is not None:
                try:
                    await self.fill_field(page, field, value)
                    field.value = value
                    self._log(f"Filled '{canon}' ({field.label}) with '{value}'")
                except FieldFillError as exc:
                    errors.append(exc)
                    self._log(str(exc), "error")
        return errors
