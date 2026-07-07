from __future__ import annotations

from typing import Any, Optional, Tuple

from app.extractors.base import BaseExtractor
from app.extractors.html_cleaner import HtmlCleaner


class DescriptionExtractor(BaseExtractor[Tuple[Optional[str], Optional[str]]]):
    """Extract and normalize job description content.

    Returns a tuple of ``(description_raw, description_html)``.
    ``description_html`` is preserved as-is if present; ``description_raw``
    is a plain-text version produced by ``HtmlCleaner``.
    """

    name = "description"

    def extract(
        self,
        raw: Any,
        **context: Any,
    ) -> Tuple[Optional[str], Optional[str]]:
        html: Optional[str] = None
        plain: Optional[str] = None

        if isinstance(raw, dict):
            html = raw.get("description_html") or None
            plain = raw.get("description_raw") or None
        elif isinstance(raw, str):
            if HtmlCleaner.is_html(raw):
                html = raw
            else:
                plain = raw

        if html and HtmlCleaner.is_html(html):
            if not plain:
                plain = HtmlCleaner.to_plain_text(html)
            html = HtmlCleaner.normalize_whitespace(html)
        elif html and not HtmlCleaner.is_html(html):
            if not plain:
                plain = html
            html = None

        if plain:
            plain = HtmlCleaner.normalize_whitespace(
                HtmlCleaner.to_plain_text(plain)
            )

        return (plain or None, html or None)
