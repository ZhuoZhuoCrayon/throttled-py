import pytest_asyncio
from fakeredis.aioredis import FakeConnection

from throttled.asyncio import BaseStore, MemoryStore, RedisStore, constants


@pytest_asyncio.fixture(
    params=[constants.StoreType.MEMORY.value, constants.StoreType.REDIS.value]
)
async def store(request) -> BaseStore:
    def _create_store(store_type: str) -> BaseStore:
        if store_type == constants.StoreType.MEMORY.value:
            return MemoryStore()
        else:
            return RedisStore(
                options={
                    "REDIS_CLIENT_CLASS": "fakeredis.aioredis.FakeRedis",
                    "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
                }
            )

    store: BaseStore = _create_store(request.param)

    yield store

    if request.param == constants.StoreType.REDIS.value:
        await store._backend.get_client().flushall()
