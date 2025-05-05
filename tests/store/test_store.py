from typing import Any, Dict, List, Optional, Type

import pytest

from throttled import BaseStore
from throttled.constants import STORE_TTL_STATE_NOT_EXIST, STORE_TTL_STATE_NOT_TTL
from throttled.exceptions import BaseThrottledError, DataError
from throttled.types import KeyT, StoreValueT

from . import parametrizes


class TestStore:
    @parametrizes.STORE_EXISTS_SET_BEFORE
    @parametrizes.STORE_EXISTS_KV
    def test_exists(
        self, store: BaseStore, set_before: bool, key: KeyT, value: [StoreValueT]
    ):
        if set_before:
            store.set(key, value, 1)

        assert store.exists(key) is set_before
        assert store.get(key) == (None, value)[set_before]

    @parametrizes.STORE_TTL_KEY
    @parametrizes.STORE_TTL_TIMEOUT
    def test_ttl(self, store: BaseStore, key: KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    def test_ttl__not_exist(self, store: BaseStore):
        assert store.ttl("key") == STORE_TTL_STATE_NOT_EXIST

    def test_ttl__not_ttl(self, store: BaseStore):
        store.hset("name", "key", 1)
        assert store.ttl("name") == STORE_TTL_STATE_NOT_TTL

    @parametrizes.STORE_SET_KEY_TIMEOUT
    def test_set(self, store: BaseStore, key: KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    @parametrizes.store_set_raise_parametrize(DataError)
    def test_set__raise(
        self,
        store: BaseStore,
        key: KeyT,
        timeout: Any,
        exc: Type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            store.set(key, 1, timeout)

    @parametrizes.STORE_GET_SET_BEFORE
    @parametrizes.STORE_GET_KV
    def test_get(
        self, store: BaseStore, set_before: bool, key: KeyT, value: StoreValueT
    ):
        if set_before:
            store.set(key, value, 1)
        assert store.get(key) == (None, value)[set_before]

    @parametrizes.STORE_HSET_PARAMETRIZE
    def test_hset(
        self,
        store: BaseStore,
        name: KeyT,
        expect: Dict[KeyT, StoreValueT],
        key: Optional[KeyT],
        value: Optional[StoreValueT],
        mapping: Optional[Dict[KeyT, StoreValueT]],
    ):
        assert store.exists(name) is False
        assert store.ttl(name) == STORE_TTL_STATE_NOT_EXIST
        store.hset(name, key, value, mapping)
        assert store.exists(name) is True
        assert store.ttl(name) == STORE_TTL_STATE_NOT_TTL
        store.expire(name, 1)
        assert store.ttl(name) == 1
        assert store.hgetall(name) == expect

    @parametrizes.store_hset_raise_parametrize(DataError)
    def test_hset__raise(
        self,
        store: BaseStore,
        params: Dict[str, Any],
        exc: Type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            store.hset(**params)

    @parametrizes.STORE_HSET_OVERWRITE_PARAMETRIZE
    def test_hset__overwrite(
        self,
        store: BaseStore,
        params_list: List[Dict[str, Any]],
        expected_results: List[Dict[KeyT, StoreValueT]],
    ):
        key: str = "key"
        for params, expected_result in zip(params_list, expected_results):
            store.hset(key, **params)
            assert store.hgetall(key) == expected_result

    @parametrizes.STORE_HGETALL_PARAMETRIZE
    def test_hgetall(
        self,
        store: BaseStore,
        params_list: List[Dict[str, Any]],
        expected_results: List[Dict[KeyT, StoreValueT]],
    ):
        for params, expected_result in zip(params_list, expected_results):
            store.hset("name", **params)
            assert store.hgetall("name") == expected_result
