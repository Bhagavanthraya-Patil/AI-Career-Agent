from __future__ import annotations

import re
from typing import Optional

from app.collectors.logging import CollectorLoggerProtocol
from app.parsing.models import ParsedCompany
from app.parsing.text import TextParser


class CompanyParser:
    """Parse company-related fields from job listings.

    Extracts:
      - Company name
      - Department
      - Team
      - Division / business unit

    Uses heuristics to split compound strings like:
      "Engineering > Backend > Payments Team"
      "Product - Design - UX"
    """

    SEPARATOR_RE = re.compile(r"\s*(?:>|/|\||-|::|\u203a|\u00bb)\s*")

    DEPARTMENT_KEYWORDS = {
        "engineering", "product", "design", "marketing", "sales",
        "finance", "hr", "human resources", "operations", "legal",
        "support", "customer success", "data", "analytics",
        "research", "security", "infrastructure", "platform",
        "devops", "qa", "quality", "mobile", "frontend",
        "backend", "fullstack", "full stack", "ml", "ai",
        "machine learning", "data science", "business development",
        "corporate", "administration", "communications", "creative",
        "content", "strategy", "partnerships", "people",
    }

    TEAM_KEYWORDS = {
        "team", "group", "unit", "squad", "crew", "chapter", "guild",
    }

    def __init__(
        self,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._logger = logger

    def parse(self, name: Optional[str]) -> ParsedCompany:
        """Parse a company name/organization string.

        Accepts either a simple company name or a compound string
        with department/team separators.

        Args:
            name: Raw company string (e.g. "Google", "Engineering > Backend Team").

        Returns:
            ParsedCompany with extracted name, department, team, division.
        """
        result = ParsedCompany()

        if not name or not name.strip():
            result.name = ""
            return result

        text = TextParser.clean_text(name)
        if not text:
            result.name = ""
            return result

        parts = self.SEPARATOR_RE.split(text)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) == 1:
            result.name = parts[0]
            return result

        hierarchy = self._classify_hierarchy(parts)
        result.name = hierarchy.get("name", parts[0])
        result.department = hierarchy.get("department")
        result.team = hierarchy.get("team")
        result.division = hierarchy.get("division")

        if not result.name:
            result.name = parts[0]

        return result

    def _classify_hierarchy(
        self,
        parts: list[str],
    ) -> dict[str, Optional[str]]:
        result: dict[str, Optional[str]] = {
            "name": None,
            "department": None,
            "team": None,
            "division": None,
        }

        if not parts:
            return result

        result["name"] = parts[0]

        for part in parts[1:]:
            lower = part.lower()
            if any(kw in lower for kw in self.TEAM_KEYWORDS):
                result["team"] = part
            elif any(kw in lower for kw in self.DEPARTMENT_KEYWORDS):
                result["department"] = part
            else:
                result["division"] = part

        return result

    def extract_department(self, text: Optional[str]) -> Optional[str]:
        """Extract department from a free-text string."""
        if not text:
            return None
        lower = text.lower()
        for dept in sorted(self.DEPARTMENT_KEYWORDS, key=len, reverse=True):
            if dept in lower:
                return dept.title()
        return None

    def extract_team(self, text: Optional[str]) -> Optional[str]:
        """Extract team name from a free-text string."""
        if not text:
            return None
        lower = text.lower()
        m = re.search(r"(\w+)\s+(?:team|group|squad)", lower, re.IGNORECASE)
        if m:
            return m.group(1).title()
        return None

    @staticmethod
    def normalize_name(name: str) -> str:
        return TextParser.clean_text(name) or ""
