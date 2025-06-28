from typing import Any, Generator

import pytest
from fakeredis import FakeConnection

from throttled import BaseStore, MemoryStore, RedisStore
from throttled.constants import StoreType
from throttled.utils import Benchmark


@pytest.fixture(params=[StoreType.MEMORY.value, StoreType.REDIS.value])
def store(request) -> Generator[BaseStore, Any, None]:
    def _create_store(store_type: str) -> BaseStore:
        if store_type == StoreType.MEMORY.value:
            return MemoryStore()
        else:
            return RedisStore(
                options={
                    "REDIS_CLIENT_CLASS": "fakeredis.FakeRedis",
                    "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
                }
            )

    store: BaseStore = _create_store(request.param)

    yield store

    if request.param == StoreType.REDIS.value:
        store._backend.get_client().flushall()


@pytest.fixture(scope="class")
def benchmark() -> Benchmark:
    return Benchmark()
