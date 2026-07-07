from __future__ import annotations

from typing import Optional


class CollectorError(Exception):
    """Base exception for all collector-related errors."""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.source = source
        self.original = original
        super().__init__(message)


class AuthenticationError(CollectorError):
    """Raised when collector authentication fails (invalid/expired credentials)."""


class RateLimitError(CollectorError):
    """Raised when the source enforces a rate limit.

    Attributes:
        retry_after: Seconds to wait before retrying (from response headers).
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, source=source, original=original)


class ParsingError(CollectorError):
    """Raised when raw source data cannot be parsed into structured models."""


class ValidationError(CollectorError):
    """Raised when normalized data fails validation checks.

    Attributes:
        field: The field that failed validation.
        value: The value that caused the failure.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: object = None,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.field = field
        self.value = value
        super().__init__(message, source=source, original=original)


class StorageError(CollectorError):
    """Raised when persisting collected jobs to the database fails."""


class NetworkError(CollectorError):
    """Raised on network-level failures (timeout, DNS, connection refused).

    Attributes:
        status_code: HTTP status code if available.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.status_code = status_code
        super().__init__(message, source=source, original=original)
