import time
from collections.abc import Callable
from unittest import mock

import pytest
from throttled import (
    BaseRateLimiter,
    BaseStore,
    MemoryStore,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    RedisStore,
    per_min,
    per_sec,
)
from throttled.constants import RateLimiterType
from throttled.rate_limiter.gcra import (
    RedisLimitAtomicActionSpec,
    RedisPeekAtomicActionSpec,
)
from throttled.types import TimeLikeValueT
from throttled.utils import Benchmark, Timer

from . import parametrizes

REDIS_CLOCK_EPOCH: int = 1735660800
"""The offset the GCRA Lua scripts subtract from the Redis clock."""


@pytest.fixture
def rate_limiter_constructor(
    store: BaseStore,
) -> Callable[[Quota], BaseRateLimiter]:
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
            results: list[bool] = benchmark.concurrent(
                task=lambda: rate_limiter.limit("key").limited, batch=requests_num
            )

    @classmethod
    def test_limit__fresh_key_first_request_allowed(cls) -> None:
        """The first request for an unseen key passes when burst equals cost.

        Deriving allow_at as (now + interval) - interval can round just above
        now, which rejected unseen keys outright for many clock values - most
        likely on recently booted machines, where time.monotonic() is small.
        """
        rate_limiter: BaseRateLimiter = RateLimiterRegistry.get(
            RateLimiterType.GCRA.value
        )(per_min(limit=1, burst=1), MemoryStore())
        for idx in range(4096):
            now: float = 30.0 + idx * 0.0173
            with mock.patch("throttled.utils.now_mono_f", return_value=now):
                result: RateLimitResult = rate_limiter.limit(f"key-{idx}")
            assert not result.limited, f"first request rejected at now={now!r}"
            assert result.state.remaining == 0

    @classmethod
    def test_redis_clock_epoch__matches_lua_scripts(cls) -> None:
        """The Redis sweeps below must land just past the scripts' offset, so
        drift would be a silent loss of coverage.
        """
        for scripts in (
            RedisLimitAtomicActionSpec.SCRIPTS,
            RedisPeekAtomicActionSpec.SCRIPTS,
        ):
            assert f"local jan_1_2025 = {REDIS_CLOCK_EPOCH}" in scripts

    @classmethod
    def test_limit__fresh_key_first_request_allowed_redis(
        cls, redis_store: RedisStore
    ) -> None:
        """As the memory variant, but driving the Lua script's clock."""
        rate_limiter: BaseRateLimiter = RateLimiterRegistry.get(
            RateLimiterType.GCRA.value
        )(per_min(limit=1, burst=1), redis_store)
        for idx in range(4096):
            now: float = REDIS_CLOCK_EPOCH + 30.0 + idx * 0.0173
            with mock.patch("time.time", return_value=now):
                result: RateLimitResult = rate_limiter.limit(f"key-{idx}")
            assert not result.limited, f"first request rejected at time={now!r}"
            assert result.state.remaining == 0

    @classmethod
    def test_peek__fresh_key_reports_full_burst(cls) -> None:
        """Peek on an unseen key reports the whole burst as remaining.

        An emission interval without an exact binary representation (1/3s
        here) used to make the allow_at derivation round against the key,
        reporting it as limited before it ever made a request.
        """
        rate_limiter: BaseRateLimiter = RateLimiterRegistry.get(
            RateLimiterType.GCRA.value
        )(per_sec(limit=3, burst=1), MemoryStore())
        for idx in range(4096):
            now: float = 30.0 + idx * 0.0173
            with mock.patch("throttled.utils.now_mono_f", return_value=now):
                state: RateLimitState = rate_limiter.peek(f"key-{idx}")
            assert state == RateLimitState(
                limit=1, remaining=1, reset_after=0, retry_after=0
            ), f"peek misreported at now={now!r}"

    @classmethod
    def test_peek__fresh_key_reports_full_burst_redis(
        cls, redis_store: RedisStore
    ) -> None:
        """As the memory variant, but driving the Lua script's clock."""
        rate_limiter: BaseRateLimiter = RateLimiterRegistry.get(
            RateLimiterType.GCRA.value
        )(per_sec(limit=3, burst=1), redis_store)
        for idx in range(4096):
            now: float = REDIS_CLOCK_EPOCH + 30.0 + idx * 0.0173
            with mock.patch("time.time", return_value=now):
                state: RateLimitState = rate_limiter.peek(f"key-{idx}")
            assert state == RateLimitState(
                limit=1, remaining=1, reset_after=0, retry_after=0
            ), f"peek misreported at time={now!r}"

    def test_peek(self, rate_limiter_constructor: Callable[[Quota], BaseRateLimiter]):
        key: str = "key"
        quota: Quota = per_min(limit=60, burst=10)
        rate_limiter: BaseRateLimiter = rate_limiter_constructor(quota)

        state: RateLimitState = rate_limiter.peek(key)
        assert state == RateLimitState(limit=10, remaining=10, reset_after=0)

        rate_limiter.limit(key, cost=5)
        state = rate_limiter.peek(key)
        assert state.limit == 10 and state.remaining == 5
        assert 5 - state.reset_after < 0.1

        time.sleep(1)
        state = rate_limiter.peek(key)
        assert state.limit == 10 and state.remaining == 6
        assert 4 - state.reset_after < 0.1

        rate_limiter.limit(key, cost=6)
        state = rate_limiter.peek(key)
        assert state.remaining == 0
        assert 10 - state.reset_after < 0.1
