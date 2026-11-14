from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, cast

import pytest
import pytest_asyncio
from throttled.asyncio import BaseStore, MemoryStore, RedisStore, constants

if TYPE_CHECKING:
    from redis.asyncio import Redis


@pytest_asyncio.fixture
async def redis_store(redis_url: str) -> AsyncIterator[RedisStore]:
    store: RedisStore = RedisStore(server=redis_url)
    yield store
    client = cast("Redis", store._backend.get_client())
    await client.aclose(close_connection_pool=True)


@pytest.fixture(
    params=[constants.StoreType.MEMORY.value, constants.StoreType.REDIS.value]
)
def store(request: pytest.FixtureRequest) -> BaseStore:
    if request.param == constants.StoreType.MEMORY.value:
        return MemoryStore()
    return cast("RedisStore", request.getfixturevalue("redis_store"))
