"""reMarkable device registration and token management.

Two-token JWT system:
  1. Device token (permanent) — exchanged from one-time registration code
  2. User token (short-lived, ~24h) — refreshed from device token each session

Do NOT use rmapy — it does not support sync15 and fails on migrated accounts.
"""

from __future__ import annotations

import functools
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

import requests

_F = TypeVar("_F", bound=Callable[..., Any])

DEVICE_REGISTRATION_URL = (
    "https://webapp-production-dot-remarkable-production.appspot.com/token/json/2/device/new"
)
USER_TOKEN_URL = (
    "https://webapp-production-dot-remarkable-production.appspot.com/token/json/2/user/new"
)


class AuthenticationError(Exception):
    """Raised when a reMarkable API call returns 401."""


def auto_refresh_token(max_retries: int = 1) -> Callable[[_F], _F]:
    """Decorator that retries a method once after refreshing the user token on 401.

    Args:
        max_retries: Number of refresh attempts before re-raising.

    Returns:
        Decorator that wraps instance methods on RemarkableClient.
    """

    def decorator(func: _F) -> _F:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except AuthenticationError:
                    if attempt < max_retries:
                        self._refresh_user_token()
                    else:
                        raise

        return wrapper  # type: ignore[return-value]

    return decorator


def register_device(one_time_code: str) -> str:
    """Exchange a one-time registration code for a permanent device token.

    Args:
        one_time_code: 8-character code from https://my.remarkable.com/device/desktop/connect

    Returns:
        Permanent device token JWT (store this securely).

    Raises:
        AuthenticationError: If registration fails.
    """
    resp = requests.post(
        DEVICE_REGISTRATION_URL,
        headers={"Authorization": "Bearer ", "Content-Type": "application/json"},
        json={
            "code": one_time_code,
            "deviceDesc": "desktop-linux",
            "deviceID": str(uuid.uuid4()),
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise AuthenticationError(f"Device registration failed: {resp.status_code} {resp.text}")
    return resp.text.strip()


def refresh_user_token(device_token: str) -> str:
    """Get a new short-lived user token using the permanent device token.

    Args:
        device_token: Permanent device JWT.

    Returns:
        New user token JWT (~24h expiry).

    Raises:
        AuthenticationError: If refresh fails.
    """
    resp = requests.post(
        USER_TOKEN_URL,
        headers={"Authorization": f"Bearer {device_token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise AuthenticationError(f"User token refresh failed: {resp.status_code} {resp.text}")
    return resp.text.strip()
