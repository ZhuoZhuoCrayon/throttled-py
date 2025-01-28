from datetime import timedelta
from typing import Any, Type

import pytest

from throttled import BaseStore
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

    @pytest.mark.parametrize("key,exc,match", [["key", DataError, "Key not found"]])
    def test_ttl__raise(
        self,
        store: BaseStore,
        key: KeyT,
        exc: Type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            store.ttl(key)

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
