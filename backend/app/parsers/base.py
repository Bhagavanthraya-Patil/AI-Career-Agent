from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from app.collectors.logging import CollectorLoggerProtocol

T = TypeVar("T")


class BaseParser(ABC, Generic[T]):
    """Abstract base class for all parsers in the Parsing Rules Engine.

    Each parser is responsible for normalizing exactly one type of
    raw field value (salary, location, employment type, etc.) into
    a structured data model.

    Subclasses must implement:
      - ``name`` (class attribute): unique parser identifier
      - ``parse()``: the main parsing entry point

    Parsers are stateless by design. All configuration is injected
    via the constructor from the centralized settings layer.
    """

    name: str = "base"

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._config = config or {}
        self._logger = logger

    @abstractmethod
    def parse(self, raw: Any, **context: Any) -> T:
        """Parse a raw input value into a structured output model.

        Args:
            raw: The raw value to parse (typically a string).
            **context: Additional context (e.g., source name, locale).

        Returns:
            Parsed output of type T.

        Raises:
            ParsingError: If the input cannot be parsed.
        """
        ...

    def can_handle(self, raw: Any) -> bool:
        """Check whether this parser can handle the given raw value.

        Override in subclasses for pre-filtering support.

        Args:
            raw: The raw value to check.

        Returns:
            True if the value is non-empty and parseable.
        """
        return raw is not None and (not isinstance(raw, str) or bool(raw.strip()))

    def cleanup(self) -> None:
        """Release any resources held by the parser.

        Stateless parsers have nothing to clean up.
        Override in subclasses that hold resources.
        """

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"
