from collections.abc import Callable
from functools import partial
from typing import Any
from unittest.mock import MagicMock

import pytest
from throttled import RateLimiterType, Throttled, per_sec, rate_limiter, store
from throttled.exceptions import BaseThrottledError, DataError, LimitedError
from throttled.hooks import Hook
from throttled.rate_limiter import RateLimitResult
from throttled.types import TimeLikeValueT
from throttled.utils import Timer

# Test constants
EXPECTED_SUM = 3  # 1 + 2
TIMEOUT_10 = 10
TIMEOUT_20 = 20
EXPECTED_HOOK_CALL_COUNT = 2
EXPECTED_REMAINING = 0
EXPECTED_RESET_AFTER = 1
EXPECTED_RETRY_AFTER = 1


@pytest.fixture
def decorated_demo() -> Callable:
    @Throttled(
        key="/api/product",
        using=RateLimiterType.FIXED_WINDOW.value,
        quota=rate_limiter.per_min(1),
        store=store.MemoryStore(),
    )
    def demo(left: int, right: int) -> int:
        return left + right

    return demo


class TestThrottled:
    @classmethod
    def test_demo(cls, decorated_demo: Callable) -> None:
        assert decorated_demo(1, 2) == EXPECTED_SUM
        with pytest.raises(LimitedError):
            decorated_demo(2, 3)

    @classmethod
    @pytest.mark.parametrize(
        ("constructor_kwargs", "exc", "match"),
        [
            ({"timeout": -2}, DataError, "Invalid timeout"),
            ({"timeout": "a"}, DataError, "Invalid timeout"),
            ({"timeout": -1.1}, DataError, "Invalid timeout"),
            ({"timeout": 0}, DataError, "Invalid timeout"),
            ({"timeout": 0.0}, DataError, "Invalid timeout"),
            ({"timeout": -0.0}, DataError, "Invalid timeout"),
        ],
    )
    def test_constructor__raise(
        cls,
        constructor_kwargs: dict[str, Any],
        exc: type[BaseThrottledError],
        match: str,
    ) -> None:
        with pytest.raises(exc, match=match):
            Throttled(**constructor_kwargs)

    @classmethod
    def test_get_key(cls) -> None:
        throttle: Throttled = Throttled(key="key")
        assert throttle._get_key() == "key"
        assert throttle._get_key(key="override_key") == "override_key"
        assert throttle._get_key(key="") == "key"
        assert throttle._get_key(key=None) == "key"

        for _throttle in [Throttled(), Throttled(key=""), Throttled(key=None)]:
            with pytest.raises(DataError, match="Invalid key"):
                _throttle(lambda _: None)

            with pytest.raises(DataError, match="Invalid key"):
                _throttle._get_key()

            with pytest.raises(DataError, match="Invalid key"):
                _throttle._get_key(key="")

            assert _throttle._get_key(key="override_key") == "override_key"

    @classmethod
    def test_get_timeout(cls) -> None:
        throttle: Throttled = Throttled(timeout=TIMEOUT_10)
        assert throttle._get_timeout() == TIMEOUT_10
        assert throttle._get_timeout(timeout=TIMEOUT_20) == TIMEOUT_20
        assert throttle._get_timeout(timeout=-1) == -1

        with pytest.raises(DataError, match="Invalid timeout"):
            throttle._get_timeout(timeout=0)

        with pytest.raises(DataError, match="Invalid timeout"):
            throttle._get_timeout(timeout=-2)

    @classmethod
    def test_limit__timeout(cls) -> None:
        throttle: Throttled = Throttled(timeout=1, quota=per_sec(1))
        assert not throttle.limit("key").limited

        def _callback(
            left: float, right: float, elapsed: TimeLikeValueT, *args: Any, **kwargs: Any
        ) -> None:
            assert left <= elapsed < right

        with Timer(callback=partial(_callback, 1, 2)):
            assert not throttle.limit("key").limited

        # case: retry_after > timeout
        with Timer(callback=partial(_callback, 0, 0.1)):
            assert throttle.limit("key", cost=2).limited

        # case: timeout < retry_after
        with Timer(callback=partial(_callback, 0, 0.1)):
            assert throttle.limit("key", timeout=0.5).limited

    @classmethod
    def test_enter(cls) -> None:
        mem_store: store.MemoryStore = store.MemoryStore()
        construct_kwargs: dict[str, Any] = {
            "key": "key",
            "quota": per_sec(1),
            "store": mem_store,
        }
        throttle: Throttled = Throttled(**construct_kwargs)
        with throttle as rate_limit_result:
            assert not rate_limit_result.limited

        with pytest.raises(LimitedError) as exc_info, throttle:
            pass
        assert exc_info.value.rate_limit_result.limited
        assert exc_info.value.rate_limit_result.state.remaining == EXPECTED_REMAINING
        assert exc_info.value.rate_limit_result.state.reset_after == EXPECTED_RESET_AFTER
        assert exc_info.value.rate_limit_result.state.retry_after == EXPECTED_RETRY_AFTER

        with Throttled(**construct_kwargs, timeout=1) as rate_limit_result:
            assert not rate_limit_result.limited

    @classmethod
    def test_hook__execution_order(cls) -> None:
        """Throttled should execute hooks in correct middleware order.

        hooks=[A, B] should execute: A_before → B_before → limit → B_after → A_after
        """
        order: list[str] = []

        class OrderHook(Hook):
            def __init__(self, name: str):
                self.name = name

            def on_limit(self, *args, **kwargs) -> RateLimitResult:
                call_next: Callable[[], RateLimitResult] = args[0]
                order.append(f"{self.name}_before")
                result: RateLimitResult = call_next()
                order.append(f"{self.name}_after")
                return result

        throttle: Throttled = Throttled(
            key="test",
            quota=per_sec(10),
            hooks=[OrderHook("A"), OrderHook("B")],
        )

        throttle.limit()

        assert order == ["A_before", "B_before", "B_after", "A_after"]

    @classmethod
    def test_hook__called_once_per_limit_even_with_retry(cls) -> None:
        """Hook should be called once per limit() call, not per retry attempt.

        This test ensures that when timeout/retry is enabled, the hook wraps
        the entire limit() operation (including retries), not each individual
        retry attempt.
        """
        mock_hook: MagicMock = MagicMock(spec=Hook)
        mock_hook.on_limit.side_effect = lambda call_next, ctx: call_next()

        throttle: Throttled = Throttled(
            key="test",
            quota=per_sec(1),
            timeout=2,  # Enable retry
            hooks=[mock_hook],
        )

        # First call: allowed immediately
        throttle.limit()
        # Second call: denied initially, then retries and succeeds after ~1s
        throttle.limit()

        # Hook should be called exactly 2 times (once per limit() call)
        # NOT more times due to internal retry attempts
        assert mock_hook.on_limit.call_count == EXPECTED_HOOK_CALL_COUNT
