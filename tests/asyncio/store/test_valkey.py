from typing import Any

import pytest
import redis.exceptions
from fakeredis.aioredis import FakeConnection
from throttled.asyncio import (
    MemoryStore,
    RateLimiterType,
    RedisStore,
    Throttled,
    ValkeyStore,
    per_min,
)
from throttled.asyncio.store.redis import RedisStoreBackend
from throttled.asyncio.store.valkey import ValkeyStoreBackend
from throttled.constants import StoreType
from throttled.store.valkey import translate_valkey_server

from ...valkey_support import valkey_client_options, valkey_required, valkey_url

_FAKE_OPTIONS: dict[str, Any] = {
    "REDIS_CLIENT_CLASS": "fakeredis.aioredis.FakeRedis",
    "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
}


class TestValkeyStore:
    @classmethod
    def test_accepts_atomic_action__reuses_redis(cls) -> None:
        store: ValkeyStore = ValkeyStore()
        assert StoreType.VALKEY.value == store.TYPE
        assert store.accepts_atomic_action(StoreType.REDIS.value)

    @classmethod
    @pytest.mark.parametrize(
        "server",
        [
            "valkey://localhost:6379/0",
            "valkey+sentinel://localhost:26379/mymaster",
            "valkey+cluster://c1:7000,c2:7000",
            "redis://localhost:6379/2",
        ],
    )
    def test_parse__matches_redis_store(cls, server: str) -> None:
        translated: str | None = translate_valkey_server(server)
        assert ValkeyStoreBackend._parse(server, None) == RedisStoreBackend._parse(
            translated, None
        )


@pytest.mark.asyncio
class TestAsyncValkeyStore:
    @classmethod
    async def _limited(cls, store: Any, using: str) -> list[bool]:
        throttle: Throttled = Throttled(using=using, quota=per_min(2), store=store)
        limited: list[bool] = []
        for _ in range(3):
            result: Any = await throttle.limit("user", cost=1)
            limited.append(result.limited)
        return limited

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    async def test_limit__matches_memory_and_redis(cls, using: str) -> None:
        memory: MemoryStore = MemoryStore()
        redis_store: RedisStore = RedisStore(
            server="redis://localhost:6379/12", options=_FAKE_OPTIONS
        )
        valkey_store: ValkeyStore = ValkeyStore(
            server="valkey://localhost:6379/11", options=_FAKE_OPTIONS
        )
        expected: list[bool] = await cls._limited(memory, using)
        assert await cls._limited(redis_store, using) == expected
        assert await cls._limited(valkey_store, using) == expected


async def _open_valkey() -> ValkeyStore:
    store: ValkeyStore = ValkeyStore(
        server=valkey_url(), options=valkey_client_options()
    )
    try:
        client: Any = store._backend.get_client()
        await client.ping()
        info: dict[str, Any] = await client.info("server")
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


async def _delete_prefix(store: ValkeyStore, prefix: str) -> None:
    client: Any = store._backend.get_client()
    keys: list[Any] = await client.keys(f"{prefix}*")
    if keys:
        await client.delete(*keys)


@pytest.mark.valkey
@pytest.mark.asyncio
class TestValkeyCompatibility:
    @classmethod
    async def test_store__round_trip(cls) -> None:
        store: ValkeyStore = await _open_valkey()
        try:
            await store.set("vk-key", 1, 30)
            assert await store.get("vk-key") == 1
            assert await store.exists("vk-key") is True
            assert await store.ttl("vk-key") > 0
            await store.hset("vk-hash", mapping={"field": 2})
            assert await store.hgetall("vk-hash") == {"field": 2}
        finally:
            await _delete_prefix(store, "vk-")

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    async def test_limit__matches_memory(cls, using: str) -> None:
        store: ValkeyStore = await _open_valkey()
        prefix: str = "valkey-live-async"
        try:
            memory: MemoryStore = MemoryStore()
            expected: list[bool] = await TestAsyncValkeyStore._limited(memory, using)
            live: Throttled = Throttled(
                using=using, quota=per_min(2), store=store, key_prefix=prefix
            )
            limited: list[bool] = []
            for _ in range(3):
                result: Any = await live.limit("user", cost=1)
                limited.append(result.limited)
            assert limited == expected
        finally:
            await _delete_prefix(store, prefix)
