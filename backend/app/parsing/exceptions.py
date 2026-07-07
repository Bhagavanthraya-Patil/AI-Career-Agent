from __future__ import annotations

from typing import Optional

from app.collectors.exceptions import ParsingError


class ParseError(ParsingError):
    """Raised when a parsing operation fails.

    Reuses the existing ParsingError from the collector framework.
    Extends with field-specific context.

    Attributes:
        field: The field being parsed when the error occurred.
        raw_value: The original value that could not be parsed.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        raw_value: object = None,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.field = field
        self.raw_value = raw_value
        super().__init__(message, source=source, original=original)
