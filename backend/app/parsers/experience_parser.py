from __future__ import annotations

import re
from typing import Any, Optional

from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider
from app.parsers.models import ParsedExperience


class ExperienceParser(BaseParser[ParsedExperience]):
    """Parse and normalize experience level requirements.

    Supports:
      - Level keywords: Fresher, Entry, Junior, Mid, Senior, Lead, Principal
      - Year ranges: "0 Years", "0-1 Years", "1+", "2+", "5+", "10+"
      - Mixed: "5+ years of experience in Python"
      - Seniority: "Senior Software Engineer" → level=senior
      - Abbreviated: "5+ yrs", "2-4 yr exp"
    """

    name = "experience"

    YEAR_RANGE_PATTERNS = [
        re.compile(
            r"(\d+)\s*[-to\u2013\u2014]+\s*(\d+)\s*\+?\s*(?:years?|yrs?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d+)\s*[-to\u2013\u2014]+\s*(\d+)\s*\+?\s*(?:yr)",
            re.IGNORECASE,
        ),
    ]

    YEAR_MIN_PATTERNS = [
        re.compile(r"(\d+)\s*\+\s*(?:years?|yrs?)", re.IGNORECASE),
        re.compile(r"(?:years?|yrs?)\s+(\d+)\s*\+?", re.IGNORECASE),
        re.compile(r"min(?:imum)?\s+(\d+)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE),
    ]

    SINGLE_YEAR_PATTERNS = [
        re.compile(r"(\d+)\s*(?:years?|yrs?)\s+of", re.IGNORECASE),
        re.compile(r"(\d+)[\+]?\s*years?\s*(?:experience|exp)", re.IGNORECASE),
        re.compile(r"(?:experience|exp)\s+(\d+)[\+]?\s*years?", re.IGNORECASE),
    ]

    FRESHER_PATTERNS = [
        re.compile(r"\bfresher\b", re.IGNORECASE),
        re.compile(r"\b0\s*years?\b", re.IGNORECASE),
        re.compile(r"\bnew\s*grad(?:uate)?\b", re.IGNORECASE),
        re.compile(r"\bentry\s*level\b", re.IGNORECASE),
    ]

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        cfg = config or ParserConfigProvider.get_experience_config()
        super().__init__(config=cfg, logger=logger)

    def parse(self, raw: Any, **context: Any) -> ParsedExperience:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return ParsedExperience(original=str(raw or ""))

        text = raw.strip()
        lower = text.lower()

        if self._is_fresher(lower):
            return ParsedExperience(level="entry", years_min=0, years_max=0, original=text)

        year_range = self._extract_year_range(lower)
        if year_range:
            min_y, max_y = year_range
            avg = (min_y + max_y) / 2.0
            level = self._years_to_level(avg)
            return ParsedExperience(level=level, years_min=min_y, years_max=max_y, original=text)

        year_min = self._extract_min_years(lower)
        if year_min is not None:
            level = self._years_to_level(float(year_min))
            return ParsedExperience(level=level, years_min=year_min, original=text)

        level = self._detect_level_from_keywords(lower)
        if level:
            return ParsedExperience(level=level, original=text)

        return ParsedExperience(original=text)

    def _is_fresher(self, lower: str) -> bool:
        for pattern in self.FRESHER_PATTERNS:
            if pattern.search(lower):
                return True
        return False

    def _extract_year_range(self, lower: str) -> Optional[tuple[int, int]]:
        for pattern in self.YEAR_RANGE_PATTERNS:
            m = pattern.search(lower)
            if m:
                return int(m.group(1)), int(m.group(2))
        return None

    def _extract_min_years(self, lower: str) -> Optional[int]:
        for pattern in self.YEAR_MIN_PATTERNS:
            m = pattern.search(lower)
            if m:
                return int(m.group(1))
        for pattern in self.SINGLE_YEAR_PATTERNS:
            m = pattern.search(lower)
            if m:
                return int(m.group(1))
        return None

    def _detect_level_from_keywords(self, lower: str) -> Optional[str]:
        level_keywords = self._config.get("level_keywords", {})
        for level, keywords in level_keywords.items():
            for kw in keywords:
                if kw in lower:
                    return level
        return None

    def _years_to_level(self, years: float) -> str:
        year_ranges = self._config.get("year_ranges", {})
        for level, (low, high) in year_ranges.items():
            if low <= years <= high:
                return level
        return "mid"
