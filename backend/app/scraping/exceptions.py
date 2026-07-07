from __future__ import annotations

from typing import Optional

from app.collectors.exceptions import CollectorError


class BrowserError(CollectorError):
    """Raised when browser-level operations fail (launch, crash, disconnect).

    Attributes:
        browser_type: The browser type that failed (chromium, firefox, webkit).
    """

    def __init__(
        self,
        message: str,
        browser_type: Optional[str] = None,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.browser_type = browser_type
        super().__init__(message, source=source, original=original)


class NavigationError(CollectorError):
    """Raised when page navigation fails (timeout, blocked, invalid URL).

    Attributes:
        url: The URL that failed to load.
        status_code: HTTP status code if available.
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        source: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        super().__init__(message, source=source, original=original)
