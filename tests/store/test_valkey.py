from typing import Any

from throttled import RedisStore, ValkeyStore

from .parametrizes import VALKEY_SERVER


class TestValkeyStore:
    @classmethod
    @VALKEY_SERVER
    def test_init__reuses_redis_configuration(
        cls, server: str | None, redis_server: str | None
    ) -> None:
        options: dict[str, Any] = {
            "SOCKET_TIMEOUT": 2,
            "SENTINEL_KWARGS": {"password": "override"},
        }
        store: ValkeyStore = ValkeyStore(server=server, options=options)
        redis_store: RedisStore = RedisStore(server=redis_server, options=options)

        assert store._backend.server == redis_store._backend.server
        assert store._backend.options == redis_store._backend.options
        assert options == {
            "SOCKET_TIMEOUT": 2,
            "SENTINEL_KWARGS": {"password": "override"},
        }
