"""Retry and circuit breaker utilities.

tenacity: exponential backoff with jitter for external API calls
pybreaker: circuit breaker for reMarkable Cloud API (fail_max=5, reset=60s)
"""

from __future__ import annotations

from typing import Any

import pybreaker
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

try:
    import httpx as _httpx

    _http_errors: tuple[type[Exception], ...] = (
        requests.HTTPError,
        _httpx.HTTPStatusError,
        ConnectionError,
    )
except ImportError:
    _http_errors = (requests.HTTPError, ConnectionError)


def make_retry_decorator(
    max_attempts: int = 5,
    initial_wait: float = 1.0,
    max_wait: float = 60.0,
    jitter: float = 2.0,
) -> Any:
    """Build a tenacity retry decorator for external API calls.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        initial_wait: Initial wait in seconds (doubles each attempt).
        max_wait: Maximum wait between retries in seconds.
        jitter: Random jitter added to each wait in seconds.

    Returns:
        tenacity retry decorator.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait, jitter=jitter),
        retry=retry_if_exception_type(_http_errors),
        reraise=True,
    )


def make_circuit_breaker(
    fail_max: int = 5,
    reset_timeout: int = 60,
    success_threshold: int = 3,
) -> pybreaker.CircuitBreaker:
    """Build a pybreaker CircuitBreaker for the reMarkable API.

    Args:
        fail_max: Failures before opening the circuit.
        reset_timeout: Seconds before trying again after opening.
        success_threshold: Successes in half-open state to close circuit.

    Returns:
        pybreaker.CircuitBreaker instance.
    """
    return pybreaker.CircuitBreaker(
        fail_max=fail_max,
        reset_timeout=reset_timeout,
        success_threshold=success_threshold,
    )


# Module-level circuit breaker for reMarkable API calls — shared across all
# RemarkableClient instances in the same process.
remarkable_breaker: pybreaker.CircuitBreaker = make_circuit_breaker()
