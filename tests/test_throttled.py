from typing import Any, Callable, Dict, Type

import pytest

from throttled import Throttled, per_sec, rate_limiter, store
from throttled.constants import RateLimiterType
from throttled.exceptions import BaseThrottledError, DataError, LimitedError
from throttled.utils import now_sec_f


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

    yield demo


class TestThrottled:
    def test_demo(self, decorated_demo: Callable) -> None:
        assert decorated_demo(1, 2) == 3
        with pytest.raises(LimitedError):
            decorated_demo(2, 3)

    @pytest.mark.parametrize(
        "constructor_kwargs,exc,match",
        [
            [{"timeout": -2}, DataError, "Invalid timeout"],
            [{"timeout": "a"}, DataError, "Invalid timeout"],
            [{"timeout": -1.1}, DataError, "Invalid timeout"],
            [{"timeout": 0}, DataError, "Invalid timeout"],
            [{"timeout": 0.0}, DataError, "Invalid timeout"],
            [{"timeout": -0.0}, DataError, "Invalid timeout"],
        ],
    )
    def test_constructor__raise(
        self,
        constructor_kwargs: Dict[str, Any],
        exc: Type[BaseThrottledError],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            Throttled(**constructor_kwargs)

    def test_get_key(self):
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

    def test_get_timeout(self):
        throttle: Throttled = Throttled(timeout=10)
        assert throttle._get_timeout() == 10
        assert throttle._get_timeout(timeout=20) == 20
        assert throttle._get_timeout(timeout=-1) == -1

        with pytest.raises(DataError, match="Invalid timeout"):
            throttle._get_timeout(timeout=0)

        with pytest.raises(DataError, match="Invalid timeout"):
            throttle._get_timeout(timeout=-2)

    def test_limit__timeout(self):
        throttle: Throttled = Throttled(timeout=1, quota=per_sec(1))
        assert not throttle.limit("key").limited

        start_time: float = now_sec_f()
        assert not throttle.limit("key").limited
        assert 1 <= now_sec_f() - start_time < 2

        # case: retry_after > timeout
        start_time: float = now_sec_f()
        assert throttle.limit("key", cost=2).limited
        assert 0 <= now_sec_f() - start_time < 0.1

        # case: timeout < retry_after
        start_time: float = now_sec_f()
        assert throttle.limit("key", timeout=0.5).limited
        assert 0 <= now_sec_f() - start_time < 0.1

    def test_enter(self):
        mem_store: store.MemoryStore = store.MemoryStore()
        construct_kwargs: Dict[str, Any] = {
            "key": "key",
            "quota": per_sec(1),
            "store": mem_store,
        }
        throttle: Throttled = Throttled(**construct_kwargs)
        with throttle as rate_limit_result:
            assert not rate_limit_result.limited

        try:
            with throttle:
                pass
        except LimitedError as e:
            assert e.rate_limit_result.limited
            assert e.rate_limit_result.state.remaining == 0
            assert e.rate_limit_result.state.reset_after == 1
            assert e.rate_limit_result.state.retry_after == 1

        with Throttled(**construct_kwargs, timeout=1) as rate_limit_result:
            assert not rate_limit_result.limited
