from collections.abc import Awaitable, Callable, Coroutine
from functools import partial
from typing import Any

import pytest
from throttled.asyncio import (
    RateLimiterType,
    Throttled,
    exceptions,
    per_sec,
    rate_limiter,
    store,
    types,
    utils,
)
from throttled.asyncio.hooks import Hook
from throttled.rate_limiter import RateLimitResult


@pytest.fixture
def decorated_demo() -> Callable[[int, int], Coroutine]:
    @Throttled(
        key="/api/product",
        using=RateLimiterType.FIXED_WINDOW.value,
        quota=rate_limiter.per_min(1),
        store=store.MemoryStore(),
    )
    async def demo(left: int, right: int) -> int:
        return left + right

    return demo


EXPECTED_RESULT = 3
EXPECTED_HOOK_CALL_COUNT = 2


@pytest.mark.asyncio
class TestThrottled:
    @classmethod
    async def test_demo(cls, decorated_demo: Callable[[int, int], Coroutine]) -> None:
        assert await decorated_demo(1, 2) == EXPECTED_RESULT
        with pytest.raises(exceptions.LimitedError):
            await decorated_demo(2, 3)

    @classmethod
    async def test_limit__timeout(cls):
        throttle: Throttled = Throttled(timeout=1, quota=per_sec(1))
        assert (await throttle.limit("key")).limited is False

        def _callback(
            left: float, right: float, elapsed: types.TimeLikeValueT, *args, **kwargs
        ):
            assert left <= elapsed < right

        async with utils.Timer(callback=partial(_callback, 1, 2)):
            assert (await throttle.limit("key")).limited is False

        # case: retry_after > timeout
        async with utils.Timer(callback=partial(_callback, 0, 0.1)):
            assert (await throttle.limit("key", cost=2)).limited

        # case: timeout < retry_after
        async with utils.Timer(callback=partial(_callback, 0, 0.1)):
            assert (await throttle.limit("key", timeout=0.5)).limited

    @classmethod
    async def test_enter(cls):
        construct_kwargs: dict[str, Any] = {
            "key": "key",
            "quota": per_sec(1),
            "store": store.MemoryStore(),
        }
        throttle: Throttled = Throttled(**construct_kwargs)
        async with throttle as rate_limit_result:
            assert rate_limit_result.limited is False

        with pytest.raises(exceptions.LimitedError) as exc_info:
            async with throttle:
                pass
        assert exc_info.value.rate_limit_result.limited
        assert exc_info.value.rate_limit_result.state.remaining == 0
        assert exc_info.value.rate_limit_result.state.reset_after == 1
        assert exc_info.value.rate_limit_result.state.retry_after == 1

        async with Throttled(**construct_kwargs, timeout=1) as rate_limit_result:
            assert not rate_limit_result.limited

    @classmethod
    async def test_hook__execution_order(cls) -> None:
        """Throttled should execute hooks in correct middleware order.

        hooks=[A, B] should execute: A_before → B_before → limit → B_after → A_after
        """
        order: list[str] = []

        class OrderHook(Hook):
            def __init__(self, name: str):
                self.name = name

            async def on_limit(self, *args, **kwargs) -> RateLimitResult:
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                order.append(f"{self.name}_before")
                result: RateLimitResult = await call_next()
                order.append(f"{self.name}_after")
                return result

        throttle: Throttled = Throttled(
            key="test",
            quota=per_sec(10),
            hooks=[OrderHook("A"), OrderHook("B")],
        )

        await throttle.limit()

        assert order == ["A_before", "B_before", "B_after", "A_after"]

    @classmethod
    async def test_hook__called_once_per_limit_even_with_retry(cls) -> None:
        """Hook should be called once per limit() call, not per retry attempt.

        This test ensures that when timeout/retry is enabled, the hook wraps
        the entire limit() operation (including retries), not each individual
        retry attempt.
        """
        call_count: int = 0

        class CountingHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                nonlocal call_count
                call_count += 1
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                return await call_next()

        throttle: Throttled = Throttled(
            key="test",
            quota=per_sec(1),
            timeout=2,  # Enable retry
            hooks=[CountingHook()],
        )

        # First call: allowed immediately
        await throttle.limit()
        # Second call: denied initially, then retries and succeeds after ~1s
        await throttle.limit()

        # Hook should be called exactly 2 times (once per limit() call)
        # NOT more times due to internal retry attempts
        assert call_count == EXPECTED_HOOK_CALL_COUNT
