from __future__ import annotations

import re
from typing import Any, Callable, Optional


PathFunc = Callable[[dict[str, Any]], Any]


def _get_in(d: dict[str, Any], path: str, default: Any = None) -> Any:
    """Traverse a nested dict using a dot-separated path."""
    parts = path.split(".")
    current: Any = d
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


class FieldMapper:
    """Maps raw collector payloads to a canonical field dictionary.

    Each source (Greenhouse, Lever, Ashby, Workday, RemoteOK, or unknown)
    has a registered mapping that translates its field layout into a
    consistent set of canonical keys that extractors can consume.
    """

    SOURCE_MAP: dict[str, dict[str, PathFunc]] = {}

    @classmethod
    def _init_maps(cls) -> None:
        if cls.SOURCE_MAP:
            return

        cls.SOURCE_MAP = {
            "greenhouse": {
                "title": lambda d: d.get("title", ""),
                "company_name": lambda d: (
                    d.get("offices", [{}])[0].get("name", "")
                    if d.get("offices")
                    else ""
                ),
                "company_logo": lambda d: None,
                "location_raw": lambda d: (
                    d.get("location", {}).get("name", "")
                    if isinstance(d.get("location"), dict)
                    else str(d.get("location", ""))
                ),
                "salary_raw": cls._greenhouse_salary,
                "employment_type_raw": cls._greenhouse_metadata("employment", "job type"),
                "experience_level_raw": cls._greenhouse_metadata("experience", "level"),
                "description_html": lambda d: d.get("content", ""),
                "description_raw": lambda d: None,
                "job_url": lambda d: d.get("absolute_url", ""),
                "apply_url": lambda d: d.get("absolute_url", ""),
                "posted_at_raw": lambda d: d.get("created_at", ""),
                "posted_at_raw_ms": lambda d: None,
                "source_job_id": lambda d: str(d.get("id", "")),
                "source": lambda d: "greenhouse",
                "department": lambda d: None,
                "tags": lambda d: [],
                "skills_raw": lambda d: [],
                "is_remote": cls._greenhouse_is_remote,
                "raw_data": lambda d: d,
            },
            "lever": {
                "title": lambda d: d.get("text", ""),
                "company_name": lambda d: (
                    d.get("categories", {}).get("team", "")
                    or ""
                ),
                "company_logo": lambda d: None,
                "location_raw": lambda d: d.get("categories", {}).get("location", ""),
                "salary_raw": lambda d: d.get("additional", ""),
                "employment_type_raw": lambda d: d.get("categories", {}).get("commitment", ""),
                "experience_level_raw": lambda d: None,
                "description_html": cls._lever_description_html,
                "description_raw": lambda d: d.get("descriptionPlain", ""),
                "job_url": lambda d: d.get("hostedUrl", ""),
                "apply_url": lambda d: d.get("hostedUrl", ""),
                "posted_at_raw": lambda d: None,
                "posted_at_raw_ms": lambda d: d.get("createdAt"),
                "source_job_id": lambda d: str(d.get("id", "")),
                "source": lambda d: "lever",
                "department": lambda d: None,
                "tags": lambda d: [],
                "skills_raw": lambda d: [],
                "is_remote": lambda d: None,
                "raw_data": lambda d: d,
            },
            "ashby": {
                "title": lambda d: d.get("title", ""),
                "company_name": lambda d: d.get("companyName", ""),
                "company_logo": lambda d: None,
                "location_raw": lambda d: (
                    d.get("locations", [None])[0] if d.get("locations") else ""
                ),
                "salary_raw": lambda d: d.get("compensationSummary", ""),
                "employment_type_raw": lambda d: d.get("type", ""),
                "experience_level_raw": lambda d: None,
                "description_html": lambda d: d.get("description", ""),
                "description_raw": lambda d: None,
                "job_url": lambda d: d.get("postingUrl", ""),
                "apply_url": lambda d: d.get("applyUrl") or d.get("postingUrl", ""),
                "posted_at_raw": lambda d: d.get("publishedAt", ""),
                "posted_at_raw_ms": lambda d: None,
                "source_job_id": lambda d: str(d.get("id", "")),
                "source": lambda d: "ashby",
                "department": lambda d: d.get("department", ""),
                "tags": lambda d: [],
                "skills_raw": lambda d: (
                    [d["department"]]
                    if d.get("department")
                    else []
                ),
                "is_remote": lambda d: None,
                "raw_data": lambda d: d,
            },
            "workday": {
                "title": lambda d: d.get("title", ""),
                "company_name": lambda d: d.get("company", ""),
                "company_logo": lambda d: None,
                "location_raw": lambda d: d.get("location", ""),
                "salary_raw": lambda d: None,
                "employment_type_raw": cls._workday_employment_type,
                "experience_level_raw": cls._workday_experience_level,
                "description_html": lambda d: (
                    d.get("jobPostingInfo", {}).get("jobDescription", "")
                    if isinstance(d.get("jobPostingInfo"), dict)
                    else ""
                ),
                "description_raw": lambda d: None,
                "job_url": cls._workday_job_url,
                "apply_url": cls._workday_job_url,
                "posted_at_raw": lambda d: d.get("postedOn", ""),
                "posted_at_raw_ms": lambda d: None,
                "source_job_id": cls._workday_source_job_id,
                "source": lambda d: "workday",
                "department": lambda d: None,
                "tags": lambda d: [],
                "skills_raw": lambda d: [],
                "is_remote": cls._workday_is_remote,
                "raw_data": lambda d: d,
            },
            "remoteok": {
                "title": lambda d: d.get("title", ""),
                "company_name": lambda d: d.get("company", "Unknown"),
                "company_logo": lambda d: d.get("company_logo", ""),
                "location_raw": lambda d: d.get("location", ""),
                "salary_raw": lambda d: None,
                "salary_min_raw": lambda d: d.get("salary_min"),
                "salary_max_raw": lambda d: d.get("salary_max"),
                "employment_type_raw": cls._remoteok_employment_type,
                "experience_level_raw": lambda d: None,
                "description_html": lambda d: d.get("description", ""),
                "description_raw": lambda d: None,
                "job_url": lambda d: d.get("url", ""),
                "apply_url": lambda d: d.get("apply_url") or d.get("url", ""),
                "posted_at_raw": lambda d: d.get("date") or d.get("created_at", ""),
                "posted_at_raw_ms": lambda d: d.get("epoch"),
                "source_job_id": lambda d: str(d.get("id", "")),
                "source": lambda d: "remoteok",
                "department": lambda d: None,
                "tags": cls._remoteok_tags,
                "skills_raw": cls._remoteok_tags,
                "is_remote": lambda d: "remote",
                "raw_data": lambda d: d,
            },
        }

    @classmethod
    def register_source(
        cls,
        source: str,
        field_map: dict[str, PathFunc],
    ) -> None:
        """Register a custom source field mapping.

        Args:
            source: Source name (e.g., 'linkedin', 'indeed').
            field_map: Dict mapping canonical field names to extractor functions.
        """
        cls.SOURCE_MAP[source] = field_map

    @classmethod
    def map(cls, raw_data: dict[str, Any], source: str) -> dict[str, Any]:
        """Map a raw collector payload to a canonical field dictionary.

        Args:
            raw_data: Raw job dict from a collector.
            source: Source name (greenhouse, lever, ashby, workday, remoteok).

        Returns:
            Canonical dict with standardized field names.
        """
        cls._init_maps()
        field_map = cls.SOURCE_MAP.get(source)
        if field_map is None:
            field_map = cls._unknown_source_map(raw_data, source)

        result: dict[str, Any] = {}
        for canon_key, extractor_fn in field_map.items():
            try:
                result[canon_key] = extractor_fn(raw_data)
            except (KeyError, IndexError, TypeError, ValueError):
                result[canon_key] = None

        result["source"] = result.get("source", source)
        return result

    @classmethod
    def _unknown_source_map(
        cls,
        raw_data: dict[str, Any],
        source: str,
    ) -> dict[str, PathFunc]:
        """Build a best-effort mapping for unknown sources."""
        known_keys = {
            "title": {"title", "job_title", "position", "name", "role"},
            "company_name": {"company", "company_name", "employer", "organization"},
            "location_raw": {"location", "locations", "address", "city"},
            "description_html": {"description", "description_html", "body", "content"},
            "job_url": {"url", "job_url", "link", "apply_url", "hostedUrl"},
            "source_job_id": {"id", "job_id", "external_id", "reference_id"},
        }

        def _best_match(canon: str, possible_keys: set[str]) -> PathFunc:
            def _extract(d: dict[str, Any]) -> Any:
                for k in possible_keys:
                    if k in d:
                        return d[k]
                return None
            return _extract

        field_map: dict[str, PathFunc] = {}
        for canon, possible in known_keys.items():
            field_map[canon] = _best_match(canon, possible)

        field_map["title"] = _best_match("title", known_keys["title"])
        field_map["company_name"] = _best_match("company_name", known_keys["company_name"])
        field_map["company_logo"] = lambda d: None
        field_map["location_raw"] = _best_match("location_raw", known_keys["location_raw"])
        field_map["salary_raw"] = lambda d: None
        field_map["salary_min_raw"] = lambda d: d.get("salary_min") or d.get("min_salary")
        field_map["salary_max_raw"] = lambda d: d.get("salary_max") or d.get("max_salary")
        field_map["employment_type_raw"] = lambda d: d.get("employment_type") or d.get("type")
        field_map["experience_level_raw"] = lambda d: d.get("experience_level") or d.get("level")
        field_map["description_html"] = _best_match("description_html", known_keys["description_html"])
        field_map["description_raw"] = lambda d: d.get("description_raw") or d.get("descriptionPlain")
        field_map["job_url"] = _best_match("job_url", known_keys["job_url"])
        field_map["apply_url"] = lambda d: d.get("apply_url") or d.get("hostedUrl") or d.get("url")
        field_map["posted_at_raw"] = lambda d: d.get("posted_at") or d.get("postedAt") or d.get("date")
        field_map["posted_at_raw_ms"] = lambda d: d.get("createdAt") if isinstance(d.get("createdAt"), (int, float)) else None
        field_map["source_job_id"] = lambda d: str(d.get("id", d.get("job_id", d.get("external_id", ""))))
        field_map["source"] = lambda d: source
        field_map["department"] = lambda d: d.get("department") or d.get("team")
        field_map["tags"] = lambda d: d.get("tags") or d.get("keywords") or []
        field_map["skills_raw"] = lambda d: d.get("skills") or d.get("tags") or []
        field_map["is_remote"] = lambda d: None
        field_map["raw_data"] = lambda d: d
        return field_map

    @classmethod
    def _greenhouse_metadata(cls, *names: str) -> PathFunc:
        """Extract metadata value from Greenhouse metadata array by name."""
        def _extract(d: dict[str, Any]) -> Optional[str]:
            for md in d.get("metadata", []):
                md_name = (md.get("name") or "").lower()
                if any(n in md_name for n in names):
                    return str(md.get("value", "")).lower() if md.get("value") else None
            return None
        return _extract

    @classmethod
    def _greenhouse_salary(cls, d: dict[str, Any]) -> Optional[str]:
        for md in d.get("metadata", []):
            md_name = (md.get("name") or "").lower()
            if "salary" in md_name:
                return str(md.get("value", "")) if md.get("value") else None
        return None

    @classmethod
    def _greenhouse_is_remote(cls, d: dict[str, Any]) -> Optional[str]:
        for md in d.get("metadata", []):
            md_name = (md.get("name") or "").lower()
            if "remote" in md_name:
                val = str(md.get("value", "")).lower()
                if val in ("remote", "yes", "true"):
                    return "remote"
        return None

    @classmethod
    def _lever_description_html(cls, d: dict[str, Any]) -> str:
        html = d.get("description", "") or ""
        for lst in d.get("lists") or []:
            content = lst.get("content", "") or ""
            if content:
                html += "\n" + content
        return html

    @classmethod
    def _workday_employment_type(cls, d: dict[str, Any]) -> Optional[str]:
        for field in d.get("bulletFields", []):
            lower = field.lower().strip()
            if lower in ("full-time", "part-time", "contract", "temporary", "internship"):
                return lower
        return None

    @classmethod
    def _workday_experience_level(cls, d: dict[str, Any]) -> Optional[str]:
        mapping = {
            "entry": "entry", "junior": "entry",
            "mid": "mid", "intermediate": "mid",
            "senior": "senior", "sr": "senior",
            "lead": "lead", "principal": "lead", "director": "lead",
            "manager": "mid",
        }
        for field in d.get("bulletFields", []):
            lower = field.lower().strip()
            if lower in mapping:
                return mapping[lower]
        return None

    @classmethod
    def _workday_job_url(cls, d: dict[str, Any]) -> str:
        return d.get("externalPath", "")

    @classmethod
    def _workday_source_job_id(cls, d: dict[str, Any]) -> str:
        ext_path = d.get("externalPath", "")
        m = re.search(r"_(\w+)$", ext_path)
        if m:
            return m.group(1)
        return str(d.get("jobPostingId", d.get("title", "")))

    @classmethod
    def _workday_is_remote(cls, d: dict[str, Any]) -> Optional[str]:
        for field in d.get("bulletFields", []):
            lower = field.lower().strip()
            if "remote" in lower:
                return "remote"
            if "hybrid" in lower:
                return "hybrid"
        return None

    @classmethod
    def _remoteok_tags(cls, d: dict[str, Any]) -> list[str]:
        tags = d.get("tags", [])
        if isinstance(tags, str):
            try:
                import json
                parsed = json.loads(tags)
                if isinstance(parsed, list):
                    return [str(t).strip().lower() for t in parsed if t]
            except (json.JSONDecodeError, TypeError):
                return [t.strip().lower() for t in tags.split(",") if t.strip()]
        if isinstance(tags, list):
            return [str(t).strip().lower() for t in tags if t]
        return []

    @classmethod
    def _remoteok_employment_type(cls, d: dict[str, Any]) -> Optional[str]:
        tags = cls._remoteok_tags(d)
        keywords = {"full-time", "part-time", "contract", "freelance", "internship", "temporary"}
        for tag in tags:
            if tag in keywords:
                return tag
        return None
