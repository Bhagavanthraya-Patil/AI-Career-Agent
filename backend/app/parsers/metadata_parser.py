from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider
from app.parsers.models import ParsedMetadata


class MetadataParser(BaseParser[ParsedMetadata]):
    """Parse metadata fields from job listing dictionaries.

    Extracts:
      - Job ID and reference ID from URLs or identifiers
      - Category tags from department or category fields
      - Technology/tag keywords
      - Posting and closing dates
      - Language detection
      - Custom fields not covered by standard schema
    """

    name = "metadata"

    JOB_ID_PATTERNS = [
        re.compile(r"/jobs/(\w[\w-]+)", re.IGNORECASE),
        re.compile(r"job_id=([\w-]+)", re.IGNORECASE),
        re.compile(r"posting_id=([\w-]+)", re.IGNORECASE),
        re.compile(r"/?p\.(\d+)(?:\?|/|$)", re.IGNORECASE),
        re.compile(r"/([A-Z0-9]{8,})(?:\?|/|$)", re.IGNORECASE),
        re.compile(r"(\d{7,})(?:\?|/|$)", re.IGNORECASE),
        re.compile(r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", re.IGNORECASE),
    ]

    DATE_PATTERNS = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
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

    LANGUAGE_RE = re.compile(
        r"\b(English|Spanish|French|German|Chinese|Japanese|Korean|"
        r"Portuguese|Russian|Arabic|Hindi|Italian|Dutch|Polish|"
        r"Swedish|Norwegian|Danish|Finnish|Turkish|Thai|Vietnamese|"
        r"Hebrew|Greek|Czech|Romanian|Hungarian|Ukrainian)\b",
        re.IGNORECASE,
    )

    KNOWN_KEYS = {
        "id", "job_id", "jobId", "posting_id", "reference_id", "req_id",
        "url", "job_url", "link", "apply_url", "title", "company",
        "company_name", "location", "description", "description_raw",
        "description_html", "salary", "salary_min", "salary_max",
        "salary_currency", "employment_type", "experience",
        "experience_level", "tags", "keywords", "skills", "benefits",
        "perks", "category", "categories", "department", "team",
        "posted_at", "posted_date", "closing_at", "closing_date",
        "languages", "language", "source", "board_token", "remote",
        "remote_type", "status", "is_active", "type",
    }

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        cfg = config or ParserConfigProvider.get_metadata_config()
        super().__init__(config=cfg, logger=logger)

    def parse(self, raw: Any, **context: Any) -> ParsedMetadata:
        if not raw or not isinstance(raw, dict):
            return ParsedMetadata(original={})

        job_id = self._extract_job_id(raw)
        reference_id = self._extract_reference_id(raw)
        categories = self._extract_categories(raw)
        tags = self._extract_tags(raw)
        posted_at = self._parse_date(raw, "posted_at", "posted_date", "date_posted")
        closing_at = self._parse_date(raw, "closing_at", "closing_date", "date_closes")
        language = self._extract_language(raw)
        custom = self._extract_custom(raw)

        return ParsedMetadata(
            job_id=job_id,
            reference_id=reference_id,
            categories=categories,
            tags=tags,
            posted_at=posted_at,
            closing_at=closing_at,
            language=language,
            custom=custom,
            original=raw,
        )

    def _extract_job_id(self, raw: dict[str, Any]) -> Optional[str]:
        for key in ("id", "job_id", "jobId", "posting_id", "external_id"):
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

    def _extract_reference_id(self, raw: dict[str, Any]) -> Optional[str]:
        for key in ("reference_id", "req_id", "requisition_id", "ref_id"):
            value = raw.get(key)
            if value is not None:
                return str(value).strip()
        return None

    def _extract_categories(self, raw: dict[str, Any]) -> list[str]:
        categories: list[str] = []
        for key in ("category", "categories", "department", "team"):
            value = raw.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.strip():
                        categories.append(item.strip())
            elif isinstance(value, str) and value.strip():
                for part in re.split(r"[,;/|]+", value):
                    part = part.strip()
                    if part:
                        categories.append(part)
        return categories

    def _extract_tags(self, raw: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for key in ("tags", "keywords", "skills", "tech_stack"):
            value = raw.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.strip():
                        tags.append(item.strip())
            elif isinstance(value, str) and value.strip():
                for part in re.split(r"[,;/|\n]+", value):
                    part = part.strip()
                    if part:
                        tags.append(part)
        return list(dict.fromkeys(tags))

    def _parse_date(self, raw: dict[str, Any], *keys: str) -> Optional[datetime]:
        date_formats = self._config.get("date_formats", self.DATE_PATTERNS)
        for key in keys:
            value = raw.get(key)
            if value is None:
                continue
            if isinstance(value, datetime):
                return value
            if isinstance(value, (int, float)) and value > 1000000000:
                try:
                    return datetime.fromtimestamp(value, tz=timezone.utc)
                except (ValueError, OSError):
                    pass
            if isinstance(value, str) and value.strip():
                text = value.strip()
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(text, fmt)
                        return dt.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        continue
        return None

    def _extract_language(self, raw: dict[str, Any]) -> Optional[str]:
        for key in ("language", "languages"):
            value = raw.get(key)
            if value and isinstance(value, str):
                m = self.LANGUAGE_RE.search(value)
                if m:
                    return m.group(1).title()
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        m = self.LANGUAGE_RE.search(item)
                        if m:
                            return m.group(1).title()
        for key in ("description", "description_raw"):
            value = raw.get(key)
            if value and isinstance(value, str):
                m = self.LANGUAGE_RE.search(value)
                if m:
                    return m.group(1).title()
        return None

    def _extract_custom(self, raw: dict[str, Any]) -> dict[str, Any]:
        custom: dict[str, Any] = {}
        for key, value in raw.items():
            if key not in self.KNOWN_KEYS and value is not None:
                custom[key] = value
        return custom
