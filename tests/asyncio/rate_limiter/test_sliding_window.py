from datetime import timedelta
from typing import Callable, List

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
def rate_limiter_constructor(store: BaseStore) -> Callable[[Quota], BaseRateLimiter]:
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

        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        store_key: str = (
            f"throttled:v1:sliding_window:key" f":period:{utils.now_sec() // period}"
        )
        assert await rate_limiter._store.exists(store_key) is False

        result: RateLimitResult = await rate_limiter.limit(key)
        assert_rate_limit_result(False, 4, quota, result)
        assert await rate_limiter._store.get(store_key) == 1
        assert await rate_limiter._store.ttl(store_key) == 3 * period

        result: RateLimitResult = await rate_limiter.limit(key, cost=4)
        assert_rate_limit_result(False, 0, quota, result)
        assert await rate_limiter._store.get(store_key) == 5

        result: RateLimitResult = await rate_limiter.limit(key, cost=4)
        assert_rate_limit_result(True, 0, quota, result)
        assert await rate_limiter._store.get(store_key) == 9

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
            assert abs(accessed_num - limit) <= (elapsed + 2) * rate

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
