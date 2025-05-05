from datetime import timedelta
from typing import Type

import pytest

STORE_EXISTS_SET_BEFORE = pytest.mark.parametrize(
    "set_before", [True, False], ids=["set", "not set"]
)

STORE_EXISTS_KV = pytest.mark.parametrize("key, value", [("one", 1)], ids=["one"])

STORE_TTL_KEY = pytest.mark.parametrize("key", ["key"])

STORE_TTL_TIMEOUT = pytest.mark.parametrize(
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

STORE_SET_KEY_TIMEOUT = pytest.mark.parametrize("key,timeout", [("one", 1)])


def store_set_raise_parametrize(data_error: Type[BaseException]):
    return pytest.mark.parametrize(
        "key,timeout,exc,match",
        [
            ["key", 0, data_error, "Invalid timeout"],
            ["key", -1, data_error, "Invalid timeout"],
            ["key", 0.1, data_error, "Invalid timeout"],
            ["key", "aaaa", data_error, "Invalid timeout"],
            ["key", timedelta(minutes=1), data_error, "Invalid timeout"],
        ],
        ids=["zero", "negative", "float", "string", "object"],
    )


STORE_GET_SET_BEFORE = pytest.mark.parametrize(
    "set_before", [True, False], ids=["set", "not set"]
)


STORE_GET_KV = pytest.mark.parametrize(
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

STORE_HSET_PARAMETRIZE = pytest.mark.parametrize(
    "name,expect,key,value,mapping",
    [
        ["one", {"k1": 1}, "k1", 1, None],
        ["one", {"中文": 1}, "中文", 1, None],
        ["one", {"🐶": 1}, "🐶", 1, None],
        ["one", {"🐶": 1}, "🐶", 1, {}],
        ["one", {"🐶": 1, "k1": 1, "k2": 2}, "🐶", 1, {"k1": 1, "k2": 2}],
    ],
)

STORE_HSET_OVERWRITE_PARAMETRIZE = pytest.mark.parametrize(
    ("params_list", "expected_results"),
    [
        [
            [
                {"key": "k1", "value": 1},
                {"key": "k1", "value": 2},
                {"mapping": {"k1": 3}},
                {"mapping": {"k1": 1, "k2": 2}},
                {"key": "k3", "value": 3},
            ],
            [
                {"k1": 1},
                {"k1": 2},
                {"k1": 3},
                {"k1": 1, "k2": 2},
                {"k1": 1, "k2": 2, "k3": 3},
            ],
        ]
    ],
)


STORE_HGETALL_PARAMETRIZE = pytest.mark.parametrize(
    "params_list, expected_results",
    [
        [
            [
                {"key": "k0", "value": 0},
                {"key": "k1", "value": 1},
                {"key": "k2", "value": 2},
            ],
            [{"k0": 0}, {"k0": 0, "k1": 1}, {"k0": 0, "k1": 1, "k2": 2}],
        ]
    ],
)


def store_hset_raise_parametrize(data_error: Type[BaseException]):
    return pytest.mark.parametrize(
        "params, exc, match",
        [
            [{"name": "key"}, data_error, "hset must with key value pairs"],
            [
                {"name": "key", "mapping": {}},
                data_error,
                "hset must with key value pairs",
            ],
        ],
    )
