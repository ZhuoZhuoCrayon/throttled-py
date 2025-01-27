import fakeredis
import pytest
from redis import Redis

from throttled.constants import StoreType
from throttled.store.base import BaseStore
from throttled.store.memory import MemoryStore
from throttled.store.redis import RedisStore


@pytest.fixture
def redis_client() -> Redis:
    redis_client = fakeredis.FakeRedis()
    return redis_client


@pytest.fixture(params=[StoreType.MEMORY.value, StoreType.REDIS.value])
def store(request, redis_client: Redis) -> BaseStore:
    def _create_store(store_type: str) -> BaseStore:
        if store_type == StoreType.MEMORY.value:
            return MemoryStore()
        else:
            return RedisStore(redis_client)

    return _create_store(request.param)
