from collections.abc import Generator
from typing import Any

import pytest
from fakeredis import FakeConnection
from throttled import BaseStore, MemoryStore, RedisStore
from throttled.constants import StoreType
from throttled.utils import Benchmark


def _create_store(store_type: str) -> BaseStore:
    """Create a store based on the given store type."""
    if store_type == StoreType.MEMORY.value:
        return MemoryStore()
    return RedisStore(
        options={
            "REDIS_CLIENT_CLASS": "fakeredis.FakeRedis",
            "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
        }
    )


def _clear_store(store: BaseStore) -> None:
    """Clear the contents of the given store."""
    if StoreType.REDIS.value == store.TYPE:
        store._backend.get_client().flushall()


def _store(store_type: str) -> Generator[RedisStore, Any, None]:
    """Fixture for creating a store of the specified type."""
    store: BaseStore = _create_store(store_type)
    yield store
    _clear_store(store)


@pytest.fixture
def redis_store() -> Generator[RedisStore, Any, None]:
    """Fixture for creating a Redis store."""
    yield from _store(StoreType.REDIS.value)


@pytest.fixture(params=[StoreType.MEMORY.value, StoreType.REDIS.value])
def store(request) -> Generator[BaseStore, Any, None]:
    """Fixture for creating different types of stores."""
    yield from _store(request.param)


@pytest.fixture(scope="class")
def benchmark() -> Benchmark:
    return Benchmark()
