import pytest
from throttled.asyncio import (
    BaseRateLimiter,
    BaseStore,
    RateLimiterRegistry,
    constants,
    exceptions,
    per_sec,
)

from ..store.unavailable import OperationUnavailableStore, UnavailableStore


def _build_rate_limiter(
    limiter_type: str, store: BaseStore | None = None
) -> BaseRateLimiter:
    limiter_cls = RateLimiterRegistry.get(limiter_type)
    return limiter_cls(per_sec(1), store or OperationUnavailableStore())


@pytest.mark.asyncio
class TestRateLimiter:
    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    async def test_init__store_unavailable(cls, limiter_type: str) -> None:
        with pytest.raises(exceptions.StoreUnavailableError):
            _build_rate_limiter(limiter_type, UnavailableStore())

    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    async def test_limit__store_unavailable(cls, limiter_type: str) -> None:
        rate_limiter = _build_rate_limiter(limiter_type)
        with pytest.raises(exceptions.StoreUnavailableError):
            await rate_limiter.limit("key")

    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    async def test_peek__store_unavailable(cls, limiter_type: str) -> None:
        rate_limiter = _build_rate_limiter(limiter_type)
        with pytest.raises(exceptions.StoreUnavailableError):
            await rate_limiter.peek("key")
