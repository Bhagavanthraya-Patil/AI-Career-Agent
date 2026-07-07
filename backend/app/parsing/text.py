from __future__ import annotations

import re
import unicodedata
from typing import Optional


class TextParser:
    """Reusable text processing utilities for job parsing.

    Provides HTML cleanup, whitespace normalization, unicode handling,
    and regex helpers. No website-specific logic.
    """

    HTML_TAG_RE = re.compile(r"<[^>]*>")
    HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;")
    WHITESPACE_RE = re.compile(r"\s+")
    MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
    NON_ASCII_RE = re.compile(r"[^\x20-\x7E]")

    HTML_ENTITY_MAP: dict[str, str] = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": "\"",
        "&#39;": "'",
        "&#x27;": "'",
        "&#x2F;": "/",
        "&#xa0;": " ",
        "&nbsp;": " ",
        "&ndash;": "-",
        "&mdash;": "--",
        "&hellip;": "...",
        "&copy;": "(c)",
        "&reg;": "(r)",
        "&trade;": "(tm)",
        "&bull;": "*",
    }

    @staticmethod
    def strip_html(html: Optional[str]) -> Optional[str]:
        """Remove HTML tags from a string.

        Converts common block tags to newlines for readability.
        """
        if not html:
            return html
        text = html
        block_tags = [
            r"</?(?:div|p|br|li|ol|ul|h[1-6]|tr|td|th|section|article|header|footer|nav)[^>]*>",
        ]
        for tag_pattern in block_tags:
            text = re.sub(tag_pattern, "\n", text, flags=re.IGNORECASE)
        text = TextParser.HTML_TAG_RE.sub("", text)
        text = TextParser.decode_html_entities(text)
        return TextParser.normalize_whitespace(text)

    @staticmethod
    def decode_html_entities(text: str) -> str:
        """Decode common HTML entities to plain text."""
        for entity, char in TextParser.HTML_ENTITY_MAP.items():
            text = text.replace(entity, char)
        text = TextParser.HTML_ENTITY_RE.sub("", text)
        return text

    @staticmethod
    def normalize_whitespace(text: Optional[str]) -> Optional[str]:
        """Collapse all whitespace runs into single spaces.

        Strips leading/trailing whitespace after normalization.
        Returns None if input is None or becomes empty.
        """
        if not text:
            return text
        text = TextParser.WHITESPACE_RE.sub(" ", text)
        text = TextParser.MULTI_NEWLINE_RE.sub("\n\n", text)
        text = text.strip()
        return text if text else None

    @staticmethod
    def normalize_unicode(text: Optional[str]) -> Optional[str]:
        """Normalize unicode characters to NFC form.

        Replaces curly quotes, dashes, and other typographic characters
        with their ASCII equivalents.
        """
        if not text:
            return text
        text = unicodedata.normalize("NFKC", text)
        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": "\"",
            "\u201d": "\"",
            "\u2013": "-",
            "\u2014": "--",
            "\u2026": "...",
            "\u2022": "*",
            "\u00a0": " ",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def clean_title(title: Optional[str]) -> Optional[str]:
        """Normalize a job title.

        Strips whitespace, normalizes unicode, removes common
        decorative prefixes/suffixes.
        """
        if not title:
            return title
        title = TextParser.normalize_unicode(title)
        title = TextParser.normalize_whitespace(title)
        if not title:
            return None
        title = re.sub(r"^[-*\u2022\u25cf\s]+", "", title)
        title = re.sub(r"[-*\u2022\u25cf\s]+$", "", title)
        return TextParser.normalize_whitespace(title) or None

    @staticmethod
    def clean_description(text: Optional[str]) -> Optional[str]:
        """Clean and normalize a job description.

        Strips HTML, normalizes unicode and whitespace.
        """
        if not text:
            return text
        text = TextParser.strip_html(text)
        text = TextParser.normalize_unicode(text)
        return TextParser.normalize_whitespace(text)

    @staticmethod
    def extract_numbers(text: str) -> list[int]:
        """Extract all integer numbers from a string.

        Handles comma separators: '1,234' -> 1234.
        """
        parts = re.findall(r"\d[\d,]*", text)
        result: list[int] = []
        for p in parts:
            try:
                result.append(int(p.replace(",", "")))
            except ValueError:
                continue
        return result

    @staticmethod
    def extract_number(text: str) -> Optional[int]:
        """Extract the first integer from a string."""
        numbers = TextParser.extract_numbers(text)
        return numbers[0] if numbers else None

    @staticmethod
    def contains(text: Optional[str], keywords: list[str]) -> bool:
        """Case-insensitive check if any keyword appears in text."""
        if not text:
            return False
        lower = text.lower()
        return any(kw.lower() in lower for kw in keywords)

    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        """Full text cleanup pipeline: unicode -> whitespace -> strip."""
        if not text:
            return text
        text = TextParser.normalize_unicode(text)
        text = TextParser.normalize_whitespace(text)
        return text
