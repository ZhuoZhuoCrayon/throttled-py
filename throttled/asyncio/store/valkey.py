from typing import Any

from ... import constants
from ...store.valkey import translate_valkey_server
from .redis import RedisStore, RedisStoreBackend


class ValkeyStoreBackend(RedisStoreBackend):
    """Backend for async ValkeyStore.

    Accepts ``valkey://``, ``valkey+sentinel://`` and ``valkey+cluster://``
    URLs, then reuses the async Redis connection factories.
    """

    @classmethod
    def _parse(
        cls, server: str | None = None, options: dict[str, Any] | None = None
    ) -> tuple[str | None, dict[str, Any]]:
        return super()._parse(translate_valkey_server(server), options)


class ValkeyStore(RedisStore):
    """Async Valkey store.

    Reuses the async RedisStore commands and Lua scripts. See
    :class:`throttled.store.ValkeyStore` for URL schemes and options.
    """

    TYPE: str = constants.StoreType.VALKEY.value
    COMPATIBLE_ACTION_TYPES: frozenset[str] = frozenset(
        (constants.StoreType.REDIS.value,)
    )

    _BACKEND_CLASS: type[ValkeyStoreBackend] = ValkeyStoreBackend
