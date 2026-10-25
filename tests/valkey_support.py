import os
from typing import Any

DEFAULT_VALKEY_URL: str = "valkey://127.0.0.1:6379/15"


def valkey_url() -> str:
    """Return the Valkey URL for live compatibility tests."""
    return os.environ.get("VALKEY_URL", DEFAULT_VALKEY_URL)


def valkey_required() -> bool:
    """Return whether a missing Valkey server should fail the test."""
    return os.environ.get("VALKEY_REQUIRED") == "1"


def valkey_client_options() -> dict[str, Any]:
    """Return short socket timeouts so an absent server fails fast."""
    timeout: float = 2.0 if valkey_required() else 0.3
    return {
        "SOCKET_CONNECT_TIMEOUT": timeout,
        "SOCKET_TIMEOUT": timeout,
    }
