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


@pytest.fixture
def rate_limiter_constructor(store: BaseStore) -> Callable[[Quota], BaseRateLimiter]:
    def _create_rate_limiter(quota: Quota) -> BaseRateLimiter:
        return RateLimiterRegistry.get(RateLimiterType.LEAKING_BUCKET.value)(
            quota, store
        )

    return _create_rate_limiter


class TestLeakingBucketRateLimiter:
    def test_limit(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        key: str = "key"
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        def _assert(_remaining: int, _result: RateLimitResult):
            assert _result.state.limit == quota.burst
            assert _result.state.remaining == _remaining
            assert _result.state.reset_after == quota.burst - _remaining
            if _result.limited:
                assert _result.state.retry_after == 1
            else:
                assert _result.state.retry_after == 0

        result: RateLimitResult = rate_limiter.limit(key)
        _assert(9, result)
        assert result.limited is False

        time.sleep(1)
        result: RateLimitResult = rate_limiter.limit(key, cost=5)
        _assert(5, result)
        assert result.limited is False

        result: RateLimitResult = rate_limiter.limit(key, cost=5)
        _assert(0, result)
        assert result.limited is False

        result: RateLimitResult = rate_limiter.limit(key)
        _assert(0, result)
        assert result.limited is True

    @pytest.mark.parametrize(
        "quota",
        [per_min(1, 1), per_min(10, 10), per_min(100, 100), per_min(1_000, 1_000)],
    )
    @pytest.mark.parametrize("requests_num", [10, 100, 1_000, 10_000])
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
            assert limit <= accessed_num <= limit + (elapsed + 5) * rate

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
        assert state == RateLimitState(limit=10, remaining=5, reset_after=5)

        time.sleep(1)
        state: RateLimitState = rate_limiter.peek(key)
        assert state.limit == 10
        assert 6 - state.remaining <= 1
        assert 4 - state.reset_after <= 4
