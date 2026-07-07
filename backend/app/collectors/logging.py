from __future__ import annotations

from typing import Optional, Protocol


class CollectorLoggerProtocol(Protocol):
    """Protocol defining the logging interface for collectors.

    This is a structural typing (Protocol) interface, not an ABC.
    Any logger with these methods is compatible.
    No logging provider implementation is included.
    """

    def info(self, message: str, **context: object) -> None:
        """Log an informational message.

        Args:
            message: The log message.
            **context: Structured key-value pairs for context.
        """
        ...

    def warning(self, message: str, **context: object) -> None:
        """Log a warning message.

        Args:
            message: The log message.
            **context: Structured key-value pairs for context.
        """
        ...

    def error(
        self,
        message: str,
        exception: Optional[Exception] = None,
        **context: object,
    ) -> None:
        """Log an error message.

        Args:
            message: The log message.
            exception: Optional exception to log.
            **context: Structured key-value pairs for context.
        """
        ...

    def debug(self, message: str, **context: object) -> None:
        """Log a debug message.

        Args:
            message: The log message.
            **context: Structured key-value pairs for context.
        """
        ...
