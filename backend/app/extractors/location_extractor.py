from __future__ import annotations

from typing import Any, Optional

from app.collectors.models import LocationData
from app.extractors.base import BaseExtractor
from app.parsers import ParserRegistry


class LocationExtractor(BaseExtractor[LocationData]):
    """Extract and normalize location data from raw job payloads.

    Delegates to ``LocationParser`` from the Parsing Rules Engine.
    Additionally handles source-specific overrides:
      - ``is_remote`` field from FieldMapper (greenhouse metadata, workday
        bulletFields)
      - ``location_raw`` string input
    """

    name = "location"

    def extract(
        self,
        raw: Any,
        **context: Any,
    ) -> LocationData:
        parser = ParserRegistry.get_or_create("location")
        if parser is None:
            return LocationData()

        location_str: Optional[str] = None
        is_remote_override: Optional[str] = None

        if isinstance(raw, dict):
            location_str = raw.get("location_raw")
            is_remote_override = raw.get("is_remote")
        elif isinstance(raw, str):
            location_str = raw

        if not location_str or not isinstance(location_str, str) or not location_str.strip():
            if is_remote_override:
                return LocationData(remote_type=is_remote_override)
            return LocationData()

        result = parser.parse(location_str)

        if is_remote_override and result.remote_type == "onsite":
            result.remote_type = is_remote_override

        return result
