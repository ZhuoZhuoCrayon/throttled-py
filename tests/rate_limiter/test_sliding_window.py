from datetime import timedelta
from typing import Any, Callable, Generator, List

import pytest

from throttled import (
    BaseRateLimiter,
    BaseStore,
    Quota,
    Rate,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    per_min,
)
from throttled.constants import RateLimiterType
from throttled.types import TimeLikeValueT
from throttled.utils import Benchmark, Timer, now_sec

from . import parametrizes


@pytest.fixture
def rate_limiter_constructor(
    store: BaseStore,
) -> Generator[Callable[[Quota], BaseRateLimiter], Any, None]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(RateLimiterType.SLIDING_WINDOW.value)(
            quota, store
        )

    yield _create_rate_limiter


def assert_rate_limit_result(
    limited: bool, remaining: int, quota: Quota, result: RateLimitResult
):
    assert result.limited == limited
    assert result.state.limit == quota.get_limit()
    assert result.state.remaining == remaining
    assert result.state.reset_after == quota.get_period_sec()


class TestSlidingWindowRateLimiter:
    def test_limit(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        limit: int = 5
        period: int = 60
        quota: Quota = Quota(Rate(period=timedelta(minutes=1), limit=limit))
        assert quota.get_limit() == limit
        assert quota.get_period_sec() == period

        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
        store_key: str = f"throttled:v1:sliding_window:key:period:{now_sec() // period}"
        assert rate_limiter._store.exists(store_key) is False

        for case in parametrizes.SLIDING_WINDOW_LIMIT_CASES:
            result: RateLimitResult = rate_limiter.limit("key", cost=case["cost"])
            assert_rate_limit_result(case["limited"], case["remaining"], quota, result)
            assert rate_limiter._store.get(store_key) == case["count"]
            if "ttl" in case:
                assert rate_limiter._store.ttl(store_key) == case["ttl"]

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
            assert abs(accessed_num - limit) <= (elapsed + 2) * rate

        with Timer(callback=_callback):
            rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
            results: List[bool] = benchmark.concurrent(
                task=lambda: rate_limiter.limit("key").limited, batch=requests_num
            )

    def test_peek(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(per_min(1))
        assert rate_limiter.peek(key) == RateLimitState(
            limit=1, remaining=1, reset_after=60
        )
        rate_limiter.limit(key)
        assert rate_limiter.peek(key) == RateLimitState(
            limit=1, remaining=0, reset_after=60
        )
