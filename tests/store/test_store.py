from typing import Any

import pytest
from throttled import BaseStore, RedisStore
from throttled.constants import STORE_TTL_STATE_NOT_EXIST, STORE_TTL_STATE_NOT_TTL
from throttled.exceptions import BaseThrottledError, DataError
from throttled.types import KeyT, StoreValueT

from . import parametrizes


class TestStore:
    @classmethod
    @parametrizes.STORE_EXISTS_SET_BEFORE
    @parametrizes.STORE_EXISTS_KV
    def test_exists(
        cls, store: BaseStore, set_before: bool, key: KeyT, value: StoreValueT
    ):
        if set_before:
            store.set(key, value, 1)

        assert store.exists(key) is set_before
        assert store.get(key) == (None, value)[set_before]

    @classmethod
    @parametrizes.STORE_TTL_KEY
    @parametrizes.STORE_TTL_TIMEOUT
    def test_ttl(cls, store: BaseStore, key: KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    @classmethod
    def test_ttl__not_exist(cls, store: BaseStore):
        assert store.ttl("key") == STORE_TTL_STATE_NOT_EXIST

    @classmethod
    def test_ttl__not_ttl(cls, store: BaseStore):
        store.hset("name", "key", 1)
        assert store.ttl("name") == STORE_TTL_STATE_NOT_TTL

    @classmethod
    @parametrizes.STORE_SET_KEY_TIMEOUT
    def test_set(cls, store: BaseStore, key: KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    @classmethod
    @parametrizes.store_set_raise_parametrize(DataError)
    def test_set__raise(
        cls,
        store: BaseStore,
        key: KeyT,
        timeout: Any,
        exc: type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            store.set(key, 1, timeout)

    @classmethod
    @parametrizes.STORE_GET_SET_BEFORE
    @parametrizes.STORE_GET_KV
    def test_get(cls, store: BaseStore, set_before: bool, key: KeyT, value: StoreValueT):
        if set_before:
            store.set(key, value, 1)
        assert store.get(key) == (None, value)[set_before]

    @classmethod
    @parametrizes.STORE_HSET_PARAMETRIZE
    def test_hset(
        cls,
        store: BaseStore,
        name: KeyT,
        expect: dict[KeyT, StoreValueT],
        key: KeyT | None,
        value: StoreValueT | None,
        mapping: dict[KeyT, StoreValueT] | None,
    ):
        assert store.exists(name) is False
        assert store.ttl(name) == STORE_TTL_STATE_NOT_EXIST
        store.hset(name, key, value, mapping)
        assert store.exists(name) is True
        assert store.ttl(name) == STORE_TTL_STATE_NOT_TTL
        store.expire(name, 1)
        assert store.ttl(name) == 1
        assert store.hgetall(name) == expect

    @classmethod
    @parametrizes.store_hset_raise_parametrize(DataError)
    def test_hset__raise(
        cls,
        store: BaseStore,
        params: dict[str, Any],
        exc: type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            store.hset(**params)

    @classmethod
    @parametrizes.STORE_HSET_OVERWRITE_PARAMETRIZE
    def test_hset__overwrite(
        cls,
        store: BaseStore,
        params_list: list[dict[str, Any]],
        expected_results: list[dict[KeyT, StoreValueT]],
    ):
        key: str = "key"
        for i, params in enumerate(params_list):
            store.hset(key, **params)
            assert store.hgetall(key) == expected_results[i]


_REDIS_STORE_PARSE_EXPECTED_RESULTS: dict[str, dict[str, Any]] = {
    "standalone": {
        "server": "redis://localhost:6379/0",
        "options": {},
    },
    "sentinel": {
        "server": "redis://mymaster/0",
        "options": {
            "SENTINELS": [("h1", 26379), ("h2", 26379)],
            "SENTINEL_KWARGS": {},
            "CONNECTION_FACTORY_CLASS": "throttled.store.SentinelConnectionFactory",
        },
    },
    "sentinel_with_auth": {
        "server": "redis://mymaster/0",
        "options": {
            "SENTINELS": [("localhost", 26379)],
            "USERNAME": "user",
            "PASSWORD": "pass",
            "SENTINEL_KWARGS": {"username": "user", "password": "pass"},
            "CONNECTION_FACTORY_CLASS": "throttled.store.SentinelConnectionFactory",
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
