from typing import Any

from .. import constants
from .redis import RedisStore, RedisStoreBackend

_VALKEY_TO_REDIS_SCHEME: dict[str, str] = {
    "valkey": "redis",
    "valkey+sentinel": "redis+sentinel",
    "valkey+cluster": "redis+cluster",
}


def translate_valkey_server(server: str | None) -> str | None:
    """Rewrite a Valkey URL scheme to the Redis scheme accepted by redis-py.

    ``redis://`` URLs are returned unchanged so an existing Redis URL can
    point at a Valkey server. Valkey speaks the Redis protocol.

    :param server: Store connection string.
    :return: Connection string using a Redis scheme, or the original value.
    """
    if not server or "://" not in server:
        return server

    scheme: str
    rest: str
    scheme, rest = server.split("://", 1)
    mapped: str | None = _VALKEY_TO_REDIS_SCHEME.get(scheme.lower())
    if mapped is None:
        return server
    return f"{mapped}://{rest}"


class ValkeyStoreBackend(RedisStoreBackend):
    """Backend for sync ValkeyStore.

    Accepts ``valkey://``, ``valkey+sentinel://`` and ``valkey+cluster://``
    URLs, then reuses the Redis connection factories.
    """

    @classmethod
    def _parse(
        cls, server: str | None = None, options: dict[str, Any] | None = None
    ) -> tuple[str | None, dict[str, Any]]:
        return super()._parse(translate_valkey_server(server), options)


class ValkeyStore(RedisStore):
    """Concrete implementation of BaseStore using Valkey as backend.

    :class:`throttled.store.ValkeyStore` reuses RedisStore commands, Lua
    scripts and connection options. Valkey speaks the Redis protocol, so the
    ``redis`` or ``valkey`` extra (both install redis-py) is enough.

    ``server`` accepts ``valkey://``, ``valkey+sentinel://``,
    ``valkey+cluster://`` and the matching ``redis://`` forms.
    """

    TYPE: str = constants.StoreType.VALKEY.value
    COMPATIBLE_ACTION_TYPES: frozenset[str] = frozenset(
        (constants.StoreType.REDIS.value,)
    )

    _BACKEND_CLASS: type[ValkeyStoreBackend] = ValkeyStoreBackend
