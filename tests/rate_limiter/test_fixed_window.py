from concurrent.futures import ThreadPoolExecutor
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
from throttled.utils import now_sec


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
        assert quota.get_limit() == 5
        assert quota.get_period_sec() == 60

        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        store_key: str = f"key:period:{now_sec() // period}"
        assert rate_limiter._store.exists(store_key) is False

        result: RateLimitResult = rate_limiter.limit(key)
        assert result.limited is False
        assert result.state == RateLimitState(
            limit=limit, remaining=4, reset_after=period
        )
        assert rate_limiter._store.get(store_key) == 1
        assert rate_limiter._store.ttl(store_key) == period

        result: RateLimitResult = rate_limiter.limit(key, cost=4)
        assert result.limited is False
        assert result.state == RateLimitState(
            limit=limit, remaining=0, reset_after=period
        )
        assert rate_limiter._store.get(store_key) == 5

        result: RateLimitResult = rate_limiter.limit(key, cost=4)
        assert result.limited is True
        assert result.state == RateLimitState(
            limit=limit, remaining=0, reset_after=period
        )
        assert rate_limiter._store.get(store_key) == 9

    @pytest.mark.parametrize(
        "quota", [per_min(1), per_min(10), per_min(100), per_min(1_000)]
    )
    @pytest.mark.parametrize("requests_num", [10, 100, 1_000, 10_000])
    def test_limit__current(
        self,
        rate_limiter_constructor: Callable[[Quota], BaseRateLimiter],
        quota: Quota,
        requests_num: int,
    ):
        def _task(_idx: int) -> bool:
            _result: RateLimitResult = rate_limiter.limit(key)
            return _result.limited

        key: str = "key"
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)
        with ThreadPoolExecutor(max_workers=32) as executor:
            results: List[bool] = list(executor.map(_task, range(requests_num)))

        accessed_num: int = requests_num - sum(results)
        limit: int = min(requests_num, quota.get_limit())
        # Period boundaries may burst with 2 times the number of requests.
        assert accessed_num == limit or accessed_num == 2 * limit

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
