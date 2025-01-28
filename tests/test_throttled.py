from typing import Callable

import pytest

from throttled import Throttled, rate_limter, store
from throttled.constants import RateLimiterType
from throttled.exceptions import LimitedError


@pytest.fixture
def decorated_demo() -> Callable:
    @Throttled(
        key="/api/product",
        using=RateLimiterType.FIXED_WINDOW.value,
        quota=rate_limter.per_min(1),
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
