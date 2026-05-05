from typing import Any

import pytest
from throttled import BaseStore, RedisStore, constants, types
from throttled.exceptions import BaseThrottledError, DataError, StoreUnavailableError

from . import parametrizes


def _replace_store_backend(store: BaseStore[Any], backend: Any) -> Any:
    original_backend = store._backend
    store._backend = backend
    return original_backend


class TestStore:
    @classmethod
    @parametrizes.STORE_EXISTS_SET_BEFORE
    @parametrizes.STORE_EXISTS_KV
    def test_exists(
        cls,
        store: BaseStore[Any],
        set_before: bool,
        key: types.KeyT,
        value: types.StoreValueT,
    ):
        if set_before:
            store.set(key, value, 1)

        assert store.exists(key) is set_before
        assert store.get(key) == (None, value)[set_before]

    @classmethod
    @parametrizes.STORE_TTL_KEY
    @parametrizes.STORE_TTL_TIMEOUT
    def test_ttl(cls, store: BaseStore[Any], key: types.KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    @classmethod
    def test_ttl__not_exist(cls, store: BaseStore[Any]):
        assert store.ttl("key") == constants.STORE_TTL_STATE_NOT_EXIST

    @classmethod
    def test_ttl__not_ttl(cls, store: BaseStore[Any]):
        store.hset("name", "key", 1)
        assert store.ttl("name") == constants.STORE_TTL_STATE_NOT_TTL

    @classmethod
    @parametrizes.STORE_SET_KEY_TIMEOUT
    def test_set(cls, store: BaseStore[Any], key: types.KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    @classmethod
    @parametrizes.store_set_raise_parametrize(DataError)
    def test_set__raise(
        cls,
        store: BaseStore[Any],
        key: types.KeyT,
        timeout: Any,
        exc: type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            store.set(key, 1, timeout)

    @classmethod
    @parametrizes.STORE_GET_SET_BEFORE
    @parametrizes.STORE_GET_KV
    def test_get(
        cls,
        store: BaseStore[Any],
        set_before: bool,
        key: types.KeyT,
        value: types.StoreValueT,
    ):
        if set_before:
            store.set(key, value, 1)
        assert store.get(key) == (None, value)[set_before]

    @classmethod
    @parametrizes.STORE_HSET_PARAMETRIZE
    def test_hset(
        cls,
        store: BaseStore[Any],
        name: types.KeyT,
        expect: dict[types.KeyT, types.StoreValueT],
        key: types.KeyT | None,
        value: types.StoreValueT | None,
        mapping: dict[types.KeyT, types.StoreValueT] | None,
    ):
        assert store.exists(name) is False
        assert store.ttl(name) == constants.STORE_TTL_STATE_NOT_EXIST
        store.hset(name, key, value, mapping)
        assert store.exists(name) is True
        assert store.ttl(name) == constants.STORE_TTL_STATE_NOT_TTL
        store.expire(name, 1)
        assert store.ttl(name) == 1
        assert store.hgetall(name) == expect

    @classmethod
    @parametrizes.store_hset_raise_parametrize(DataError)
    def test_hset__raise(
        cls,
        store: BaseStore[Any],
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
        store: BaseStore[Any],
        params_list: list[dict[str, Any]],
        expected_results: list[dict[types.KeyT, types.StoreValueT]],
    ):
        key: str = "key"
        for i, params in enumerate(params_list):
            store.hset(key, **params)
            assert store.hgetall(key) == expected_results[i]

    @classmethod
    @parametrizes.STORE_UNAVAILABLE_METHOD_PARAMETRIZE
    def test_store_unavailable__wrap_backend_error(
        cls, store: BaseStore[Any], method_name: str, params: dict[str, Any]
    ) -> None:
        base_exceptions: tuple[type[BaseException], ...] = store._backend.base_exceptions
        if not base_exceptions:
            pytest.skip(
                f"{store._backend.__class__.__name__} "
                f"does not define unavailable exceptions"
            )

        original_backend = _replace_store_backend(
            store, parametrizes.BrokenStoreBackend(base_exceptions)
        )
        try:
            with pytest.raises(StoreUnavailableError) as exc_info:
                getattr(store, method_name)(**params)
        finally:
            store._backend = original_backend

        assert isinstance(exc_info.value.__cause__, base_exceptions)


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
    "cluster": {
        "server": "redis+cluster://c1:7000,c2:7000,c3:7000",
        "options": {
            "CLUSTER_NODES": [("c1", 7000), ("c2", 7000), ("c3", 7000)],
            "CONNECTION_FACTORY_CLASS": "throttled.store.ClusterConnectionFactory",
        },
    },
    "cluster_with_auth": {
        "server": "redis+cluster://user:pass@c1:7000",
        "options": {
            "CLUSTER_NODES": [("c1", 7000)],
            "USERNAME": "user",
            "PASSWORD": "pass",
            "CONNECTION_FACTORY_CLASS": "throttled.store.ClusterConnectionFactory",
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
