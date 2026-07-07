from __future__ import annotations

import re
from typing import Optional


class HtmlCleaner:
    """Stateless HTML / Markdown / plain text cleaner.

    Provides a suite of static methods for normalizing job description
    content regardless of whether it arrives as HTML, Markdown, or
    plain text.
    """

    HTML_TAG_RE = re.compile(r"<[^>]+>")
    SCRIPT_STYLE_RE = re.compile(
        r"<(script|style|noscript)[^>]*>.*?</\1>",
        re.IGNORECASE | re.DOTALL,
    )
    WHITESPACE_RE = re.compile(r"\s+")
    ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;")
    MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    MARKDOWN_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
    MARKDOWN_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
    MARKDOWN_ITALIC_RE = re.compile(r"\*(.+?)\*")
    MARKDOWN_CODE_RE = re.compile(r"`{1,3}[^`]*`{1,3}")
    MARKDOWN_LIST_RE = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
    MARKDOWN_NUMERIC_LIST_RE = re.compile(r"^[\s]*\d+[.)]\s+", re.MULTILINE)
    MARKDOWN_BLOCKQUOTE_RE = re.compile(r"^>\s?", re.MULTILINE)
    MARKDOWN_THEMATIC_BREAK_RE = re.compile(r"^-{3,}\s*$", re.MULTILINE)

    KNOWN_MARKDOWN_CHARS = {"#", "*", "`", "[", "]", "(", ")", "_", "~", "|"}

    @staticmethod
    def is_markdown(text: str) -> bool:
        """Heuristic check: return True if text looks like Markdown."""
        if not text or not isinstance(text, str):
            return False
        return any(c in text for c in HtmlCleaner.KNOWN_MARKDOWN_CHARS)

    @staticmethod
    def is_html(text: str) -> bool:
        """Heuristic check: return True if text looks like HTML."""
        if not text or not isinstance(text, str):
            return False
        return bool(HtmlCleaner.HTML_TAG_RE.search(text))

    @staticmethod
    def strip_html(html: str) -> str:
        """Strip HTML tags, preserving whitespace between elements."""
        if not html or not isinstance(html, str):
            return ""
        text = HtmlCleaner.SCRIPT_STYLE_RE.sub("", html)
        text = HtmlCleaner.HTML_TAG_RE.sub(" ", text)
        text = HtmlCleaner.ENTITY_RE.sub(" ", text)
        text = HtmlCleaner.WHITESPACE_RE.sub(" ", text)
        return text.strip()

    @staticmethod
    def strip_markdown(md: str) -> str:
        """Strip Markdown formatting, preserving plain text content."""
        if not md or not isinstance(md, str):
            return ""
        text = HtmlCleaner.MARKDOWN_LINK_RE.sub(r"\1", md)
        text = HtmlCleaner.MARKDOWN_HEADER_RE.sub("", text)
        text = HtmlCleaner.MARKDOWN_BOLD_RE.sub(r"\1", text)
        text = HtmlCleaner.MARKDOWN_ITALIC_RE.sub(r"\1", text)
        text = HtmlCleaner.MARKDOWN_CODE_RE.sub(" ", text)
        text = HtmlCleaner.MARKDOWN_LIST_RE.sub("", text)
        text = HtmlCleaner.MARKDOWN_NUMERIC_LIST_RE.sub("", text)
        text = HtmlCleaner.MARKDOWN_BLOCKQUOTE_RE.sub("", text)
        text = HtmlCleaner.MARKDOWN_THEMATIC_BREAK_RE.sub("", text)
        text = HtmlCleaner.ENTITY_RE.sub(" ", text)
        text = HtmlCleaner.WHITESPACE_RE.sub(" ", text)
        return text.strip()

    @staticmethod
    def to_plain_text(
        text: str,
        strip_html_first: bool = True,
        strip_markdown: bool = True,
    ) -> str:
        """Convert any text format to clean plain text.

        Args:
            text: Input text (HTML, Markdown, or plain)
            strip_html_first: Whether to strip HTML tags first
            strip_markdown: Whether to strip Markdown formatting

        Returns:
            Clean plain text string.
        """
        if not text or not isinstance(text, str):
            return ""
        result = text
        if strip_html_first and HtmlCleaner.is_html(result):
            result = HtmlCleaner.strip_html(result)
        if strip_markdown and HtmlCleaner.is_markdown(result):
            result = HtmlCleaner.strip_markdown(result)
        return result.strip()

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse multiple whitespace characters into a single space."""
        if not text:
            return ""
        return HtmlCleaner.WHITESPACE_RE.sub(" ", text).strip()
