from typing import Any, Dict, List, Optional, Type

import pytest

from throttled.asyncio import BaseStore, constants, exceptions, types

from ...store import parametrizes


@pytest.mark.asyncio
class TestStore:
    @parametrizes.STORE_EXISTS_SET_BEFORE
    @parametrizes.STORE_EXISTS_KV
    async def test_exists(
        self,
        store: BaseStore,
        set_before: bool,
        key: types.KeyT,
        value: [types.StoreValueT],
    ):
        if set_before:
            await store.set(key, value, 1)

        assert await store.exists(key) is set_before
        assert await store.get(key) == (None, value)[set_before]

    @parametrizes.STORE_TTL_KEY
    @parametrizes.STORE_TTL_TIMEOUT
    async def test_ttl(self, store: BaseStore, key: types.KeyT, timeout: int):
        await store.set(key, 1, timeout)
        assert timeout == await store.ttl(key)

    async def test_ttl__not_exist(self, store: BaseStore):
        assert await store.ttl("key") == constants.STORE_TTL_STATE_NOT_EXIST

    async def test_ttl__not_ttl(self, store: BaseStore):
        await store.hset("name", "key", 1)
        assert await store.ttl("name") == constants.STORE_TTL_STATE_NOT_TTL

    @parametrizes.STORE_SET_KEY_TIMEOUT
    async def test_set(self, store: BaseStore, key: types.KeyT, timeout: int):
        await store.set(key, 1, timeout)
        assert timeout == await store.ttl(key)

    @parametrizes.store_set_raise_parametrize(exceptions.DataError)
    async def test_set__raise(
        self,
        store: BaseStore,
        key: types.KeyT,
        timeout: Any,
        exc: Type[exceptions.BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            await store.set(key, 1, timeout)

    @parametrizes.STORE_GET_SET_BEFORE
    @parametrizes.STORE_GET_KV
    async def test_get(
        self,
        store: BaseStore,
        set_before: bool,
        key: types.KeyT,
        value: types.StoreValueT,
    ):
        if set_before:
            await store.set(key, value, 1)
        assert await store.get(key) == (None, value)[set_before]

    @parametrizes.STORE_HSET_PARAMETRIZE
    async def test_hset(
        self,
        store: BaseStore,
        name: types.KeyT,
        expect: Dict[types.KeyT, types.StoreValueT],
        key: Optional[types.KeyT],
        value: Optional[types.StoreValueT],
        mapping: Optional[Dict[types.KeyT, types.StoreValueT]],
    ):
        assert await store.exists(name) is False
        assert await store.ttl(name) == constants.STORE_TTL_STATE_NOT_EXIST

        await store.hset(name, key, value, mapping)
        assert await store.exists(name) is True
        assert await store.ttl(name) == constants.STORE_TTL_STATE_NOT_TTL

        await store.expire(name, 1)
        assert await store.ttl(name) == 1
        assert await store.hgetall(name) == expect

    @parametrizes.store_hset_raise_parametrize(exceptions.DataError)
    async def test_hset__raise(
        self,
        store: BaseStore,
        params: Dict[str, Any],
        exc: Type[exceptions.BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            await store.hset(**params)

    @parametrizes.STORE_HSET_OVERWRITE_PARAMETRIZE
    async def test_hset__overwrite(
        self,
        store: BaseStore,
        params_list: List[Dict[str, Any]],
        expected_results: List[Dict[types.KeyT, types.StoreValueT]],
    ):
        key: str = "key"
        for params, expected_result in zip(params_list, expected_results):
            await store.hset(key, **params)
            assert await store.hgetall(key) == expected_result

    @parametrizes.STORE_HGETALL_PARAMETRIZE
    async def test_hgetall(
        self,
        store: BaseStore,
        params_list: List[Dict[str, Any]],
        expected_results: List[Dict[types.KeyT, types.StoreValueT]],
    ):
        for params, expected_result in zip(params_list, expected_results):
            await store.hset("name", **params)
            assert await store.hgetall("name") == expected_result
