from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from app.collectors.logging import CollectorLoggerProtocol

T = TypeVar("T")


class BaseExtractor(ABC, Generic[T]):
    """Abstract base class for all field-level extractors.

    Each extractor is responsible for normalizing exactly one aspect
    of a raw job payload (salary, location, description, metadata, etc.)
    into a structured data model.

    Subclasses must implement:
      - ``name`` (class attribute): unique extractor identifier
      - ``extract()``: the main extraction entry point

    Extractors are stateless by design. Configuration is injected
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
    def extract(self, raw: Any, **context: Any) -> T:
        """Extract and normalize data from a raw input value.

        Args:
            raw: The raw value to extract from (string, dict, or None).
            **context: Additional context (source name, canonical fields, etc.).

        Returns:
            Structured output of type T.

        Raises:
            ParsingError: If the input cannot be processed.
        """
        ...

    def can_handle(self, raw: Any) -> bool:
        """Check whether this extractor can handle the given raw value."""
        return raw is not None and (not isinstance(raw, str) or bool(raw.strip()))

    def cleanup(self) -> None:
        """Release any resources held by the extractor."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"
