from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from app.collectors.logging import CollectorLoggerProtocol
from app.parsing.models import ParsedMetadata
from app.parsing.text import TextParser


class MetadataParser:
    """Parse metadata fields from job listings.

    Extracts:
      - Source job IDs from URLs or identifiers
      - Source URLs
      - Apply URLs
      - Categories
      - Tags / keywords
      - Benefits
      - Languages
      - Custom fields
    """

    JOB_ID_PATTERNS = [
        re.compile(r"/jobs/(\w[\w-]+)", re.IGNORECASE),
        re.compile(r"job_id=([\w-]+)", re.IGNORECASE),
        re.compile(r"posting_id=([\w-]+)", re.IGNORECASE),
        re.compile(r"/(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})(?:\?|$|/)", re.IGNORECASE),
        re.compile(r"/(\d{5,})(?:\?|$|/)"),
        re.compile(r"([A-Z0-9]{6,})", re.IGNORECASE),
    ]

    BENEFIT_KEYWORDS = {
        "health insurance", "dental insurance", "vision insurance",
        "life insurance", "disability insurance",
        "401k", "401(k)", "retirement", "pension",
        "stock options", "equity", "rsu",
        "paid time off", "pto", "vacation", "sick leave",
        "parental leave", "maternity leave", "paternity leave",
        "flexible hours", "flexible schedule", "flex hours",
        "remote work", "work from home", "distributed team",
        "gym membership", "wellness", "mental health",
        "tuition reimbursement", "professional development",
        "conference budget", "learning budget",
        "free lunch", "catered lunch", "snacks",
        "commuter benefits", "parking",
        "relocation assistance", "relocation",
        "bonus", "sign-on bonus", "performance bonus",
        "commission", "profit sharing",
    }

    LANGUAGE_RE = re.compile(
        r"\b(English|Spanish|French|German|Chinese|Japanese|Korean|"
        r"Portuguese|Russian|Arabic|Hindi|Italian|Dutch|Polish|"
        r"Swedish|Norwegian|Danish|Finnish|Turkish|Thai|Vietnamese|"
        r"Hebrew|Greek|Czech|Romanian|Hungarian|Ukrainian)\b",
        re.IGNORECASE,
    )

    TAG_SPLIT_RE = re.compile(r"[,;/\n|]+")

    def __init__(
        self,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._logger = logger

    def parse(self, raw: dict[str, Any]) -> ParsedMetadata:
        """Parse metadata from a dictionary of raw fields.

        Args:
            raw: Dictionary of raw metadata fields.

        Returns:
            ParsedMetadata with extracted values.
        """
        result = ParsedMetadata()

        if not raw:
            return result

        result.source_job_id = self._extract_job_id(raw)
        result.job_url = self._extract_url(raw, "job_url", "url", "link", "apply_url")
        result.apply_url = self._extract_url(raw, "apply_url", "application_url")
        result.categories = self._extract_list(raw, "category", "categories", "department")
        result.tags = self._extract_tags(raw)
        result.benefits = self._extract_benefits(raw)
        result.languages = self._extract_languages(raw)
        result.custom = self._extract_custom(raw)

        return result

    def _extract_job_id(self, raw: dict[str, Any]) -> Optional[str]:
        for key in ("id", "job_id", "jobId", "posting_id", "postingId", "external_id", "reference_id"):
            value = raw.get(key)
            if value is not None:
                return str(value).strip()

        for key in ("url", "job_url", "link", "apply_url"):
            value = raw.get(key)
            if value and isinstance(value, str):
                for pattern in self.JOB_ID_PATTERNS:
                    m = pattern.search(value)
                    if m:
                        return m.group(1)

        return None

    def _extract_url(
        self,
        raw: dict[str, Any],
        *keys: str,
    ) -> Optional[str]:
        for key in keys:
            value = raw.get(key)
            if value and isinstance(value, str) and value.startswith(("http://", "https://")):
                return value.strip()
        return None

    def _extract_list(
        self,
        raw: dict[str, Any],
        *keys: str,
    ) -> list[str]:
        result: list[str] = []
        for key in keys:
            value = raw.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.strip():
                        result.append(item.strip())
            elif isinstance(value, str) and value.strip():
                parts = self.TAG_SPLIT_RE.split(value)
                for p in parts:
                    p = p.strip()
                    if p:
                        result.append(p)
        return result

    def _extract_tags(self, raw: dict[str, Any]) -> list[str]:
        tags = self._extract_list(raw, "tags", "keywords", "skills", "tech_stack")
        seen: set[str] = set()
        unique: list[str] = []
        for t in tags:
            lower = t.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(t)
        return unique

    def _extract_benefits(self, raw: dict[str, Any]) -> list[str]:
        found: list[str] = []
        text = ""

        for key in ("benefits", "perks", "compensation", "description", "description_raw"):
            value = raw.get(key)
            if value and isinstance(value, str):
                text += " " + value.lower()

        for keyword in sorted(self.BENEFIT_KEYWORDS, key=len, reverse=True):
            if keyword in text:
                found.append(keyword.title())

        seen: set[str] = set()
        unique: list[str] = []
        for f in found:
            lower = f.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(f)
        return unique

    def _extract_languages(self, raw: dict[str, Any]) -> list[str]:
        found: list[str] = []
        text = ""

        for key in ("languages", "language", "description", "requirements"):
            value = raw.get(key)
            if value and isinstance(value, str):
                text += " " + value
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        text += " " + item

        for m in self.LANGUAGE_RE.finditer(text):
            lang = m.group(1)
            if lang not in found:
                found.append(lang)

        return found

    def _extract_custom(self, raw: dict[str, Any]) -> dict[str, Any]:
        known_keys = {
            "id", "job_id", "jobId", "posting_id", "url", "job_url", "link",
            "apply_url", "title", "company", "company_name", "location",
            "description", "description_raw", "description_html",
            "salary", "salary_min", "salary_max", "salary_currency",
            "employment_type", "experience", "experience_level",
            "tags", "keywords", "skills", "benefits", "perks",
            "category", "categories", "department", "team",
            "posted_at", "posted_date", "closing_at", "closing_date",
            "languages", "language", "source", "board_token",
        }
        custom: dict[str, Any] = {}
        for key, value in raw.items():
            if key not in known_keys and value is not None:
                custom[key] = value
        return custom
