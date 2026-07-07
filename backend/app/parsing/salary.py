from __future__ import annotations

import re
from typing import Optional

from app.collectors.logging import CollectorLoggerProtocol
from app.parsing.exceptions import ParseError
from app.parsing.models import ParsedSalary
from app.parsing.text import TextParser


class SalaryParser:
    """Parse salary strings from job listings into structured ParsedSalary.

    Supports formats:
      - "$120k", "$90,000", "€70k"
      - "₹8 LPA", "₹10–15 LPA"
      - "$80k - $120k", "$100,000 - $150,000"
      - "Competitive", "Negotiable", "Unknown"
      - "/hr", "/year", "/month", "per hour", "per annum"
    """

    CURRENCY_SYMBOLS: dict[str, str] = {
        "$": "USD",
        "\u20ac": "EUR",
        "\u00a3": "GBP",
        "\u00a5": "JPY",
        "\u20b9": "INR",
        "Rs": "INR",
        "R$": "BRL",
        "A$": "AUD",
        "C$": "CAD",
        "HK$": "HKD",
        "NT$": "TWD",
        "S$": "SGD",
        "z\u0142": "PLN",
        "\u20bd": "RUB",
        "kr": "SEK",
        "CHF": "CHF",
        "NOK": "NOK",
        "DKK": "DKK",
    }

    INTERVAL_KEYWORDS: dict[str, str] = {
        "per hour": "hourly",
        "/hr": "hourly",
        "/hour": "hourly",
        "an hour": "hourly",
        "hourly": "hourly",
        "per month": "monthly",
        "/mo": "monthly",
        "/month": "monthly",
        "monthly": "monthly",
        "per year": "yearly",
        "/yr": "yearly",
        "/year": "yearly",
        "per annum": "yearly",
        "annual": "yearly",
        "yearly": "yearly",
        "p.a.": "yearly",
        "per day": "daily",
        "/day": "daily",
        "daily": "daily",
        "one time": "one_time",
        "one-time": "one_time",
        "signing": "one_time",
        "sign-on": "one_time",
        "bonus": "one_time",
    }

    LPA_RE = re.compile(r"(\d[\d,]*\.?\d*)\s*LPA", re.IGNORECASE)
    LPA_RANGE_RE = re.compile(
        r"(\d[\d,]*\.?\d*)\s*[-to\u2013\u2014]+\s*(\d[\d,]*\.?\d*)\s*LPA",
        re.IGNORECASE,
    )
    K_RANGE_RE = re.compile(
        r"([\$\u20ac\u00a3\u00a5\u20b9]?)\s*(\d[\d,.]*)\s*k\s*[-to\u2013\u2014]+\s*"
        r"([\$\u20ac\u00a3\u00a5\u20b9]?)\s*(\d[\d,.]*)\s*k",
        re.IGNORECASE,
    )
    K_SINGLE_RE = re.compile(
        r"([\$\u20ac\u00a3\u00a5\u20b9]?)\s*(\d[\d,.]*)\s*k",
        re.IGNORECASE,
    )
    NUMERIC_RANGE_RE = re.compile(
        r"([\$\u20ac\u00a3\u00a5\u20b9]?)\s*(\d[\d,]*)\s*[-to\u2013\u2014]+\s*"
        r"([\$\u20ac\u00a3\u00a5\u20b9]?)\s*(\d[\d,]*)",
    )
    NUMERIC_SINGLE_RE = re.compile(r"([\$\u20ac\u00a3\u00a5\u20b9]?)\s*(\d[\d,]*)")

    UNCERTAIN_KEYWORDS = {
        "competitive", "negotiable", "unknown", "undisclosed",
        "depending on experience", "doe", "market rate",
        "to be discussed", "tbd", "varies",
    }

    def __init__(
        self,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._logger = logger

    def parse(self, raw: Optional[str]) -> Optional[ParsedSalary]:
        """Parse a salary string into structured salary data.

        Args:
            raw: Raw salary string (e.g. "$120k", "₹8 LPA", "Competitive").

        Returns:
            ParsedSalary if a salary was detected, None if uncertain/empty.
        """
        if not raw or not raw.strip():
            return None

        text = TextParser.normalize_whitespace(raw.strip())
        if not text:
            return None

        lower = text.lower()

        if lower in self.UNCERTAIN_KEYWORDS or any(
            kw in lower for kw in self.UNCERTAIN_KEYWORDS
        ):
            return None

        interval = self._detect_interval(text)
        currency = self._detect_currency(text)

        lpa_range = self.LPA_RANGE_RE.search(text)
        if lpa_range:
            return self._build_lpa(lpa_range.group(1), lpa_range.group(2), text)

        lpa_single = self.LPA_RE.search(text)
        if lpa_single:
            return self._build_lpa(lpa_single.group(1), None, text)

        k_range = self.K_RANGE_RE.search(text)
        if k_range:
            min_val = self._parse_k_value(k_range.group(2))
            max_val = self._parse_k_value(k_range.group(4))
            detected_currency = (
                self._detect_currency(k_range.group(1))
                or self._detect_currency(k_range.group(3))
                or currency
            )
            return self._build(min_val, max_val, detected_currency, interval, text)

        k_single = self.K_SINGLE_RE.search(text)
        if k_single:
            val = self._parse_k_value(k_single.group(2))
            detected_currency = currency or self._detect_currency(k_single.group(1))
            return self._build(val, None, detected_currency, interval, text)

        numeric_range = self.NUMERIC_RANGE_RE.search(text)
        if numeric_range:
            min_val = self._parse_raw_number(numeric_range.group(2))
            max_val = self._parse_raw_number(numeric_range.group(4))
            detected_currency = (
                self._detect_currency(numeric_range.group(1))
                or self._detect_currency(numeric_range.group(3))
                or currency
            )
            return self._build(min_val, max_val, detected_currency, interval, text)

        numeric_single = self.NUMERIC_SINGLE_RE.search(text)
        if numeric_single:
            val = self._parse_raw_number(numeric_single.group(2))
            detected_currency = currency or self._detect_currency(numeric_single.group(1))
            return self._build(val, None, detected_currency, interval, text)

        numbers = TextParser.extract_numbers(text)
        if len(numbers) >= 2:
            return self._build(numbers[0], numbers[-1], currency, interval, text)
        if len(numbers) == 1:
            return self._build(numbers[0], None, currency, interval, text)

        return None

    def _detect_interval(self, text: str) -> str:
        lower = text.lower()
        for keyword, interval in self.INTERVAL_KEYWORDS.items():
            if keyword in lower:
                return interval
        return "yearly"

    def _detect_currency(self, text: str) -> str:
        for symbol, code in self.CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code
        upper = text.upper()
        for code in ["USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "CHF"]:
            if code in upper:
                return code
        return "USD"

    def _parse_k_value(self, raw: str) -> int:
        raw = raw.replace(",", "")
        val = float(raw)
        return int(val * 1000)

    def _parse_raw_number(self, raw: str) -> int:
        raw = raw.replace(",", "")
        return int(float(raw))

    def _build_lpa(
        self,
        min_raw: str,
        max_raw: Optional[str],
        original: str,
    ) -> ParsedSalary:
        min_val = int(float(min_raw.replace(",", "")) * 100000)
        max_val = (
            int(float(max_raw.replace(",", "")) * 100000) if max_raw else None
        )
        return ParsedSalary(
            min=min_val,
            max=max_val,
            currency="INR",
            interval="yearly",
            original=original,
        )

    def _build(
        self,
        min_val: Optional[int],
        max_val: Optional[int],
        currency: str,
        interval: str,
        original: str,
    ) -> ParsedSalary:
        return ParsedSalary(
            min=min_val if min_val and min_val > 0 else None,
            max=max_val if max_val and max_val > 0 else None,
            currency=currency,
            interval=interval,
            original=original,
        )

    @staticmethod
    def normalize_interval(interval: str) -> str:
        mapping = {
            "hourly": "hourly",
            "daily": "daily",
            "monthly": "monthly",
            "yearly": "yearly",
            "one_time": "one_time",
            "per hour": "hourly",
            "per day": "daily",
            "per month": "monthly",
            "per year": "yearly",
            "annual": "yearly",
        }
        return mapping.get(interval.lower(), "yearly")

    @staticmethod
    def normalize_currency(code: str) -> str:
        return code.upper() if len(code) == 3 else "USD"
