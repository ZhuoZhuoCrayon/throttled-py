from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, cast

import pytest
from redis import Redis
from throttled import BaseStore, MemoryStore, RedisStore
from throttled.constants import StoreType
from throttled.rate_limiter.gcra import (
    RedisLimitAtomicActionSpec,
    RedisPeekAtomicActionSpec,
)
from throttled.utils import Benchmark

if TYPE_CHECKING:
    from pytest_redis.executor import RedisExecutor


@pytest.fixture
def redis_url(redis_proc: "RedisExecutor") -> Iterator[str]:
    """Use the Redis process that pytest-redis owns for this worker."""
    url: str = f"redis://{redis_proc.host}:{redis_proc.port}/0"
    with Redis.from_url(url) as client:
        yield url
        client.flushdb()


@pytest.fixture
def redis_store(redis_url: str) -> RedisStore:
    return RedisStore(server=redis_url)


@pytest.fixture(params=[StoreType.MEMORY.value, StoreType.REDIS.value])
def store(request: pytest.FixtureRequest) -> BaseStore:
    if request.param == StoreType.MEMORY.value:
        return MemoryStore()
    return cast("RedisStore", request.getfixturevalue("redis_store"))


@pytest.fixture(scope="class")
def benchmark() -> Benchmark:
    return Benchmark()


@pytest.fixture
def gcra_clock_key(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], str]:
    """Encode the server clock in each test key for the GCRA precision sweep."""
    epoch: int = 1735660800
    for spec in (RedisLimitAtomicActionSpec, RedisPeekAtomicActionSpec):
        assert f"local jan_1_2025 = {epoch}" in spec.SCRIPTS
        clock_call: str = 'redis.call("TIME")'
        assert clock_call in spec.SCRIPTS
        script: str = spec.SCRIPTS.replace(
            clock_call, '{string.match(KEYS[1], "(%d+):(%d+)$")}'
        )
        monkeypatch.setattr(spec, "SCRIPTS", script)

    def key(index: int) -> str:
        seconds, micros = divmod(30_000_000 + index * 17_300, 1_000_000)
        return f"clock:{epoch + seconds}:{micros}"

    return key
