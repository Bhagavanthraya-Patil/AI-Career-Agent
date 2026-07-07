from __future__ import annotations

import re
from typing import Any, Optional

from app.collectors.models import LocationData
from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider


class LocationParser(BaseParser[LocationData]):
    """Parse and normalize location strings from job listings.

    Supports:
      - Remote: "Remote", "Work from Home", "Remote (India)", "Remote (Worldwide)"
      - Hybrid: "Hybrid", "Hybrid - New York", "Flexible"
      - Onsite: "San Francisco, CA", "New York, NY, US"
      - Multiple cities: "San Francisco or New York"
      - Country-specific: "India", "United States", "UK"
      - Full addresses with city, state, country
      - Parenthetical locations: "Bengaluru (Remote)"
    """

    name = "location"

    SEPARATORS = re.compile(r"\s*(?:[,;]|\sor\s|\s{2,}|[/|])\s*")
    REMOTE_IN_PAREN = re.compile(r"\((remote|hybrid|onsite|wfh)\)", re.IGNORECASE)
    LOCATION_IN_PAREN = re.compile(r"\(([^)]+)\)")
    COUNTRY_IN_PAREN = re.compile(r"Remote\s*\(([^)]+)\)", re.IGNORECASE)
    US_STATE_RE = re.compile(
        r"\b(A[LKSZR]|C[AOT]|D[EC]|FL|GA|HI|I[DLNA]|K[SY]|LA|M[ADEINOST]|"
        r"N[CDEHJMVY]|O[HKR]|P[AR]|RI|S[CD]|T[NX]|UT|V[AIT]|W[AIVY])\b"
    )

    COUNTRIES = {
        "us": "United States", "usa": "United States", "united states": "United States",
        "uk": "United Kingdom", "united kingdom": "United Kingdom",
        "india": "India", "canada": "Canada", "australia": "Australia",
        "germany": "Germany", "france": "France", "spain": "Spain",
        "netherlands": "Netherlands", "switzerland": "Switzerland",
        "sweden": "Sweden", "norway": "Norway", "denmark": "Denmark",
        "finland": "Finland", "singapore": "Singapore", "japan": "Japan",
        "china": "China", "brazil": "Brazil", "mexico": "Mexico",
    }

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        cfg = config or ParserConfigProvider.get_location_config()
        super().__init__(config=cfg, logger=logger)

    def parse(self, raw: Any, **context: Any) -> LocationData:
        if not raw or not isinstance(raw, str):
            return LocationData()

        text = raw.strip()
        if not text:
            return LocationData()

        remote_type = self._detect_remote_type(text)
        full_address = text

        if remote_type == "remote":
            country = self._extract_remote_country(text)
            if country:
                return LocationData(
                    country=country,
                    remote_type="remote",
                    full_address=full_address,
                )
            return LocationData(
                remote_type="remote",
                full_address=full_address,
            )

        city, state, country = self._extract_location_parts(text)

        if remote_type == "hybrid" and city:
            return LocationData(
                city=city,
                state=state,
                country=country,
                remote_type="hybrid",
                full_address=full_address,
            )

        if remote_type == "hybrid":
            return LocationData(
                remote_type="hybrid",
                full_address=full_address,
            )

        return LocationData(
            city=city,
            state=state,
            country=country,
            remote_type="onsite",
            full_address=full_address,
        )

    def _detect_remote_type(self, text: str) -> str:
        lower = text.lower().strip()

        remote_keywords = self._config.get("remote_keywords", [])
        hybrid_keywords = self._config.get("hybrid_keywords", [])
        remote_suffixes = self._config.get("remote_suffixes", [])

        for kw in remote_keywords:
            if kw in lower:
                return "remote"

        for kw in hybrid_keywords:
            if kw in lower:
                return "hybrid"

        for suffix in remote_suffixes:
            if lower.endswith(suffix.lower()) or lower.startswith(suffix.lower()):
                return "remote"

        m = self.REMOTE_IN_PAREN.search(text)
        if m:
            tag = m.group(1).lower()
            if tag == "remote":
                return "remote"
            if tag in ("hybrid",):
                return "hybrid"
            if tag == "onsite":
                return "onsite"

        return "onsite"

    def _extract_remote_country(self, text: str) -> Optional[str]:
        m = self.COUNTRY_IN_PAREN.search(text)
        if m:
            country_raw = m.group(1).strip().lower()
            return self.COUNTRIES.get(country_raw, m.group(1).strip())
        return None

    def _extract_location_parts(
        self,
        text: str,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        clean = self.REMOTE_IN_PAREN.sub("", text).strip()
        clean = self.LOCATION_IN_PAREN.sub("", clean).strip()
        clean = re.sub(r"\s+", " ", clean).strip()

        parts = self.SEPARATORS.split(clean)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return None, None, None

        city: Optional[str] = None
        state: Optional[str] = None
        country: Optional[str] = None

        for part in parts:
            lower = part.lower()
            if lower in self.COUNTRIES:
                country = self.COUNTRIES[lower]
                continue

            if self.US_STATE_RE.match(part.strip().upper()):
                state = part.strip().upper()
                continue

            if re.match(r"^\d{5}(-\d{4})?$", part.strip()):
                continue

            if city is None:
                city = part.strip()

        return city, state, country
