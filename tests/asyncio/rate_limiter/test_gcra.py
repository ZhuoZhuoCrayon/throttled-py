import asyncio
from typing import Callable, List

import pytest

from throttled.asyncio import (
    BaseRateLimiter,
    BaseStore,
    Quota,
    RateLimiterRegistry,
    RateLimiterType,
    RateLimitResult,
    RateLimitState,
    per_min,
    types,
    utils,
)

from ...rate_limiter import parametrizes
from ...rate_limiter.test_gcra import assert_rate_limit_result


@pytest.fixture
def rate_limiter_constructor(store: BaseStore) -> Callable[[Quota], BaseRateLimiter]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(RateLimiterType.GCRA.value)(quota, store)

    return _create_rate_limiter


@pytest.mark.asyncio
class TestGCRARateLimiter:
    async def test_limit(
        self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]
    ):
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
        for case in parametrizes.GCRA_LIMIT_CASES:
            if "sleep" in case:
                await asyncio.sleep(case["sleep"])

            result: RateLimitResult = await rate_limiter.limit("key", cost=case["cost"])
            assert_rate_limit_result(case["limited"], case["remaining"], quota, result)

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
            rate: float = quota.get_limit() / quota.get_period_sec()
            assert limit <= accessed_num <= limit + (elapsed + 2) * rate

        async def _task():
            result = await rate_limiter.limit("key")
            return result.limited

        async with utils.Timer(callback=_callback):
            rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
            results: List[bool] = await benchmark.async_concurrent(
                task=_task, batch=requests_num
            )

    async def test_peek(
        self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]
    ):
        key: str = "key"
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        state: RateLimitState = await rate_limiter.peek(key)
        assert state == RateLimitState(limit=10, remaining=10, reset_after=0)

        await rate_limiter.limit(key, cost=5)
        state: RateLimitState = await rate_limiter.peek(key)
        assert state.limit == 10 and state.remaining == 5
        assert 5 - state.reset_after < 0.1

        await asyncio.sleep(1)
        state: RateLimitState = await rate_limiter.peek(key)
        assert state.limit == 10 and state.remaining == 6
        assert 4 - state.reset_after < 0.1

        await rate_limiter.limit(key, cost=6)
        state: RateLimitState = await rate_limiter.peek(key)
        assert state.remaining == 0
        assert 10 - state.reset_after < 0.1
