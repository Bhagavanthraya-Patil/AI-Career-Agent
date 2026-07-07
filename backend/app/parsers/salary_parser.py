from __future__ import annotations

import re
from typing import Any, Optional

from app.collectors.models import SalaryData
from app.parsers.base import BaseParser
from app.parsers.config import ParserConfigProvider


class SalaryParser(BaseParser[Optional[SalaryData]]):
    """Parse and normalize salary strings from job listings.

    Supports:
      - INR: ₹8 LPA, ₹12-18 LPA, ₹10lpa, 8 LPA
      - USD: $120k, $80,000 - $120,000, $50/hr
      - EUR: €70k, €60.000 - €80.000
      - GBP: £50k
      - CAD/AUD: C$80k, A$100k
      - Ranges and single values
      - Intervals: yearly, monthly, hourly, one_time
      - Textual: "Competitive", "Negotiable", "Unknown", DOE
    """

    name = "salary"

    LOCAL_PATTERNS = [
        # INR LPA: ₹8 LPA, ₹12-18 LPA, 8 LPA, 10lpa, ₹8LPA
        (re.compile(
            r"(?:[\u20b9Rs\.]*)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(?:[-to\u2013\u2014]+)\s*"
            r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(?:LPA|lpa|Lakh|LAKHS|lakhs)",
            re.IGNORECASE,
        ), "range_inr"),
        (re.compile(
            r"(?:[\u20b9Rs\.]*)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(?:LPA|lpa|Lakh|LAKHS|lakhs)",
            re.IGNORECASE,
        ), "single_inr"),
        # INR CTC format: ₹12 CTC, 12 CTC
        (re.compile(
            r"(?:[\u20b9Rs\.]*)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(?:[-to\u2013\u2014]+)\s*"
            r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"CTC",
            re.IGNORECASE,
        ), "range_ctc"),
        (re.compile(
            r"(?:[\u20b9Rs\.]*)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*CTC",
            re.IGNORECASE,
        ), "single_ctc"),
    ]

    STANDARD_PATTERNS = [
        # Prefix-style currencies: C$80k, A$100k (must precede $ patterns)
        (re.compile(
            r"(?<![A-Za-z])([AUC])(?:A|U|D)?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?"
        ), "single_currency_prefix"),
        # Range patterns next (tried before single values)
        # $120k - $150k, €70k - €90k, £50k - £70k
        (re.compile(
            r"(?<![A-Za-z])([\$\u20ac\£])(?:AUD|CAD)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(k|K)?\s*"
            r"(?:[-to\u2013\u2014]+\s*)\s*"
            r"[\$\u20ac\£](?:AUD|CAD)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(k|K)?"
        ), "range_currency"),
        # $80,000 - $120,000
        (re.compile(
            r"(?<![A-Za-z])([\$\u20ac\£])\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(?:[-to\u2013\u2014]+)\s*"
            r"[\$\u20ac\£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        ), "range_full"),
        # Single values (tried after ranges)
        # $120k, €70k, £50k
        (re.compile(
            r"(?<![A-Za-z])([\$\u20ac\£])\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?"
        ), "single_currency_k"),
        # $50/hr, $50 per hour, €40/hour
        (re.compile(
            r"(?<![A-Za-z])([\$\u20ac\£])\s*(\d+(?:\.\d+)?)\s*"
            r"(?:/|per\s+)(?:hr|hour|h)\b"
        ), "hourly"),
        # $5,000/mo, €4,000 monthly
        (re.compile(
            r"(?<![A-Za-z])([\$\u20ac\£])\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*"
            r"(?:/|per\s+)(?:mo|month|monthly)\b"
        ), "monthly"),
    ]

    PREFIX_CURRENCY_MAP = {
        "c": "CAD",
        "a": "AUD",
        "ca": "CAD",
        "au": "AUD",
        "hk": "HKD",
        "s": "SGD",
    }

    INTERVAL_HINTS = re.compile(
        r"(?:/|per\s+)(hr|hour|h|mo|month|monthly|year|yr|yearly|annum|annual)",
        re.IGNORECASE,
    )

    TEXTUAL_VALUES = {
        "competitive": None,
        "negotiable": None,
        "unknown": None,
        "doe": None,
        "depends on experience": None,
        "undisclosed": None,
        "not specified": None,
    }

    CURRENCY_MAP = {
        "$": "USD",
        "\u20ac": "EUR",
        "\u00a3": "GBP",
        "c$": "CAD",
        "a$": "AUD",
        "\u20b9": "INR",
        "rs": "INR",
        "rs.": "INR",
        "\u00a5": "JPY",
        "\u20a9": "KRW",
        "hk$": "HKD",
        "s$": "SGD",
    }

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Any = None,
    ) -> None:
        cfg = config or ParserConfigProvider.get_salary_config()
        super().__init__(config=cfg, logger=logger)

    def parse(self, raw: Any, **context: Any) -> Optional[SalaryData]:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return None

        text = raw.strip()

        lower = text.lower()
        for textual, value in self.TEXTUAL_VALUES.items():
            if lower == textual or lower.startswith(textual):
                return None

        if self._config.get("local_formats_enabled", True):
            result = self._try_local_patterns(text)
            if result is not None:
                return result

        result = self._try_standard_patterns(text)
        if result is not None:
            return result

        numbers = self._extract_numbers(text)
        if numbers:
            currency = self._detect_currency(text)
            interval = self._detect_interval(text)
            if len(numbers) >= 2:
                return SalaryData(
                    min=numbers[0],
                    max=numbers[-1],
                    currency=currency,
                    interval=interval,
                )
            return SalaryData(
                min=numbers[0],
                currency=currency,
                interval=interval,
            )

        return None

    def _try_local_patterns(self, text: str) -> Optional[SalaryData]:
        for pattern, kind in self.LOCAL_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue

            if kind == "range_inr":
                min_val = self._parse_decimal(m.group(1))
                max_val = self._parse_decimal(m.group(2))
                if min_val is not None and max_val is not None:
                    return SalaryData(
                        min=min_val * 100000,
                        max=max_val * 100000,
                        currency="INR",
                        interval="yearly",
                    )

            if kind == "single_inr":
                val = self._parse_decimal(m.group(1))
                if val is not None:
                    return SalaryData(
                        min=val * 100000,
                        currency="INR",
                        interval="yearly",
                    )

            if kind == "range_ctc":
                min_val = self._parse_decimal(m.group(1))
                max_val = self._parse_decimal(m.group(2))
                if min_val is not None and max_val is not None:
                    return SalaryData(
                        min=min_val * 100000,
                        max=max_val * 100000,
                        currency="INR",
                        interval="yearly",
                    )

            if kind == "single_ctc":
                val = self._parse_decimal(m.group(1))
                if val is not None:
                    return SalaryData(
                        min=val * 100000,
                        currency="INR",
                        interval="yearly",
                    )

        return None

    def _try_standard_patterns(self, text: str) -> Optional[SalaryData]:
        for pattern, kind in self.STANDARD_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue

            if kind == "range_currency":
                currency_symbol = m.group(1).strip().lower()
                currency = self._map_currency(currency_symbol)
                min_val = self._parse_decimal(m.group(2))
                k1 = m.group(3)
                max_val = self._parse_decimal(m.group(4))
                k2 = m.group(5)
                if min_val is not None and max_val is not None:
                    m_mult = 1000 if (k1 and k1.lower() == "k") else 1
                    x_mult = 1000 if (k2 and k2.lower() == "k") else 1
                    return SalaryData(
                        min=min_val * m_mult,
                        max=max_val * x_mult,
                        currency=currency,
                        interval=self._detect_interval(text),
                    )

            if kind == "single_currency_k":
                currency_symbol = m.group(1).strip().lower()
                currency = self._map_currency(currency_symbol)
                val = self._parse_decimal(m.group(2))
                k_suffix = m.group(3) if m.lastindex >= 3 else None
                multiplier = 1000 if (k_suffix and k_suffix.lower() == "k") else 1
                if val is not None:
                    return SalaryData(
                        min=val * multiplier,
                        currency=currency,
                        interval=self._detect_interval(text),
                    )

            if kind == "single_currency_prefix":
                prefix = m.group(1).strip().lower()
                currency = self.PREFIX_CURRENCY_MAP.get(prefix, "USD")
                val = self._parse_decimal(m.group(2))
                k_suffix = m.group(3) if m.lastindex >= 3 else None
                multiplier = 1000 if (k_suffix and k_suffix.lower() == "k") else 1
                if val is not None:
                    return SalaryData(
                        min=val * multiplier,
                        currency=currency,
                        interval=self._detect_interval(text),
                    )

            if kind == "range_full":
                currency_symbol = m.group(1).strip().lower()
                currency = self._map_currency(currency_symbol)
                min_val = self._parse_decimal(m.group(2))
                max_val = self._parse_decimal(m.group(3))
                if min_val is not None and max_val is not None:
                    return SalaryData(
                        min=min_val,
                        max=max_val,
                        currency=currency,
                        interval=self._detect_interval(text),
                    )

            if kind == "hourly":
                currency_symbol = m.group(1).strip().lower()
                currency = self._map_currency(currency_symbol)
                val = self._parse_decimal(m.group(2))
                if val is not None:
                    return SalaryData(
                        min=val,
                        currency=currency,
                        interval="hourly",
                    )

            if kind == "monthly":
                currency_symbol = m.group(1).strip().lower()
                currency = self._map_currency(currency_symbol)
                val = self._parse_decimal(m.group(2))
                if val is not None:
                    return SalaryData(
                        min=val,
                        currency=currency,
                        interval="monthly",
                    )

        return None

    def _parse_decimal(self, s: str) -> Optional[int]:
        cleaned = s.replace(",", "").replace(" ", "")
        try:
            if "." in cleaned:
                return int(float(cleaned))
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    def _detect_currency(self, text: str) -> str:
        m = re.match(r"^\s*([^\d\s]+)", text)
        if m:
            symbol = m.group(1).strip().lower()
            mapped = self._map_currency(symbol)
            if mapped != "USD":
                return mapped
        return self._config.get("default_currency", "USD")

    def _map_currency(self, symbol: str) -> str:
        return self.CURRENCY_MAP.get(symbol, "USD")

    def _detect_interval(self, text: str) -> str:
        m = self.INTERVAL_HINTS.search(text)
        if m:
            hint = m.group(1).lower()
            if hint in ("hr", "hour", "h"):
                return "hourly"
            if hint in ("mo", "month", "monthly"):
                return "monthly"
            if hint in ("year", "yr", "yearly", "annum", "annual"):
                return "yearly"
        return self._config.get("default_interval", "yearly")

    def _extract_numbers(self, text: str) -> list[int]:
        numbers = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?", text)
        result = []
        for n in numbers:
            val = self._parse_decimal(n)
            if val is not None and val > 0:
                result.append(val)
        return result
