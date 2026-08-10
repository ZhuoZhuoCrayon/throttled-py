"""Built-in key extraction helpers for Flask views."""

import logging

from flask import request

logger = logging.getLogger(__name__)

_UNKNOWN_CLIENT = "unknown"


def get_remote_address() -> str:
    """Return the direct client IP from the active request context.

    Reads the thread-local ``flask.request`` proxy, so it takes no
    arguments (Flask convention). Behind a reverse proxy, wrap the app
    with :class:`werkzeug.middleware.proxy_fix.ProxyFix` so
    ``request.remote_addr`` reflects the real client.

    :returns: ``request.remote_addr`` when available, otherwise the
        :data:`_UNKNOWN_CLIENT` sentinel.
    """
    remote_addr: str | None = request.remote_addr
    if remote_addr:
        return remote_addr
    logger.warning(
        "get_remote_address: request.remote_addr is unavailable; "
        "falling back to '%s' key",
        _UNKNOWN_CLIENT,
    )
    return _UNKNOWN_CLIENT
