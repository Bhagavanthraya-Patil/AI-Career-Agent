from __future__ import annotations

from typing import Any, Optional

from app.collectors.models import SalaryData
from app.extractors.base import BaseExtractor
from app.parsers import ParserRegistry


class SalaryExtractor(BaseExtractor[Optional[SalaryData]]):
    """Extract and normalize salary data from raw job payloads.

    Delegates to ``SalaryParser`` from the Parsing Rules Engine.
    Supports three input modes:
    1. ``salary_raw`` string (Greenhouse metadata, Lever additional, Ashby
       compensationSummary)
    2. ``salary_min_raw`` / ``salary_max_raw`` numeric values (RemoteOK)
    3. ``salary_min`` / ``salary_max`` from the canonical dict directly
    """

    name = "salary"

    def extract(
        self,
        raw: Any,
        **context: Any,
    ) -> Optional[SalaryData]:
        parser = ParserRegistry.get_or_create("salary")
        if parser is None:
            return None

        if isinstance(raw, dict):
            salary_raw = raw.get("salary_raw")
            salary_min = raw.get("salary_min_raw")
            salary_max = raw.get("salary_max_raw")

            if salary_raw and isinstance(salary_raw, str) and salary_raw.strip():
                return parser.parse(salary_raw)

            if salary_min is not None or salary_max is not None:
                try:
                    min_val = int(salary_min) if salary_min is not None else None
                    max_val = int(salary_max) if salary_max is not None else None
                    if min_val is not None and min_val > 0:
                        return SalaryData(
                            min=min_val,
                            max=max_val,
                            currency=raw.get("currency", "USD"),
                            interval=raw.get("interval", "yearly"),
                        )
                except (ValueError, TypeError):
                    pass

            return None

        if isinstance(raw, str) and raw.strip():
            return parser.parse(raw)

        return None
