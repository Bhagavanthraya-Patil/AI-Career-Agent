from __future__ import annotations

import re
from typing import Any, Optional

from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider
from app.parsers.models import ParsedEmploymentType


class EmploymentTypeParser(BaseParser[ParsedEmploymentType]):
    """Parse and normalize employment type strings.

    Normalizes to one of:
      - full-time
      - part-time
      - contract
      - temporary
      - internship
      - freelance
      - volunteer

    Handles synonyms, abbreviations, and common variations.
    """

    name = "employment_type"

    STANDARD_TYPES = [
        "full-time", "part-time", "contract", "temporary",
        "internship", "freelance", "volunteer",
    ]

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        cfg = config or ParserConfigProvider.get_employment_config()
        super().__init__(config=cfg, logger=logger)

    def parse(self, raw: Any, **context: Any) -> ParsedEmploymentType:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return ParsedEmploymentType(original=str(raw or ""))

        text = raw.strip()
        lower = text.lower().strip()

        normalized = self._lookup_synonym(lower)
        if normalized:
            return ParsedEmploymentType(
                normalized=normalized,
                original=text,
                is_remote_friendly=normalized in ("full-time", "contract", "freelance"),
            )

        for std_type in self.STANDARD_TYPES:
            if std_type in lower or lower in std_type:
                return ParsedEmploymentType(
                    normalized=std_type,
                    original=text,
                    is_remote_friendly=std_type in ("full-time", "contract", "freelance"),
                )

        underscore_version = lower.replace(" ", "-").replace("_", "-")
        for std_type in self.STANDARD_TYPES:
            if underscore_version == std_type:
                return ParsedEmploymentType(
                    normalized=std_type,
                    original=text,
                    is_remote_friendly=std_type in ("full-time", "contract", "freelance"),
                )

        return ParsedEmploymentType(
            normalized=lower.replace(" ", "-"),
            original=text,
        )

    def _lookup_synonym(self, lower: str) -> Optional[str]:
        synonyms = self._config.get("synonyms", {})

        direct = synonyms.get(lower)
        if direct:
            return direct

        for raw_syn, normalized in synonyms.items():
            if raw_syn in lower or lower in raw_syn:
                return normalized

        match = re.match(r"^(\w[\w\s/-]*\w)", lower)
        if match:
            first_word = match.group(1).strip()
            return synonyms.get(first_word)

        return None
