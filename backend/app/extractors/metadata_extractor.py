from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.collectors.models import CompanyData, JobMetadata
from app.extractors.base import BaseExtractor


class MetadataExtractor(BaseExtractor[dict[str, Any]]):
    """Extract metadata fields (IDs, dates, tags, company info) from
    a canonical field dictionary.

    Returns a dict with keys:
      - ``source``, ``source_job_id``, ``job_url``, ``apply_url``,
        ``posted_at``, ``company_name``, ``company_logo``,
        ``employment_type``, ``experience_level``, ``department``,
        ``skills``, ``scraped_at``
    """

    name = "metadata"

    def extract(
        self,
        raw: Any,
        **context: Any,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "source": "unknown",
            "source_job_id": "",
            "job_url": "",
            "apply_url": None,
            "posted_at": None,
            "company_name": "",
            "company_logo": None,
            "employment_type": None,
            "experience_level": None,
            "department": None,
            "skills": [],
            "tags": [],
            "scraped_at": datetime.utcnow(),
        }

        if not isinstance(raw, dict):
            return result

        result["source"] = raw.get("source", "unknown") or "unknown"
        result["source_job_id"] = str(raw.get("source_job_id", ""))
        result["job_url"] = str(raw.get("job_url", ""))
        result["apply_url"] = raw.get("apply_url") or result["job_url"]
        result["company_name"] = str(raw.get("company_name", ""))
        result["company_logo"] = raw.get("company_logo")
        result["employment_type"] = raw.get("employment_type_raw")
        result["experience_level"] = raw.get("experience_level_raw")
        result["department"] = raw.get("department")
        result["skills"] = raw.get("skills_raw") or []
        result["tags"] = raw.get("tags") or []

        posted_at = self._parse_posted_at(raw)
        if posted_at:
            result["posted_at"] = posted_at

        return result

    def _parse_posted_at(self, raw: dict[str, Any]) -> Optional[datetime]:
        raw_str = raw.get("posted_at_raw")
        raw_ms = raw.get("posted_at_raw_ms")

        if raw_str and isinstance(raw_str, str) and raw_str.strip():
            try:
                text = raw_str.strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                pass

        if raw_ms is not None:
            try:
                ts = float(raw_ms)
                if ts > 1000000000000:
                    ts = ts / 1000.0
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                pass

        if raw_str and isinstance(raw_str, str) and raw_str.strip():
            try:
                ts = float(raw_str)
                if ts > 1000000000:
                    if ts > 1000000000000:
                        ts = ts / 1000.0
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (ValueError, TypeError):
                pass

        return None

    def build_job_metadata(self, meta: dict[str, Any]) -> JobMetadata:
        """Build a ``JobMetadata`` model from extracted metadata dict."""
        return JobMetadata(
            source=meta.get("source", "unknown"),
            source_job_id=meta.get("source_job_id", ""),
            job_url=meta.get("job_url", ""),
            apply_url=meta.get("apply_url"),
            posted_at=meta.get("posted_at"),
            scraped_at=meta.get("scraped_at", datetime.utcnow()),
        )

    def build_company_data(self, meta: dict[str, Any]) -> CompanyData:
        """Build a ``CompanyData`` model from extracted metadata dict."""
        return CompanyData(
            name=meta.get("company_name", ""),
            logo_url=meta.get("company_logo"),
        )
