import time
from typing import Callable

import pytest

from throttled import (
    BaseRateLimiter,
    BaseStore,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    per_min,
)
from throttled.constants import RateLimiterType
from throttled.types import TimeLikeValueT
from throttled.utils import Benchmark, Timer

from . import parametrizes


@pytest.fixture
def rate_limiter_constructor(store: BaseStore) -> Callable[[Quota], BaseRateLimiter]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(RateLimiterType.TOKEN_BUCKET.value)(quota, store)

    yield _create_rate_limiter


def assert_rate_limit_result(
    limited: bool, remaining: int, quota: Quota, result: RateLimitResult
):
    assert result.limited == limited
    assert result.state.limit == quota.burst
    assert result.state.remaining == remaining
    assert result.state.reset_after == quota.burst - remaining
    if result.limited:
        assert result.state.retry_after == 1
    else:
        assert result.state.retry_after == 0


class TestTokenBucketRateLimiter:
    def test_limit(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        key: str = "key"
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        time.sleep(1)
        result: RateLimitResult = rate_limiter.limit(key)
        assert_rate_limit_result(False, 9, quota, result)

        time.sleep(1)
        result: RateLimitResult = rate_limiter.limit(key, cost=5)
        assert_rate_limit_result(False, 5, quota, result)

        result: RateLimitResult = rate_limiter.limit(key, cost=5)
        assert_rate_limit_result(False, 0, quota, result)

        result: RateLimitResult = rate_limiter.limit(key)
        assert_rate_limit_result(True, 0, quota, result)

    @parametrizes.LIMIT_C_QUOTA
    @parametrizes.LIMIT_C_REQUESTS_NUM
    def test_limit__concurrent(
        self,
        benchmark: Benchmark,
        rate_limiter_constructor: Callable[[Quota], BaseRateLimiter],
        quota: Quota,
        requests_num: int,
    ):
        def _callback(elapsed: TimeLikeValueT, *args, **kwargs):
            accessed_num: int = requests_num - sum(results)
            limit: int = min(requests_num, quota.get_limit())

            assert accessed_num >= limit
            assert accessed_num <= limit + (elapsed + 6) * quota.fill_rate

        with Timer(callback=_callback):
            rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
            results = benchmark.concurrent(
                task=lambda: rate_limiter.limit("key").limited, batch=requests_num
            )

    def test_peek(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        key: str = "key"
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        state: RateLimitState = rate_limiter.peek(key)
        assert state == RateLimitState(limit=10, remaining=10, reset_after=0)

        rate_limiter.limit(key, cost=5)
        state: RateLimitState = rate_limiter.peek(key)
        assert state == RateLimitState(limit=10, remaining=5, reset_after=5)

        time.sleep(1)
        state: RateLimitState = rate_limiter.peek(key)
        assert state == RateLimitState(limit=10, remaining=6, reset_after=4)
