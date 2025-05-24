from datetime import timedelta
from typing import Callable, List

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
from throttled.utils import Benchmark, now_sec

from . import parametrizes


@pytest.fixture
def rate_limiter_constructor(store: BaseStore) -> Callable[[Quota], BaseRateLimiter]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(RateLimiterType.FIXED_WINDOW.value)(quota, store)

    yield _create_rate_limiter


class TestFixedWindowRateLimiter:
    def test_limit(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        limit: int = 5
        period: int = 60
        quota: Quota = Quota(Rate(period=timedelta(minutes=1), limit=limit))
        assert quota.get_limit() == limit
        assert quota.get_period_sec() == period

        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        store_key: str = f"throttled:v1:fixed_window:key:period:{now_sec() // period}"
        assert rate_limiter._store.exists(store_key) is False

        def _assert(_remaining: int, _result: RateLimitResult):
            assert _result.state.limit == limit
            assert _result.state.remaining == _remaining
            assert _result.state.reset_after == period - (now_sec() % period)
            if _result.limited:
                assert _result.state.retry_after == _result.state.reset_after

        result: RateLimitResult = rate_limiter.limit(key)
        _assert(4, result)
        assert result.limited is False
        assert rate_limiter._store.get(store_key) == 1
        assert rate_limiter._store.ttl(store_key) == period

        result: RateLimitResult = rate_limiter.limit(key, cost=4)
        _assert(0, result)
        assert result.limited is False
        assert rate_limiter._store.get(store_key) == 5

        result: RateLimitResult = rate_limiter.limit(key, cost=4)
        _assert(0, result)
        assert result.limited is True
        assert rate_limiter._store.get(store_key) == 9

    @parametrizes.LIMIT_C_QUOTA
    @parametrizes.LIMIT_C_REQUESTS_NUM
    def test_limit__concurrent(
        self,
        benchmark: Benchmark,
        rate_limiter_constructor: Callable[[Quota], BaseRateLimiter],
        quota: Quota,
        requests_num: int,
    ):
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
        results: List[bool] = benchmark.concurrent(
            task=lambda: rate_limiter.limit("key").limited, batch=requests_num
        )

        accessed_num: int = requests_num - sum(results)
        limit: int = min(requests_num, quota.get_limit())
        # Period boundaries may burst with 2 times the number of requests.
        assert limit <= accessed_num <= 2 * limit

    def test_peek(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(per_min(1))

        def _assert(_state: RateLimitState):
            assert _state.limit == 1
            assert _state.reset_after - (60 - (now_sec() % 60)) <= 1

        state: RateLimitState = rate_limiter.peek(key)
        _assert(state)
        assert state.remaining == 1

        rate_limiter.limit(key)

        state: RateLimitState = rate_limiter.peek(key)
        assert state.remaining == 0
        _assert(state)
