"""Built-in key extraction helpers for FastAPI routes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)

_UNKNOWN_CLIENT = "unknown"


def get_remote_address(request: Request) -> str:
    """Return the direct client IP from the ASGI scope.

    :returns: ``request.client.host`` when available, otherwise the
        :data:`_UNKNOWN_CLIENT` sentinel.
    """
    client = request.client
    if client is not None and client.host:
        return client.host
    logger.warning(
        "get_remote_address: request.client is unavailable; falling back to '%s' key",
        _UNKNOWN_CLIENT,
    )
    return _UNKNOWN_CLIENT
