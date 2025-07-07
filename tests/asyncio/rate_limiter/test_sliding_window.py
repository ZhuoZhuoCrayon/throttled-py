import math
from datetime import timedelta
from typing import Any, Callable, Generator, List

import pytest

from throttled.asyncio import (
    BaseRateLimiter,
    BaseStore,
    Quota,
    Rate,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    constants,
    per_min,
    types,
    utils,
)

from ...rate_limiter import parametrizes
from ...rate_limiter.test_sliding_window import assert_rate_limit_result


@pytest.fixture
def rate_limiter_constructor(
    store: BaseStore,
) -> Generator[Callable[[Quota], BaseRateLimiter], Any, None]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(constants.RateLimiterType.SLIDING_WINDOW.value)(
            quota, store
        )

    yield _create_rate_limiter


@pytest.mark.asyncio
class TestSlidingWindowRateLimiter:
    async def test_limit(
        self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]
    ):
        limit: int = 5
        period: int = 60
        quota: Quota = Quota(Rate(period=timedelta(minutes=1), limit=limit))

        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
        store_key: str = (
            f"throttled:v1:sliding_window:key:period:{utils.now_sec() // period}"
        )
        assert await rate_limiter._store.exists(store_key) is False

        for case in parametrizes.SLIDING_WINDOW_LIMIT_CASES:
            result: RateLimitResult = await rate_limiter.limit("key", cost=case["cost"])
            assert_rate_limit_result(case["limited"], case["remaining"], quota, result)
            assert await rate_limiter._store.get(store_key) == case["count"]
            if "ttl" in case:
                assert await rate_limiter._store.ttl(store_key) == case["ttl"]

    @parametrizes.LIMIT_C_QUOTA
    @parametrizes.LIMIT_C_REQUESTS_NUM
    async def test_limit__concurrent(
        self,
        benchmark: utils.Benchmark,
        rate_limiter_constructor: Callable[[Quota], BaseRateLimiter],
        quota: Quota,
        requests_num: int,
    ):
        def _callback(elapsed: types.TimeLikeValueT, *args, **kwargs):
            accessed_num: int = requests_num - sum(results)
            limit: int = min(requests_num, quota.get_limit())
            assert abs(accessed_num - limit) <= math.ceil(
                (elapsed + 2) * quota.fill_rate
            )

        async def _task():
            result = await rate_limiter.limit("key")
            return result.limited

        with utils.Timer(callback=_callback):
            rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
            results: List[bool] = await benchmark.async_concurrent(
                task=_task, batch=requests_num
            )

    async def test_peek(
        self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]
    ):
        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(per_min(1))
        assert await rate_limiter.peek(key) == RateLimitState(
            limit=1, remaining=1, reset_after=60
        )
        await rate_limiter.limit(key)
        assert await rate_limiter.peek(key) == RateLimitState(
            limit=1, remaining=0, reset_after=60
        )
