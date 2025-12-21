from typing import Any

import pytest
from throttled.asyncio import BaseStore, RedisStore, constants, exceptions, types

from ...store import parametrizes


@pytest.mark.asyncio
class TestStore:
    @classmethod
    @parametrizes.STORE_EXISTS_SET_BEFORE
    @parametrizes.STORE_EXISTS_KV
    async def test_exists(
        cls,
        store: BaseStore,
        set_before: bool,
        key: types.KeyT,
        value: types.StoreValueT,
    ):
        if set_before:
            await store.set(key, value, 1)

        assert await store.exists(key) is set_before
        assert await store.get(key) == (None, value)[set_before]

    @classmethod
    @parametrizes.STORE_TTL_KEY
    @parametrizes.STORE_TTL_TIMEOUT
    async def test_ttl(cls, store: BaseStore, key: types.KeyT, timeout: int):
        await store.set(key, 1, timeout)
        assert timeout == await store.ttl(key)

    @classmethod
    async def test_ttl__not_exist(cls, store: BaseStore):
        assert await store.ttl("key") == constants.STORE_TTL_STATE_NOT_EXIST

    @classmethod
    async def test_ttl__not_ttl(cls, store: BaseStore):
        await store.hset("name", "key", 1)
        assert await store.ttl("name") == constants.STORE_TTL_STATE_NOT_TTL

    @classmethod
    @parametrizes.STORE_SET_KEY_TIMEOUT
    async def test_set(cls, store: BaseStore, key: types.KeyT, timeout: int):
        await store.set(key, 1, timeout)
        assert timeout == await store.ttl(key)

    @classmethod
    @parametrizes.store_set_raise_parametrize(exceptions.DataError)
    async def test_set__raise(
        cls,
        store: BaseStore,
        key: types.KeyT,
        timeout: Any,
        exc: type[exceptions.BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            await store.set(key, 1, timeout)

    @classmethod
    @parametrizes.STORE_GET_SET_BEFORE
    @parametrizes.STORE_GET_KV
    async def test_get(
        cls,
        store: BaseStore,
        set_before: bool,
        key: types.KeyT,
        value: types.StoreValueT,
    ):
        if set_before:
            await store.set(key, value, 1)
        assert await store.get(key) == (None, value)[set_before]

    @classmethod
    @parametrizes.STORE_HSET_PARAMETRIZE
    async def test_hset(
        cls,
        store: BaseStore,
        name: types.KeyT,
        expect: dict[types.KeyT, types.StoreValueT],
        key: types.KeyT | None,
        value: types.StoreValueT | None,
        mapping: dict[types.KeyT, types.StoreValueT] | None,
    ):
        assert await store.exists(name) is False
        assert await store.ttl(name) == constants.STORE_TTL_STATE_NOT_EXIST

        await store.hset(name, key, value, mapping)
        assert await store.exists(name) is True
        assert await store.ttl(name) == constants.STORE_TTL_STATE_NOT_TTL

        await store.expire(name, 1)
        assert await store.ttl(name) == 1
        assert await store.hgetall(name) == expect

    @classmethod
    @parametrizes.store_hset_raise_parametrize(exceptions.DataError)
    async def test_hset__raise(
        cls,
        store: BaseStore,
        params: dict[str, Any],
        exc: type[exceptions.BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            await store.hset(**params)

    @classmethod
    @parametrizes.STORE_HSET_OVERWRITE_PARAMETRIZE
    async def test_hset__overwrite(
        cls,
        store: BaseStore,
        params_list: list[dict[str, Any]],
        expected_results: list[dict[types.KeyT, types.StoreValueT]],
    ):
        key: str = "key"
        for params, expected_result in zip(params_list, expected_results, strict=False):
            await store.hset(key, **params)
            assert await store.hgetall(key) == expected_result

    @classmethod
    @parametrizes.STORE_HGETALL_PARAMETRIZE
    async def test_hgetall(
        cls,
        store: BaseStore,
        params_list: list[dict[str, Any]],
        expected_results: list[dict[types.KeyT, types.StoreValueT]],
    ):
        for params, expected_result in zip(params_list, expected_results, strict=False):
            await store.hset("name", **params)
            assert await store.hgetall("name") == expected_result


_REDIS_STORE_PARSE_COMMON_OPTIONS: dict[str, Any] = {
    "REUSE_CONNECTION": False,
    "REDIS_CLIENT_CLASS": "redis.asyncio.Redis",
    "PARSER_CLASS": "redis.asyncio.connection.DefaultParser",
    "CONNECTION_POOL_CLASS": "redis.asyncio.ConnectionPool",
}

_REDIS_STORE_PARSE_SENTINEL_OPTIONS: dict[str, Any] = {
    "SENTINEL_CLASS": "redis.asyncio.Sentinel",
    "CONNECTION_POOL_CLASS": "redis.asyncio.SentinelConnectionPool",
    "CONNECTION_FACTORY_CLASS": "throttled.store.SentinelConnectionFactory",
}

_REDIS_STORE_PARSE_EXPECTED_RESULTS: dict[str, dict[str, Any]] = {
    "standalone": {
        "server": "redis://localhost:6379/0",
        "options": {**_REDIS_STORE_PARSE_COMMON_OPTIONS},
    },
    "sentinel": {
        "server": "redis://mymaster/0",
        "options": {
            **_REDIS_STORE_PARSE_COMMON_OPTIONS,
            **_REDIS_STORE_PARSE_SENTINEL_OPTIONS,
            "SENTINELS": [("h1", 26379), ("h2", 26379)],
            "SENTINEL_KWARGS": {},
        },
    },
    "sentinel_with_auth": {
        "server": "redis://mymaster/0",
        "options": {
            **_REDIS_STORE_PARSE_COMMON_OPTIONS,
            **_REDIS_STORE_PARSE_SENTINEL_OPTIONS,
            "USERNAME": "user",
            "PASSWORD": "pass",
            "SENTINELS": [("localhost", 26379)],
            "SENTINEL_KWARGS": {"username": "user", "password": "pass"},
        },
    },
}


class TestRedisStore:
    @classmethod
    @parametrizes.redis_store_parse_parametrize(_REDIS_STORE_PARSE_EXPECTED_RESULTS)
    def test_parse(
        cls,
        redis_store: RedisStore,
        input_data: dict[str, Any],
        expected_result: dict[str, Any],
    ):
        server, options = redis_store._BACKEND_CLASS._parse(
            input_data["server"], input_data["options"]
        )
        assert server == expected_result["server"]
        assert options == expected_result["options"]
