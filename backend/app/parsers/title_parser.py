from __future__ import annotations

import re
from typing import Any, Optional

from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider
from app.parsers.models import ParsedTitle


class TitleParser(BaseParser[ParsedTitle]):
    """Parse and normalize job titles.

    Handles:
      - Seniority prefix detection (Senior, Lead, Junior, etc.)
      - Title normalization (strip seniority, version numbers)
      - Role classification
      - Technology/stack suffixes
    """

    name = "title"

    ROLE_CATEGORIES: dict[str, list[str]] = {
        "engineering": [
            "engineer", "developer", "programmer", "software", "sde",
            "backend", "frontend", "fullstack", "full stack", "infrastructure",
            "platform", "devops", "site reliability", "sre", "data",
            "machine learning", "ml", "ai", "systems",
        ],
        "product": [
            "product manager", "product owner", "product designer",
            "technical product manager", "tpm",
        ],
        "design": [
            "designer", "ux", "ui", "user experience", "user interface",
            "product design", "visual designer", "graphic designer",
        ],
        "management": [
            "manager", "director", "vp", "vice president", "head of",
            "chief", "cto", "ceo", "coo",
        ],
        "data": [
            "data scientist", "data analyst", "data engineer",
            "analytics engineer", "data architect",
        ],
    }

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        cfg = config or ParserConfigProvider.get_title_config()
        super().__init__(config=cfg, logger=logger)

    def parse(self, raw: Any, **context: Any) -> ParsedTitle:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return ParsedTitle(original=str(raw or ""))

        text = raw.strip()
        original = text

        seniority = self._extract_seniority(text)
        normalized = self._normalize(text, seniority)

        return ParsedTitle(
            normalized=normalized,
            seniority=seniority,
            original=original,
        )

    def _extract_seniority(self, text: str) -> Optional[str]:
        prefixes = self._config.get("seniority_prefixes", [])
        lower = text.lower().strip()

        found: list[tuple[int, str]] = []
        for prefix in prefixes:
            if lower.startswith(prefix):
                found.append((len(prefix), prefix))
            elif prefix.endswith(" of") and lower.startswith(prefix):
                found.append((len(prefix), prefix))

        if not found:
            for prefix in prefixes:
                pattern = re.compile(rf"\b{re.escape(prefix)}\b", re.IGNORECASE)
                if pattern.search(lower):
                    found.append((len(prefix), prefix))

        if found:
            found.sort(key=lambda x: x[0], reverse=True)
            return found[0][1].lower().replace(" ", "-")

        seniority_map = {
            "junior": "junior", "jr": "junior",
            "senior": "senior", "sr": "senior",
            "lead": "lead",
            "principal": "principal",
            "staff": "staff",
            "chief": "chief",
            "vp": "vp",
            "vice president": "vp",
            "director": "director",
            "head": "lead",
        }

        first_word = lower.split()[0] if lower.split() else ""
        if first_word in seniority_map:
            return seniority_map[first_word]

        return None

    def _normalize(self, text: str, seniority: Optional[str]) -> str:
        normalized = text.strip()
        stopwords = self._config.get("stopwords", [])

        if seniority:
            seniority_lower = seniority.replace("-", " ")
            pattern = re.compile(rf"^{re.escape(seniority_lower)}\s+", re.IGNORECASE)
            normalized = pattern.sub("", normalized).strip()

        for stopword in stopwords:
            normalized = re.sub(
                rf"\s*{re.escape(stopword)}\s*", " ", normalized,
                flags=re.IGNORECASE,
            )

        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized
