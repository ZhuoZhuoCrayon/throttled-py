from typing import Callable

import pytest

from throttled import MemoryStore, Throttled, per_min
from throttled.constants import RateLimiterType
from throttled.exceptions import LimitedError


@pytest.fixture
def decorated_demo() -> Callable:
    @Throttled(
        key="/api/product",
        using=RateLimiterType.FIXED_WINDOW.value,
        quota=per_min(1),
        store=MemoryStore(),
    )
    def demo(left: int, right: int) -> int:
        return left + right

    yield demo


class TestThrottled:
    def test_demo(self, decorated_demo: Callable) -> None:
        assert decorated_demo(1, 2) == 3
        with pytest.raises(LimitedError):
            decorated_demo(2, 3)
