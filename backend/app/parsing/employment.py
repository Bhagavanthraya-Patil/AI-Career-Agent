from __future__ import annotations

from typing import Optional

from app.parsing.text import TextParser


class EmploymentTypeParser:
    """Parse employment type strings into normalized values.

    Normalizes to one of:
      - "full-time"
      - "part-time"
      - "contract"
      - "temporary"
      - "internship"
      - "freelance"
      - "volunteer"
    """

    TYPE_MAP: dict[str, str] = {
        "full time": "full-time",
        "full-time": "full-time",
        "fulltime": "full-time",
        "full time employee": "full-time",
        "fTE": "full-time",
        "permanent": "full-time",
        "regular": "full-time",
        "part time": "part-time",
        "part-time": "part-time",
        "parttime": "part-time",
        "part time employee": "part-time",
        "pTE": "part-time",
        "contract": "contract",
        "contractor": "contract",
        "contract-to-hire": "contract",
        "c2h": "contract",
        "w2 contract": "contract",
        "fixed term": "contract",
        "fixed-term": "contract",
        "temporary": "temporary",
        "temp": "temporary",
        "temp-to-perm": "temporary",
        "seasonal": "temporary",
        "internship": "internship",
        "intern": "internship",
        "co-op": "internship",
        "coop": "internship",
        "graduate": "internship",
        "freelance": "freelance",
        "freelancer": "freelance",
        "gig": "freelance",
        "contractor - freelance": "freelance",
        "volunteer": "volunteer",
        "voluntary": "volunteer",
        "unpaid": "volunteer",
    }

    def parse(self, raw: Optional[str]) -> Optional[str]:
        """Parse a raw employment type string into a normalized value.

        Args:
            raw: Raw employment type (e.g. "Full Time", "Contractor").

        Returns:
            Normalized employment type string, or None if not recognized.
        """
        if not raw or not raw.strip():
            return None

        text = TextParser.clean_text(raw)
        if not text:
            return None

        lower = text.lower().strip()

        direct = self.TYPE_MAP.get(lower)
        if direct:
            return direct

        for raw_type, normalized in self.TYPE_MAP.items():
            if raw_type in lower:
                return normalized

        return None

    @staticmethod
    def normalize(type_str: str) -> str:
        mapping = {
            "full-time": "full-time",
            "part-time": "part-time",
            "contract": "contract",
            "temporary": "temporary",
            "internship": "internship",
            "freelance": "freelance",
            "volunteer": "volunteer",
        }
        lower = type_str.lower().replace("_", "-")
        return mapping.get(lower, lower)
