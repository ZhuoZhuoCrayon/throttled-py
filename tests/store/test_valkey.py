from typing import Any

import pytest
import redis.exceptions
from fakeredis import FakeConnection
from throttled import (
    MemoryStore,
    RateLimiterType,
    RedisStore,
    Throttled,
    ValkeyStore,
    exceptions,
    per_min,
)
from throttled.constants import StoreType
from throttled.store.redis import RedisStoreBackend
from throttled.store.valkey import ValkeyStoreBackend, translate_valkey_server

from ..valkey_support import valkey_client_options, valkey_required, valkey_url

_FAKE_OPTIONS: dict[str, Any] = {
    "REDIS_CLIENT_CLASS": "fakeredis.FakeRedis",
    "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
}

_VALKEY_URLS: tuple[str, ...] = (
    "valkey://localhost:6379/0",
    "VALKEY://user:pass@localhost:6379/1",
    "valkey+sentinel://h1:26379,h2/mymaster",
    "valkey+sentinel://user:pass@localhost:26379/mymaster",
    "valkey+cluster://c1:7000,c2:7000,c3:7000",
    "valkey+cluster://user:pass@c1:7000",
    "redis://localhost:6379/0",
    "redis+sentinel://h1:26379,h2/mymaster",
    "redis+cluster://c1:7000,c2:7000,c3:7000",
)

_REJECTED_URLS: tuple[str, ...] = (
    "valkey://localhost:6379/0",
    "VALKEY://localhost:6379/0",
    "valkey+sentinel://localhost:26379/mymaster",
    "valkey+cluster://localhost:6379",
)


class TestValkeyStore:
    @classmethod
    def test_parse__unknown_scheme_is_left_alone(cls) -> None:
        server: str = "valkey+foo://localhost:6379/0"
        parsed: str | None
        parsed, _options = RedisStoreBackend._parse(server, None)
        assert parsed == server

    @classmethod
    def test_choice__includes_valkey(cls) -> None:
        assert StoreType.VALKEY.value in StoreType.choice()

    @classmethod
    def test_translate_server__keeps_empty(cls) -> None:
        assert translate_valkey_server(None) is None
        assert translate_valkey_server("") == ""  # noqa: PLC1901

    @classmethod
    def test_accepts_atomic_action__reuses_redis(cls) -> None:
        store: ValkeyStore = ValkeyStore()
        assert StoreType.VALKEY.value == store.TYPE
        assert store.accepts_atomic_action(StoreType.REDIS.value)
        assert store.accepts_atomic_action(StoreType.VALKEY.value)
        assert not store.accepts_atomic_action(StoreType.MEMORY.value)

    @classmethod
    @pytest.mark.parametrize("server", _VALKEY_URLS)
    def test_parse__matches_redis_store(cls, server: str) -> None:
        translated: str | None = translate_valkey_server(server)
        assert ValkeyStoreBackend._parse(server, None) == RedisStoreBackend._parse(
            translated, None
        )

    @classmethod
    @pytest.mark.parametrize("server", _REJECTED_URLS)
    def test_init__rejects_valkey_url_on_redis_store(cls, server: str) -> None:
        with pytest.raises(exceptions.DataError, match="ValkeyStore"):
            RedisStore(server=server)

    @classmethod
    def _limited(cls, store: Any, using: str) -> list[bool]:
        throttle: Throttled = Throttled(using=using, quota=per_min(2), store=store)
        return [throttle.limit("user", cost=1).limited for _ in range(3)]

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    def test_limit__matches_memory_and_redis(cls, using: str) -> None:
        memory: MemoryStore = MemoryStore()
        redis_store: RedisStore = RedisStore(
            server="redis://localhost:6379/14", options=_FAKE_OPTIONS
        )
        valkey_store: ValkeyStore = ValkeyStore(
            server="valkey://localhost:6379/15", options=_FAKE_OPTIONS
        )
        expected: list[bool] = cls._limited(memory, using)
        assert cls._limited(redis_store, using) == expected
        assert cls._limited(valkey_store, using) == expected

    @classmethod
    def test_limit__fixed_window_remaining_matches_memory(cls) -> None:
        memory: MemoryStore = MemoryStore()
        valkey_store: ValkeyStore = ValkeyStore(
            server="valkey://localhost:6379/13", options=_FAKE_OPTIONS
        )

        def remaining(store: Any) -> list[int]:
            throttle: Throttled = Throttled(
                using=RateLimiterType.FIXED_WINDOW.value,
                quota=per_min(2),
                store=store,
            )
            return [throttle.limit("user", cost=1).state.remaining for _ in range(3)]

        assert remaining(valkey_store) == remaining(memory)


def _open_valkey() -> ValkeyStore:
    store: ValkeyStore = ValkeyStore(
        server=valkey_url(), options=valkey_client_options()
    )
    try:
        client: Any = store._backend.get_client()
        client.ping()
        info: dict[str, Any] = client.info("server")
    except (redis.exceptions.RedisError, OSError, TimeoutError) as exc:
        if valkey_required():
            raise
        pytest.skip(f"Valkey is not reachable at {valkey_url()}: {exc}")
    if "valkey_version" not in info:
        message: str = f"server at {valkey_url()} is not Valkey"
        if valkey_required():
            pytest.fail(message)
        pytest.skip(message)
    return store


def _delete_prefix(store: ValkeyStore, prefix: str) -> None:
    client: Any = store._backend.get_client()
    keys: list[Any] = client.keys(f"{prefix}*")
    if keys:
        client.delete(*keys)


@pytest.mark.valkey
class TestValkeyCompatibility:
    @classmethod
    def test_info__reports_valkey_version(cls) -> None:
        store: ValkeyStore = _open_valkey()
        client: Any = store._backend.get_client()
        info: dict[str, Any] = client.info("server")
        assert info["valkey_version"]

    @classmethod
    def test_store__round_trip(cls) -> None:
        store: ValkeyStore = _open_valkey()
        try:
            store.set("vk-key", 1, 30)
            assert store.get("vk-key") == 1
            assert store.exists("vk-key") is True
            assert store.ttl("vk-key") > 0
            store.expire("vk-key", 60)
            store.hset("vk-hash", "field", 2)
            assert store.hgetall("vk-hash") == {"field": 2}
        finally:
            _delete_prefix(store, "vk-")

    @classmethod
    def test_init__accepts_redis_url(cls) -> None:
        redis_url: str | None = translate_valkey_server(valkey_url())
        store: ValkeyStore = ValkeyStore(
            server=redis_url, options=valkey_client_options()
        )
        try:
            client: Any = store._backend.get_client()
            assert client.ping() is True
        except (redis.exceptions.RedisError, OSError, TimeoutError) as exc:
            if valkey_required():
                raise
            pytest.skip(f"Valkey is not reachable at {redis_url}: {exc}")

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    def test_limit__matches_memory(cls, using: str) -> None:
        store: ValkeyStore = _open_valkey()
        prefix: str = "valkey-live"
        try:
            memory: MemoryStore = MemoryStore()
            expected: list[bool] = TestValkeyStore._limited(memory, using)
            live: Throttled = Throttled(
                using=using, quota=per_min(2), store=store, key_prefix=prefix
            )
            assert [live.limit("user", cost=1).limited for _ in range(3)] == expected
        finally:
            _delete_prefix(store, prefix)
