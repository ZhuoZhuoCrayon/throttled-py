import pytest
from throttled import (
    BaseRateLimiter,
    RateLimiterRegistry,
    constants,
    exceptions,
    per_sec,
)

from ..store.unavailable import OperationUnavailableStore, UnavailableStore


def _build_rate_limiter(limiter_type: str) -> BaseRateLimiter:
    limiter_cls = RateLimiterRegistry.get(limiter_type)
    return limiter_cls(per_sec(1), OperationUnavailableStore())


class TestRateLimiter:
    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    def test_init__store_unavailable(cls, limiter_type: str) -> None:
        limiter_cls = RateLimiterRegistry.get(limiter_type)
        with pytest.raises(exceptions.StoreUnavailableError):
            limiter_cls(per_sec(1), UnavailableStore())

    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    def test_limit__store_unavailable(cls, limiter_type: str) -> None:
        rate_limiter = _build_rate_limiter(limiter_type)
        with pytest.raises(exceptions.StoreUnavailableError):
            rate_limiter.limit("key")

    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    def test_peek__store_unavailable(cls, limiter_type: str) -> None:
        rate_limiter = _build_rate_limiter(limiter_type)
        with pytest.raises(exceptions.StoreUnavailableError):
            rate_limiter.peek("key")
