from datetime import timedelta
from typing import Any, Callable, Generator, List

import pytest

from tests.rate_limiter import parametrizes
from tests.rate_limiter.test_fixed_window import assert_rate_limit_result
from throttled.asyncio import (
    BaseRateLimiter,
    BaseStore,
    Quota,
    Rate,
    RateLimiterRegistry,
    RateLimiterType,
    RateLimitResult,
    RateLimitState,
    per_min,
)
from throttled.utils import Benchmark, now_sec


@pytest.fixture
def rate_limiter_constructor(
    store: BaseStore,
) -> Generator[Callable[[Quota], BaseRateLimiter], Any, None]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(RateLimiterType.FIXED_WINDOW.value)(quota, store)

    yield _create_rate_limiter


@pytest.mark.asyncio
class TestFixedWindowRateLimiter:
    async def test_limit(
        self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]
    ):
        limit: int = 5
        period: int = 60
        quota: Quota = Quota(Rate(period=timedelta(minutes=1), limit=limit))

        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        store_key: str = f"throttled:v1:fixed_window:key:period:{now_sec() // period}"
        assert await rate_limiter._store.exists(store_key) is False

        for case in parametrizes.FIXED_WINDOW_LIMIT_CASES:
            result: RateLimitResult = await rate_limiter.limit(key, cost=case["cost"])
            assert_rate_limit_result(case["limited"], case["remaining"], quota, result)
            assert await rate_limiter._store.get(store_key) == case["count"]

    @pytest.mark.parametrize(
        "quota", [per_min(1), per_min(10), per_min(100), per_min(1_000)]
    )
    @pytest.mark.parametrize("requests_num", [10, 100, 1_000, 10_000])
    async def test_limit__concurrent(
        self,
        benchmark: Benchmark,
        rate_limiter_constructor: Callable[[Quota], BaseRateLimiter],
        quota: Quota,
        requests_num: int,
    ):
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        async def _task():
            result = await rate_limiter.limit("key")
            return result.limited

        results: List[bool] = await benchmark.async_concurrent(
            task=_task, batch=requests_num
        )

        accessed_num: int = requests_num - sum(results)
        limit: int = min(requests_num, quota.get_limit())
        # Period boundaries may burst with 2 times the number of requests.
        assert limit <= accessed_num <= 2 * limit

    async def test_peek(
        self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]
    ):
        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(per_min(1))

        def _assert(_state: RateLimitState):
            assert _state.limit == 1
            assert _state.reset_after - (60 - (now_sec() % 60)) <= 1

        state: RateLimitState = await rate_limiter.peek(key)
        _assert(state)
        assert state.remaining == 1

        await rate_limiter.limit(key)

        state: RateLimitState = await rate_limiter.peek(key)
        assert state.remaining == 0
        _assert(state)
