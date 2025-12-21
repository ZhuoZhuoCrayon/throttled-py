from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from fakeredis.aioredis import FakeConnection
from throttled.asyncio import BaseStore, MemoryStore, RedisStore, constants


def _create_store(store_type: str) -> BaseStore:
    """Create a store based on the given store type."""
    if store_type == constants.StoreType.MEMORY.value:
        return MemoryStore()
    return RedisStore(
        options={
            "REDIS_CLIENT_CLASS": "fakeredis.aioredis.FakeRedis",
            "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
        }
    )


async def _clear_store(store: BaseStore) -> None:
    """Clear the contents of the given store."""
    if constants.StoreType.REDIS.value == store.TYPE:
        await store._backend.get_client().flushall()


async def _store(store_type: str) -> AsyncGenerator[BaseStore, Any]:
    """Fixture for creating a store of the specified type."""
    store: BaseStore = _create_store(store_type)
    yield store
    await _clear_store(store)


@pytest_asyncio.fixture()
async def redis_store() -> AsyncGenerator[RedisStore, Any]:
    """Fixture for creating a Redis store."""
    async for store in _store(constants.StoreType.REDIS.value):
        yield store


@pytest_asyncio.fixture(
    params=[constants.StoreType.MEMORY.value, constants.StoreType.REDIS.value]
)
async def store(request) -> AsyncGenerator[BaseStore, Any]:
    """Fixture for creating different types of stores."""
    async for store in _store(request.param):
        yield store
