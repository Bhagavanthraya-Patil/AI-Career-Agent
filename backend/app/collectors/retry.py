from __future__ import annotations

import asyncio
import math
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar

from app.collectors.exceptions import NetworkError, RateLimitError

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class RetryStrategy:
    """Configurable retry strategy with exponential backoff and cancellation.

    This is a pure configuration and orchestration class.
    It does NOT make HTTP requests or implement any network calls.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        backoff_multiplier: float = 2.0,
        timeout_seconds: Optional[float] = None,
        retryable_exceptions: tuple[type[Exception], ...] = (
            NetworkError,
            RateLimitError,
        ),
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be >= 0")
        if backoff_multiplier <= 0:
            raise ValueError("backoff_multiplier must be > 0")

        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.timeout_seconds = timeout_seconds
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt using exponential backoff.

        delay = base * multiplier ^ attempt, capped at max_delay.
        """
        delay = self.base_delay_seconds * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay_seconds)

    async def execute(
        self,
        coro_factory: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a coroutine with retry logic.

        Args:
            coro_factory: Async callable to execute.
            *args: Positional arguments for the callable.
            **kwargs: Keyword arguments for the callable.

        Returns:
            The result of the callable.

        Raises:
            The last exception encountered if all retries are exhausted.
            asyncio.TimeoutError if timeout_seconds is exceeded.
            asyncio.CancelledError if the task is cancelled.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                if self.timeout_seconds is not None:
                    coro = coro_factory(*args, **kwargs)
                    return await asyncio.wait_for(
                        coro,
                        timeout=self.timeout_seconds,
                    )
                return await coro_factory(*args, **kwargs)

            except asyncio.CancelledError:
                raise

            except asyncio.TimeoutError:
                raise

            except self.retryable_exceptions as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)

                    if isinstance(e, RateLimitError) and e.retry_after is not None:
                        delay = max(delay, e.retry_after)

                    await asyncio.sleep(delay)
                else:
                    raise

            except Exception as e:
                raise

        if last_exception is not None:
            raise last_exception

    def __call__(
        self,
        coro_factory: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        """Use as a decorator on async functions."""

        @wraps(coro_factory)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.execute(coro_factory, *args, **kwargs)

        return wrapper


def retry(
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 60.0,
    backoff_multiplier: float = 2.0,
    timeout_seconds: Optional[float] = None,
    retryable_exceptions: tuple[type[Exception], ...] = (
        NetworkError,
        RateLimitError,
    ),
) -> Callable[[F], F]:
    """Decorator that wraps an async function with retry logic.

    Usage:

        @retry(max_retries=3, timeout_seconds=30.0)
        async def fetch_page(url: str) -> str:
            ...
    """
    strategy = RetryStrategy(
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        max_delay_seconds=max_delay_seconds,
        backoff_multiplier=backoff_multiplier,
        timeout_seconds=timeout_seconds,
        retryable_exceptions=retryable_exceptions,
    )
    return strategy  # type: ignore
