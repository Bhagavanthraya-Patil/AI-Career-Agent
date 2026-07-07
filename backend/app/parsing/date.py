from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from app.parsing.text import TextParser


class DateParser:
    """Parse date strings from job listings into datetime objects.

    Supports multiple formats commonly found in job postings:
      - ISO 8601: "2024-01-15", "2024-01-15T10:30:00Z"
      - US: "01/15/2024", "Jan 15, 2024", "January 15, 2024"
      - EU: "15/01/2024", "15 Jan 2024", "15 January 2024"
      - Relative: "2 days ago", "3 weeks ago", "posted yesterday"
      - Ordinal: "Jan 15th, 2024", "15th Jan 2024"
      - Epoch timestamps: 1705315200
    """

    RELATIVE_PATTERNS = [
        (re.compile(r"just\s*now", re.IGNORECASE), 0),
        (re.compile(r"(\d+)\s*(second|sec|s)\b", re.IGNORECASE), 1),
        (re.compile(r"(\d+)\s*(minute|min|m)\b", re.IGNORECASE), 60),
        (re.compile(r"(\d+)\s*(hour|hr|h)\b", re.IGNORECASE), 3600),
        (re.compile(r"(\d+)\s*(day|d)\b", re.IGNORECASE), 86400),
        (re.compile(r"(\d+)\s*(week|wk|w)\b", re.IGNORECASE), 604800),
        (re.compile(r"(\d+)\s*(month|mon|mo)\b", re.IGNORECASE), 2592000),
        (re.compile(r"(\d+)\s*(year|yr|y)\b", re.IGNORECASE), 31536000),
        (re.compile(r"yesterday", re.IGNORECASE), 86400),
        (re.compile(r"today", re.IGNORECASE), 0),
    ]

    MONTH_NAMES = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12,
    }

    DATE_FORMATS = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%B %d %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%b %d %Y",
        "%d %b %Y",
        "%Y/%m/%d",
    ]

    def __init__(self) -> None:
        self._ordinal_re = re.compile(r"(\d+)(st|nd|rd|th)")

    def parse(self, raw: Optional[str]) -> Optional[datetime]:
        """Parse a date string into a datetime object.

        Args:
            raw: Date string in various formats.

        Returns:
            Parsed datetime in UTC, or None if parsing fails.
        """
        if not raw or not raw.strip():
            return None

        text = TextParser.clean_text(raw.strip())
        if not text:
            return None

        epoch = self._try_parse_epoch(text)
        if epoch is not None:
            return epoch

        relative = self._try_parse_relative(text)
        if relative is not None:
            return relative

        text = self._ordinal_re.sub(r"\1", text)

        text = text.strip()

        for fmt in self.DATE_FORMATS:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

        return None

    def _try_parse_epoch(self, text: str) -> Optional[datetime]:
        try:
            ts = int(text.strip())
            if ts > 1000000000:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, TypeError):
            pass
        return None

    def _try_parse_relative(self, text: str) -> Optional[datetime]:
        lower = text.lower().strip()
        now = datetime.now(timezone.utc)

        # "posted X ago", "X ago"
        ago_match = re.search(r"(\d+\s+\w+)\s+ago", lower)
        if ago_match:
            lower = ago_match.group(1)

        for pattern, multiplier in self.RELATIVE_PATTERNS:
            m = pattern.search(lower)
            if m:
                if multiplier == 0:
                    return now
                try:
                    num = int(m.group(1))
                    seconds = num * multiplier
                    return datetime.fromtimestamp(
                        now.timestamp() - seconds,
                        tz=timezone.utc,
                    )
                except (ValueError, IndexError):
                    continue

        return None

    @staticmethod
    def is_expired(
        closing_date: Optional[datetime],
        reference: Optional[datetime] = None,
    ) -> bool:
        if closing_date is None:
            return False
        ref = reference or datetime.now(timezone.utc)
        return closing_date < ref

    @staticmethod
    def days_since(dt: Optional[datetime]) -> Optional[int]:
        if dt is None:
            return None
        delta = datetime.now(timezone.utc) - dt
        return max(0, delta.days)

    @staticmethod
    def format_date(dt: Optional[datetime], fmt: str = "%Y-%m-%d") -> Optional[str]:
        if dt is None:
            return None
        return dt.strftime(fmt)
