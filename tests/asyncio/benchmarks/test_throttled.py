import asyncio

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from throttled.asyncio import (
    BaseStore,
    MemoryStore,
    Quota,
    RateLimiterType,
    RedisStore,
    Throttled,
    constants,
    per_sec,
    types,
    utils,
)

REDIS_URL: str = "redis://127.0.0.1:6379/0"

WORKERS: int = 8


async def clear_redis(client: Redis) -> None:
    keys: list[str] = await client.keys("throttled*")
    await client.delete(*keys)


async def redis_baseline(client: Redis):
    await client.incrby("throttled:v2", 1)


async def memory_baseline(dict_store: dict[str, int]):
    dict_store["throttled:v2"] = dict_store.get("throttled:v2", 0) + 1


async def memory_with_lock_baseline(lock: asyncio.Lock, dict_store: dict[str, int]):
    async with lock:
        await memory_baseline(dict_store)


async def call_api(throttle: Throttled) -> bool:
    return (await throttle.limit("/ping", cost=1)).limited


@pytest_asyncio.fixture(params=constants.StoreType.choice())
def store(request) -> BaseStore:
    def _create_store(store_type: str) -> BaseStore:
        if store_type == constants.StoreType.MEMORY.value:
            return MemoryStore()
        return RedisStore(server=REDIS_URL)

    store: BaseStore = _create_store(request.param)

    yield store

    if request.param == constants.StoreType.REDIS.value:
        clear_redis(store._backend.get_client())


@pytest_asyncio.fixture
async def redis_client() -> Redis:
    client: Redis = Redis.from_url(REDIS_URL)

    yield client

    await clear_redis(client)


@pytest.mark.skip(reason="skip benchmarks")
@pytest.mark.asyncio
class TestBenchmarkThrottled:
    @classmethod
    async def test_memory_baseline__serial(cls, benchmark: utils.Benchmark):
        await benchmark.async_serial(memory_baseline, batch=500_000, dict_store={})

    @classmethod
    async def test_memory_baseline__concurrent(cls, benchmark: utils.Benchmark):
        await benchmark.async_concurrent(
            memory_with_lock_baseline,
            batch=100_000,
            workers=WORKERS,
            lock=asyncio.Lock(),
            dict_store={},
        )

    @classmethod
    async def test_redis_baseline__serial(
        cls, benchmark: utils.Benchmark, redis_client: Redis
    ):
        await benchmark.async_serial(redis_baseline, batch=100_000, client=redis_client)

    @classmethod
    async def test_redis_baseline__concurrent(
        cls, benchmark: utils.Benchmark, redis_client: Redis
    ):
        await benchmark.async_concurrent(
            redis_baseline, batch=100_000, workers=WORKERS, client=redis_client
        )

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    @pytest.mark.parametrize("quota", [per_sec(1_000)])
    async def test_limit__serial(
        cls,
        benchmark: utils.Benchmark,
        store: BaseStore,
        using: types.RateLimiterTypeT,
        quota: Quota,
    ):
        throttle = Throttled(using=using, quota=quota, store=store)
        await benchmark.async_serial(call_api, batch=100_000, throttle=throttle)

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    @pytest.mark.parametrize("quota", [per_sec(1_000)])
    async def test_limit__concurrent(
        cls,
        benchmark: utils.Benchmark,
        store: BaseStore,
        using: types.RateLimiterTypeT,
        quota: Quota,
    ):
        throttle = Throttled(using=using, quota=quota, store=store)
        await benchmark.async_concurrent(
            call_api, batch=100_000, workers=WORKERS, throttle=throttle
        )
