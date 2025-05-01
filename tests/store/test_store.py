from datetime import timedelta
from typing import Any, Dict, Optional, Type

import pytest

from throttled import BaseStore
from throttled.constants import STORE_TTL_STATE_NOT_EXIST, STORE_TTL_STATE_NOT_TTL
from throttled.exceptions import BaseThrottledError, DataError
from throttled.types import KeyT, StoreValueT


class TestStore:
    @pytest.mark.parametrize("set_before", [True, False], ids=["set", "not set"])
    @pytest.mark.parametrize("key, value", [("one", 1)], ids=["one"])
    def test_exists(
        self, store: BaseStore, set_before: bool, key: KeyT, value: [StoreValueT]
    ):
        if set_before:
            store.set(key, value, 1)

        assert store.exists(key) is set_before
        assert store.get(key) == (None, value)[set_before]

    @pytest.mark.parametrize("key", ["key"])
    @pytest.mark.parametrize(
        "timeout",
        [
            int(timedelta(seconds=1).total_seconds()),
            int(timedelta(minutes=1).total_seconds()),
            int(timedelta(hours=1).total_seconds()),
            int(timedelta(days=1).total_seconds()),
            int(timedelta(weeks=1).total_seconds()),
            int(timedelta(days=30).total_seconds()),
            int(timedelta(days=365).total_seconds()),
        ],
    )
    def test_ttl(self, store: BaseStore, key: KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    def test_ttl__not_exist(self, store: BaseStore):
        assert store.ttl("key") == STORE_TTL_STATE_NOT_EXIST

    def test_ttl__not_ttl(self, store: BaseStore):
        store.hset("name", "key", 1)
        assert store.ttl("name") == STORE_TTL_STATE_NOT_TTL

    @pytest.mark.parametrize("key,timeout", [("one", 1)])
    def test_set(self, store: BaseStore, key: KeyT, timeout: int):
        store.set(key, 1, timeout)
        assert timeout == store.ttl(key)

    @pytest.mark.parametrize(
        "key,timeout,exc,match",
        [
            ["key", 0, DataError, "Invalid timeout"],
            ["key", -1, DataError, "Invalid timeout"],
            ["key", 0.1, DataError, "Invalid timeout"],
            ["key", "aaaa", DataError, "Invalid timeout"],
            ["key", timedelta(minutes=1), DataError, "Invalid timeout"],
        ],
        ids=["zero", "negative", "float", "string", "object"],
    )
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

    @pytest.mark.parametrize("set_before", [True, False], ids=["set", "not set"])
    @pytest.mark.parametrize(
        "key, value",
        [
            ("one", 1),
            ("two", 1e100),
            ("three", 1e-10),
            ("/product/?a=1#/////", 1),
            ("🐶", 0.1),
            ("?book=《活着》", 1),
            ("long text" * 1000, 1),
            ("127.0.0.1", 1),
            ("0000:0000:0000:0000:0000:FFFF:0CFF:0001", 1),
        ],
        ids=[
            "value(integer)",
            "value(big integer)",
            "value(float)",
            "key(url)",
            "key(emoji)",
            "key(zh)",
            "key(long text)",
            "key(IPv4)",
            "key(IPv6)",
        ],
    )
    def test_get(
        self, store: BaseStore, set_before: bool, key: KeyT, value: StoreValueT
    ):
        if set_before:
            store.set(key, value, 1)
        assert store.get(key) == (None, value)[set_before]

    @pytest.mark.parametrize(
        "name,expect,key,value,mapping",
        [
            ["one", {"k1": 1}, "k1", 1, None],
            ["one", {"中文": 1}, "中文", 1, None],
            ["one", {"🐶": 1}, "🐶", 1, None],
            ["one", {"🐶": 1}, "🐶", 1, {}],
            ["one", {"🐶": 1, "k1": 1, "k2": 2}, "🐶", 1, {"k1": 1, "k2": 2}],
        ],
    )
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

    def test_hset__raise(self, store: BaseStore):
        with pytest.raises(DataError, match="hset must with key value pairs"):
            store.hset("key")

        with pytest.raises(DataError, match="hset must with key value pairs"):
            store.hset("key", mapping={})

    def test_hset__overwrite(self, store: BaseStore):
        key: str = "key"
        store.hset(key, "k1", 1)
        assert store.hgetall(key) == {"k1": 1}

        store.hset(key, "k1", 2)
        assert store.hgetall(key) == {"k1": 2}

        store.hset(key, mapping={"k1": 3})
        assert store.hgetall(key) == {"k1": 3}

        store.hset(key, mapping={"k1": 1, "k2": 2})
        assert store.hgetall(key) == {"k1": 1, "k2": 2}

        store.hset(key, "k3", 3)
        assert store.hgetall(key) == {"k1": 1, "k2": 2, "k3": 3}

    def test_hgetall(self, store: BaseStore):
        assert store.hgetall("name") == {}
        store.hset("name", "k1", 1)
        assert store.hgetall("name") == {"k1": 1}
        store.hset("name", "k2", 2)
        assert store.hgetall("name") == {"k1": 1, "k2": 2}
