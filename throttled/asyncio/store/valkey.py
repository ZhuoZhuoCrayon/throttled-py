from typing import Any

from ...store.valkey import _translate_server
from .redis import RedisStore


class ValkeyStore(RedisStore):
    """Async Valkey store using the Redis backend and atomic actions.

    See :class:`throttled.store.ValkeyStore` for URL schemes and options.
    """

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(_translate_server(server), options)
