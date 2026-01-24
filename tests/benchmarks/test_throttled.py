import threading
from collections.abc import Generator
from typing import Any

import pytest
import redis
from redis import Redis
from throttled import (
    BaseStore,
    MemoryStore,
    Quota,
    RateLimiterType,
    RedisStore,
    Throttled,
    per_sec,
)
from throttled.constants import StoreType
from throttled.types import RateLimiterTypeT
from throttled.utils import Benchmark

REDIS_URL: str = "redis://127.0.0.1:6379/0"

WORKERS: int = 8


def clear_redis(client: redis.Redis) -> None:
    keys: list[str] = client.keys("throttled*")
    client.delete(*keys)


def redis_baseline(client: redis.Redis):
    client.incrby("throttled:v2", 1)


def memory_baseline(dict_store: dict[str, int]):
    dict_store["throttled:v2"] = dict_store.get("throttled:v2", 0) + 1


def memory_with_lock_baseline(lock: threading.RLock, dict_store: dict[str, int]):
    with lock:
        memory_baseline(dict_store)


def call_api(throttle: Throttled) -> bool:
    result = throttle.limit("/ping", cost=1)
    return result.limited


@pytest.fixture(params=StoreType.choice())
def store(request) -> Generator[BaseStore, Any, None]:
    def _create_store(store_type: str) -> BaseStore:
        if store_type == StoreType.MEMORY.value:
            return MemoryStore()
        return RedisStore(server=REDIS_URL)

    store: BaseStore = _create_store(request.param)

    yield store

    if request.param == StoreType.REDIS.value:
        clear_redis(store._backend.get_client())


@pytest.fixture
def redis_client() -> Generator[Redis, Any, None]:
    client: redis.Redis = redis.Redis.from_url(REDIS_URL)

    yield client

    clear_redis(client)


@pytest.mark.skip(reason="skip benchmarks")
class TestBenchmarkThrottled:
    @classmethod
    def test_memory_baseline__serial(cls, benchmark: Benchmark):
        benchmark.serial(memory_baseline, batch=500_000, dict_store={})

    @classmethod
    def test_memory_baseline__concurrent(cls, benchmark: Benchmark):
        benchmark.concurrent(
            memory_with_lock_baseline,
            batch=100_000,
            workers=WORKERS,
            lock=threading.RLock(),
            dict_store={},
        )

    @classmethod
    def test_redis_baseline__serial(
        cls, benchmark: Benchmark, redis_client: redis.Redis
    ):
        benchmark.serial(redis_baseline, batch=100_000, client=redis_client)

    @classmethod
    def test_redis_baseline__concurrent(
        cls, benchmark: Benchmark, redis_client: redis.Redis
    ):
        benchmark.concurrent(
            redis_baseline, batch=100_000, workers=WORKERS, client=redis_client
        )

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    @pytest.mark.parametrize("quota", [per_sec(1_000)])
    def test_limit__serial(
        cls,
        benchmark: Benchmark,
        store: BaseStore,
        using: RateLimiterTypeT,
        quota: Quota,
    ):
        throttle = Throttled(using=using, quota=quota, store=store)
        benchmark.serial(call_api, batch=100_000, throttle=throttle)

    @classmethod
    @pytest.mark.parametrize("using", RateLimiterType.choice())
    @pytest.mark.parametrize("quota", [per_sec(1_000)])
    def test_limit__concurrent(
        cls,
        benchmark: Benchmark,
        store: BaseStore,
        using: RateLimiterTypeT,
        quota: Quota,
    ):
        throttle = Throttled(using=using, quota=quota, store=store)
        benchmark.concurrent(call_api, batch=100_000, workers=WORKERS, throttle=throttle)
