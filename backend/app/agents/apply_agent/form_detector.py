from __future__ import annotations

import re
from typing import Any, Optional

from app.agents.apply_agent.application_context import FormField
from app.agents.apply_agent.exceptions import FormDetectionError
from app.collectors.logging import CollectorLoggerProtocol


class FormDetector:
    """Detects and extracts form fields from a Playwright page.

    Uses Playwright locator APIs combined with heuristics
    (label proximity, placeholder text, name/id/aria-label attributes)
    to identify form elements and their metadata.

    Usage::

        detector = FormDetector(logger=logger)
        fields = await detector.detect(page)
    """

    ELEMENT_ROLE_MAP: dict[str, str] = {
        "textbox": "text",
        "combobox": "dropdown",
        "checkbox": "checkbox",
        "radio": "radio",
        "button": "button",
        "listbox": "dropdown",
        "searchbox": "text",
    }

    AUTOCOMPLETE_TO_FIELD: dict[str, str] = {
        "given-name": "first_name",
        "family-name": "last_name",
        "email": "email",
        "tel": "phone",
        "tel-national": "phone",
        "street-address": "address",
        "address-line1": "address",
        "address-line2": "address_line2",
        "postal-code": "postal_code",
        "country-name": "country",
        "organization": "company",
        "job-title": "job_title",
    }

    INPUT_TYPE_MAP: dict[str, str] = {
        "text": "text",
        "email": "text",
        "tel": "text",
        "url": "text",
        "password": "text",
        "number": "text",
        "date": "date",
        "datetime-local": "date",
        "month": "date",
        "week": "date",
        "time": "date",
        "file": "file",
        "checkbox": "checkbox",
        "radio": "radio",
        "hidden": "hidden",
        "submit": "button",
        "reset": "button",
    }

    def __init__(self, logger: Optional[CollectorLoggerProtocol] = None) -> None:
        self._logger = logger

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def detect(self, page: Any) -> list[FormField]:
        """Detect all form fields on the current page.

        Args:
            page: A Playwright Page object.

        Returns:
            A list of FormField instances sorted by tab order.

        Raises:
            FormDetectionError: If detection fails catastrophically.
        """
        try:
            fields: list[FormField] = []
            fields.extend(await self._detect_input_elements(page))
            fields.extend(await self._detect_select_elements(page))
            fields.extend(await self._detect_textarea_elements(page))
            fields = self._deduplicate(fields)
            fields = self._sort_by_tab_order(fields, await self._get_tab_order(page))
            self._log(f"Detected {len(fields)} form fields")
            return fields
        except FormDetectionError:
            raise
        except Exception as exc:
            raise FormDetectionError(
                message=f"Form detection failed: {exc}",
                step="form_detection",
                original=exc,
            ) from exc

    async def _detect_input_elements(self, page: Any) -> list[FormField]:
        """Detect <input> elements on the page."""
        fields: list[FormField] = []
        inputs = await page.query_selector_all("input:not([type=hidden])")
        for el in inputs:
            try:
                field = await self._extract_input_field(el)
                if field:
                    fields.append(field)
            except Exception:
                continue
        return fields

    async def _detect_select_elements(self, page: Any) -> list[FormField]:
        """Detect <select> elements on the page."""
        fields: list[FormField] = []
        selects = await page.query_selector_all("select")
        for el in selects:
            try:
                field = await self._extract_select_field(el)
                if field:
                    fields.append(field)
            except Exception:
                continue
        return fields

    async def _detect_textarea_elements(self, page: Any) -> list[FormField]:
        """Detect <textarea> elements on the page."""
        fields: list[FormField] = []
        textareas = await page.query_selector_all("textarea")
        for el in textareas:
            try:
                field = await self._extract_textarea_field(el)
                if field:
                    fields.append(field)
            except Exception:
                continue
        return fields

    async def _extract_input_field(self, el: Any) -> Optional[FormField]:
        """Extract field metadata from an <input> element."""
        name = (await el.get_attribute("name")) or ""
        el_id = (await el.get_attribute("id")) or ""
        input_type = (await el.get_attribute("type")) or "text"
        placeholder = (await el.get_attribute("placeholder")) or ""
        aria_label = (await el.get_attribute("aria-label")) or ""
        autocomplete = (await el.get_attribute("autocomplete")) or ""
        required = (await el.get_attribute("required")) is not None
        readonly = (await el.get_attribute("readonly")) is not None

        label = await self._find_label_for_element(page=el.page, el_id=el_id, name=name, aria_label=aria_label, placeholder=placeholder)

        element_type = self.INPUT_TYPE_MAP.get(input_type, "text")
        selector = await self._build_unique_selector(el)

        field = FormField(
            element_type=element_type,
            selector=selector,
            label=label,
            name=name,
            required=required,
            placeholder=placeholder,
            readonly=readonly,
            autocomplete=autocomplete,
        )
        return field

    async def _extract_select_field(self, el: Any) -> Optional[FormField]:
        """Extract field metadata from a <select> element."""
        name = (await el.get_attribute("name")) or ""
        el_id = (await el.get_attribute("id")) or ""
        aria_label = (await el.get_attribute("aria-label")) or ""
        required = (await el.get_attribute("required")) is not None

        options: list[str] = []
        option_els = await el.query_selector_all("option")
        for opt in option_els:
            text = await opt.inner_text()
            value = (await opt.get_attribute("value")) or ""
            options.append(value or text.strip())

        label = await self._find_label_for_element(page=el.page, el_id=el_id, name=name, aria_label=aria_label)
        selector = await self._build_unique_selector(el)

        return FormField(
            element_type="dropdown",
            selector=selector,
            label=label,
            name=name,
            required=required,
            options=options,
        )

    async def _extract_textarea_field(self, el: Any) -> Optional[FormField]:
        """Extract field metadata from a <textarea> element."""
        name = (await el.get_attribute("name")) or ""
        el_id = (await el.get_attribute("id")) or ""
        placeholder = (await el.get_attribute("placeholder")) or ""
        aria_label = (await el.get_attribute("aria-label")) or ""
        required = (await el.get_attribute("required")) is not None

        label = await self._find_label_for_element(page=el.page, el_id=el_id, name=name, aria_label=aria_label, placeholder=placeholder)
        selector = await self._build_unique_selector(el)

        return FormField(
            element_type="text",
            selector=selector,
            label=label,
            name=name,
            required=required,
            placeholder=placeholder,
        )

    async def _find_label_for_element(
        self,
        page: Any,
        el_id: str = "",
        name: str = "",
        aria_label: str = "",
        placeholder: str = "",
    ) -> str:
        """Find the visible label text for a form element using several strategies."""
        # Strategy 1: aria-label
        if aria_label:
            return aria_label

        # Strategy 2: explicit <label for="id">
        if el_id:
            label_el = await page.query_selector(f'label[for="{el_id}"]')
            if label_el:
                text = await label_el.inner_text()
                if text.strip():
                    return text.strip()

        # Strategy 3: parent <label> or wrapping label
        # Strategy 4: placeholder as label
        if placeholder:
            return placeholder

        # Strategy 5: use name attribute as fallback
        if name:
            return name.replace("_", " ").replace("-", " ").strip().title()

        return ""

    async def _build_unique_selector(self, el: Any) -> str:
        """Build a unique CSS selector for the element."""
        tag = await el.evaluate("el => el.tagName.toLowerCase()")
        el_id = await el.get_attribute("id")
        if el_id:
            return f"#{el_id}"

        name = await el.get_attribute("name")
        if name:
            return f'{tag}[name="{name}"]'

        class_attr = await el.get_attribute("class")
        if class_attr:
            classes = class_attr.strip().split()
            class_selector = ".".join(classes[:3])
            return f"{tag}.{class_selector}"

        return tag

    async def _get_tab_order(self, page: Any) -> list[str]:
        """Get elements in tab order using tabindex attributes."""
        elements = await page.query_selector_all(
            "input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
        )
        selectors: list[str] = []
        for el in elements:
            sel = await self._build_unique_selector(el)
            selectors.append(sel)
        return selectors

    def _sort_by_tab_order(self, fields: list[FormField], tab_order: list[str]) -> list[FormField]:
        """Sort fields to match tab order where possible."""
        selector_to_field = {f.selector: f for f in fields}
        sorted_fields: list[FormField] = []
        used: set[str] = set()

        for sel in tab_order:
            if sel in selector_to_field and sel not in used:
                sorted_fields.append(selector_to_field[sel])
                used.add(sel)

        for field in fields:
            if field.selector not in used:
                sorted_fields.append(field)
                used.add(field.selector)

        return sorted_fields

    def _deduplicate(self, fields: list[FormField]) -> list[FormField]:
        """Remove duplicate fields by selector."""
        seen: set[str] = set()
        unique: list[FormField] = []
        for field in fields:
            key = field.selector
            if key and key not in seen:
                seen.add(key)
                unique.append(field)
            elif not key:
                unique.append(field)
        return unique
