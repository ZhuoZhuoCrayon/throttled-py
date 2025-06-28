import time
from typing import Callable, List

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
        return RateLimiterRegistry.get(RateLimiterType.GCRA.value)(quota, store)

    return _create_rate_limiter


def assert_rate_limit_result(
    limited: bool, remaining: int, quota: Quota, result: RateLimitResult
):
    assert result.limited == limited
    assert result.state.limit == quota.burst
    assert remaining - result.state.remaining <= 1
    assert quota.burst - remaining - result.state.reset_after < 0.1

    if result.limited:
        assert 1 - result.state.retry_after < 0.1
    else:
        assert result.state.retry_after == 0


class TestGCRARateLimiter:
    def test_limit(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
        for case in parametrizes.GCRA_LIMIT_CASES:
            if "sleep" in case:
                time.sleep(case["sleep"])

            result: RateLimitResult = rate_limiter.limit("key", cost=case["cost"])
            assert_rate_limit_result(case["limited"], case["remaining"], quota, result)

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
            rate: float = quota.get_limit() / quota.get_period_sec()
            assert limit <= accessed_num <= limit + (elapsed + 2) * rate

        with Timer(callback=_callback):
            rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
            results: List[bool] = benchmark.concurrent(
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
        assert state.limit == 10 and state.remaining == 5
        assert 5 - state.reset_after < 0.1

        time.sleep(1)
        state: RateLimitState = rate_limiter.peek(key)
        assert state.limit == 10 and state.remaining == 6
        assert 4 - state.reset_after < 0.1

        rate_limiter.limit(key, cost=6)
        state: RateLimitState = rate_limiter.peek(key)
        assert state.remaining == 0
        assert 10 - state.reset_after < 0.1
