from typing import Any

from .redis import RedisStore

_VALKEY_SCHEMES: dict[str, str] = {
    "valkey": "redis",
    "valkey+sentinel": "redis+sentinel",
    "valkey+cluster": "redis+cluster",
}


def _translate_server(server: str | None) -> str | None:
    """Translate Valkey URL schemes for the Redis connection factories."""
    if server is None:
        return None

    scheme: str
    separator: str
    address: str
    scheme, separator, address = server.partition("://")
    return f"{_VALKEY_SCHEMES.get(scheme.lower(), scheme)}{separator}{address}"


class ValkeyStore(RedisStore):
    """Valkey store using Redis commands, Lua scripts and connection options.

    ``server`` accepts ``valkey://``, ``valkey+sentinel://`` and
    ``valkey+cluster://``, as well as existing Redis URLs. Install the
    ``valkey`` extra to use this store.

    The store inherits RedisStore's ``TYPE`` so existing Redis atomic
    actions, including custom actions, work without additional registration.
    """

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(_translate_server(server), options)
