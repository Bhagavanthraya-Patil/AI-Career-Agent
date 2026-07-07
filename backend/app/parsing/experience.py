from __future__ import annotations

import re
from typing import Optional, Union

from app.parsing.text import TextParser


class ExperienceParser:
    """Parse experience level strings into normalized values.

    Produces one of:
      - "entry"
      - "mid"
      - "senior"
      - "lead"
      - "principal"

    Also extracts numeric year ranges.
    """

    LEVEL_KEYWORDS: dict[str, str] = {
        "entry level": "entry",
        "entry-level": "entry",
        "entry": "entry",
        "junior": "entry",
        "fresher": "entry",
        "graduate": "entry",
        "new grad": "entry",
        "new graduate": "entry",
        "recent grad": "entry",
        "0 years": "entry",
        "0-1 years": "entry",
        "0-2 years": "entry",
        "1 years": "entry",
        "1+ years": "entry",
        "1-2 years": "entry",
        "1-3 years": "entry",
        "2 years": "mid",
        "2+ years": "mid",
        "2-3 years": "mid",
        "2-4 years": "mid",
        "mid level": "mid",
        "mid-level": "mid",
        "mid": "mid",
        "intermediate": "mid",
        "associate": "mid",
        "3 years": "mid",
        "3+ years": "mid",
        "3-5 years": "mid",
        "4 years": "mid",
        "4+ years": "mid",
        "4-6 years": "mid",
        "5 years": "mid",
        "5+ years": "mid",
        "5-7 years": "mid",
        "senior": "senior",
        "sr.": "senior",
        "sr": "senior",
        "6 years": "senior",
        "6+ years": "senior",
        "7 years": "senior",
        "7+ years": "senior",
        "8 years": "senior",
        "8+ years": "senior",
        "8-10 years": "senior",
        "9 years": "senior",
        "10 years": "senior",
        "10+ years": "senior",
        "lead": "lead",
        "team lead": "lead",
        "tech lead": "lead",
        "lead engineer": "lead",
        "staff": "senior",
        "staff engineer": "senior",
        "principal": "principal",
        "principal engineer": "principal",
        "architect": "principal",
        "distinguished": "principal",
        "fellow": "principal",
    }

    YEAR_RANGE_RE = re.compile(
        r"(\d+)\s*[-to\u2013\u2014+]+\s*(\d+)\s*\+?\s*(?:years?|yrs?)",
        re.IGNORECASE,
    )
    YEAR_MIN_RE = re.compile(
        r"(\d+)\s*\+?\s*(?:years?|yrs?).*(?:experience|exp)",
        re.IGNORECASE,
    )
    YEAR_BARE_RE = re.compile(r"(\d+)\s*[-to\u2013\u2014]\s*(\d+)\s*years?", re.IGNORECASE)

    def parse_level(self, raw: Optional[str]) -> Optional[str]:
        """Parse experience level from a string.

        Args:
            raw: Raw experience string (e.g. "Senior", "3+ years", "Entry Level").

        Returns:
            Normalized level string: "entry", "mid", "senior", "lead", "principal".
        """
        if not raw or not raw.strip():
            return None

        text = TextParser.clean_text(raw)
        if not text:
            return None

        lower = text.lower().strip()

        direct = self.LEVEL_KEYWORDS.get(lower)
        if direct:
            return direct

        for keyword, level in self.LEVEL_KEYWORDS.items():
            if keyword in lower:
                return level

        year_range = self.YEAR_RANGE_RE.search(lower)
        if year_range:
            avg = (int(year_range.group(1)) + int(year_range.group(2))) / 2
            return self._years_to_level(avg)

        year_min = self.YEAR_MIN_RE.search(lower)
        if year_min:
            years = int(year_min.group(1))
            return self._years_to_level(float(years))

        return None

    def parse_years(self, raw: Optional[str]) -> Optional[Union[int, tuple[int, int]]]:
        """Extract numeric year experience from a string.

        Args:
            raw: Raw experience string.

        Returns:
            Tuple of (min, max) years, or single int, or None.
        """
        if not raw or not raw.strip():
            return None

        text = TextParser.clean_text(raw)
        if not text:
            return None

        lower = text.lower()

        m = self.YEAR_RANGE_RE.search(lower)
        if m:
            return (int(m.group(1)), int(m.group(2)))

        m = self.YEAR_MIN_RE.search(lower)
        if m:
            return int(m.group(1))

        numbers = TextParser.extract_numbers(text)
        if len(numbers) >= 2:
            return (numbers[0], numbers[-1])
        if len(numbers) == 1:
            return numbers[0]

        return None

    def _years_to_level(self, avg: float) -> str:
        if avg <= 2:
            return "entry"
        if avg <= 5:
            return "mid"
        if avg <= 10:
            return "senior"
        if avg <= 15:
            return "lead"
        return "principal"

    @staticmethod
    def normalize_level(level: str) -> str:
        mapping = {
            "entry": "entry",
            "junior": "entry",
            "fresher": "entry",
            "mid": "mid",
            "intermediate": "mid",
            "associate": "mid",
            "senior": "senior",
            "sr": "senior",
            "lead": "lead",
            "staff": "senior",
            "principal": "principal",
            "architect": "principal",
            "director": "lead",
            "head": "lead",
            "manager": "mid",
        }
        return mapping.get(level.lower().strip(), level.lower().strip())
