from __future__ import annotations

from typing import Optional

from app.collectors.logging import CollectorLoggerProtocol
from app.parsing.models import ParsedLocation
from app.parsing.text import TextParser


class LocationParser:
    """Parse location strings from job listings into structured ParsedLocation.

    Supports formats:
      - "Remote", "Remote (India)", "Remote (Worldwide)"
      - "Hybrid - New York, NY"
      - "San Francisco, CA, US"
      - "London, UK"
      - "New York, NY 10001"
      - "Multiple locations"
    """

    REMOTE_KEYWORDS = {
        "remote", "anywhere", "virtual", "work from home", "wfh",
        "telecommute", "distributed", "from home", "home office",
        "remote ok", "remote okay", "remote-friendly", "remote friendly",
    }

    HYBRID_KEYWORDS = {
        "hybrid", "flexible", "mix", "partial remote", "mostly remote",
        "office some days", "2-3 days in office", "3 days in office",
    }

    ONSITE_KEYWORDS = {
        "onsite", "on-site", "in office", "in-office", "office based",
        "at office", "on premises", "on-premises",
    }

    MULTI_LOCATION_KEYWORDS = {
        "multiple", "several", "various", "multiple locations",
        "multiple cities", "nationwide",
    }

    def __init__(
        self,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._logger = logger

    def parse(self, raw: Optional[str]) -> ParsedLocation:
        """Parse a location string into structured location data.

        Args:
            raw: Raw location string (e.g. "Remote", "San Francisco, CA").

        Returns:
            ParsedLocation with detected city/state/country/remote_type.
        """
        if not raw or not raw.strip():
            return ParsedLocation(remote_type="onsite")

        text = TextParser.clean_text(raw)
        if not text:
            return ParsedLocation(remote_type="onsite")

        lower = text.lower()

        remote_type = self._detect_remote_type(lower)

        if remote_type == "remote":
            return self._parse_remote_location(text, lower)

        country = None
        state = None
        city = None
        postal_code = None

        # Extract postal code if present (US ZIP or UK Postcode)
        postal_code = self._extract_postal_code(text)

        parts = [p.strip() for p in text.split(",")]

        if len(parts) >= 3:
            city = parts[0]
            state = self._clean_state(parts[1])
            country = self._clean_country(parts[-1])
        elif len(parts) == 2:
            city = parts[0]
            state_or_country = parts[1].strip()
            if self._is_state(parts[1].strip()):
                state = state_or_country
            else:
                country = state_or_country
        elif len(parts) == 1:
            single = parts[0]
            if len(single) <= 3 and single.isalpha():
                state = single.upper()
            else:
                city = single

        return ParsedLocation(
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            remote_type=remote_type,
            full_address=text,
        )

    def _detect_remote_type(self, lower: str) -> str:
        if any(kw in lower for kw in self.REMOTE_KEYWORDS):
            return "remote"
        if any(kw in lower for kw in self.HYBRID_KEYWORDS):
            return "hybrid"
        if any(kw in lower for kw in self.ONSITE_KEYWORDS):
            return "onsite"
        return "onsite"

    def _parse_remote_location(
        self,
        text: str,
        lower: str,
    ) -> ParsedLocation:
        country = None
        city = None
        state = None

        # "Remote (India)", "Remote (Worldwide)"
        paren_match = self._extract_parenthetical(text)
        if paren_match:
            country = paren_match

        # "Remote - India", "Remote - Worldwide"
        elif " - " in text and not lower.startswith("remote - "):
            parts = text.split(" - ", 1)
            if len(parts) == 2:
                country = parts[1].strip()

        return ParsedLocation(
            city=city,
            state=state,
            country=country,
            remote_type="remote",
            full_address=text,
        )

    def _extract_parenthetical(self, text: str) -> Optional[str]:
        import re
        m = re.search(r"\(([^)]+)\)", text)
        if m:
            return m.group(1).strip()
        return None

    def _extract_postal_code(self, text: str) -> Optional[str]:
        import re
        # US ZIP code
        m = re.search(r"\b(\d{5}(?:-\d{4})?)\b", text)
        if m:
            return m.group(1)
        # UK Postcode (simplified)
        m = re.search(r"\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b", text)
        if m:
            return m.group(1)
        return None

    def _is_state(self, part: str) -> bool:
        clean = part.strip().upper()
        if len(clean) == 2 and clean.isalpha():
            return True
        us_states = {
            "alabama", "alaska", "arizona", "arkansas", "california",
            "colorado", "connecticut", "delaware", "florida", "georgia",
            "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
            "kentucky", "louisiana", "maine", "maryland", "massachusetts",
            "michigan", "minnesota", "mississippi", "missouri", "montana",
            "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
            "new york", "north carolina", "north dakota", "ohio", "oklahoma",
            "oregon", "pennsylvania", "rhode island", "south carolina",
            "south dakota", "tennessee", "texas", "utah", "vermont",
            "virginia", "washington", "west virginia", "wisconsin", "wyoming",
        }
        return clean.lower() in us_states

    def _clean_state(self, raw: str) -> str:
        clean = raw.strip()
        if len(clean) == 2:
            return clean.upper()
        return clean

    def _clean_country(self, raw: str) -> str:
        clean = raw.strip()
        country_map = {
            "us": "United States",
            "usa": "United States",
            "united states": "United States",
            "u.s.": "United States",
            "u.s.a.": "United States",
            "uk": "United Kingdom",
            "u.k.": "United Kingdom",
            "united kingdom": "United Kingdom",
        }
        lower = clean.lower()
        if lower in country_map:
            return country_map[lower]
        return clean
