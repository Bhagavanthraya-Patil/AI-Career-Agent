from __future__ import annotations

import re
from typing import Any, Optional

from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider
from app.parsers.models import ParsedCompany


class CompanyParser(BaseParser[ParsedCompany]):
    """Parse company-related fields from job listings.

    Extracts:
      - Company name
      - Department
      - Division / Business Unit
      - Team

    Handles hierarchy separators:
      - "Engineering > Backend > Payments Team"
      - "Product - Design - UX"
      - "Engineering / Platform / Core"
      - "Google | Cloud AI | Research"
    """

    name = "company"

    SEPARATOR_RE = re.compile(r"\s*(?:>|/|\||-|\u203a|\u00bb|::)\s*")
    HIERARCHY_KEYWORDS = {
        "department": [
            "engineering", "product", "design", "marketing", "sales",
            "finance", "hr", "human resources", "operations", "legal",
            "support", "customer success", "data", "analytics",
            "research", "security", "infrastructure", "platform",
            "devops", "qa", "quality", "mobile", "frontend",
            "backend", "fullstack", "full stack", "ml", "ai",
            "machine learning", "data science", "business development",
            "corporate", "administration", "communications", "creative",
            "content", "strategy", "partnerships", "people",
            "finance and accounting", "information technology",
            "it", "software engineering", "cloud",
        ],
        "team": [
            "team", "group", "squad", "crew", "chapter", "guild", "unit",
        ],
        "business_unit": [
            "business unit", "division", "practice", "vertical",
        ],
    }

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        super().__init__(config=config or ParserConfigProvider.get_all(), logger=logger)

    def parse(self, raw: Any, **context: Any) -> ParsedCompany:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return ParsedCompany(original=str(raw or ""))

        text = raw.strip()

        parts = self.SEPARATOR_RE.split(text)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return ParsedCompany(original=text)

        if len(parts) == 1:
            return ParsedCompany(name=parts[0], original=text)

        hierarchy = self._classify_parts(parts)
        return ParsedCompany(
            name=hierarchy.get("name", parts[0]),
            department=hierarchy.get("department"),
            team=hierarchy.get("team"),
            business_unit=hierarchy.get("business_unit"),
            original=text,
        )

    def _classify_parts(self, parts: list[str]) -> dict[str, Optional[str]]:
        result: dict[str, Optional[str]] = {
            "name": parts[0],
            "department": None,
            "team": None,
            "business_unit": None,
        }

        for part in parts[1:]:
            lower = part.lower()
            assigned = False

            for category, keywords in self.HIERARCHY_KEYWORDS.items():
                for kw in keywords:
                    if kw in lower:
                        if result[category] is None:
                            result[category] = part
                            assigned = True
                        break
                if assigned:
                    break

            if not assigned:
                if result["department"] is None:
                    result["department"] = part
                elif result["team"] is None:
                    result["team"] = part
                else:
                    result["business_unit"] = part

        return result
