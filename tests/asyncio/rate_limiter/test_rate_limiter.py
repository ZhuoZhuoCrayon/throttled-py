from collections.abc import Sequence
from typing import TypeVar, cast

import pytest
from throttled.asyncio import (
    BaseRateLimiter,
    RateLimiterRegistry,
    constants,
    per_sec,
    types,
)
from throttled.exceptions import StoreUnavailableError

_MakeAtomicT = TypeVar("_MakeAtomicT")


class _UnavailableAtomicAction(types.AsyncAtomicActionP):
    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = constants.StoreType.REDIS.value

    async def do(
        self, keys: Sequence[types.KeyT], args: Sequence[types.StoreValueT] | None
    ) -> tuple[int | float, ...]:
        raise StoreUnavailableError("store unavailable")


class _OperationUnavailableStore(types.AsyncStoreP):
    TYPE: str = constants.StoreType.REDIS.value

    def make_atomic(self, action_cls: type[_MakeAtomicT]) -> _MakeAtomicT:
        return cast("_MakeAtomicT", _UnavailableAtomicAction())

    async def exists(self, key: types.KeyT) -> bool:
        raise StoreUnavailableError("store unavailable")

    async def ttl(self, key: types.KeyT) -> int:
        raise StoreUnavailableError("store unavailable")

    async def expire(self, key: types.KeyT, timeout: int) -> None:
        raise StoreUnavailableError("store unavailable")

    async def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        raise StoreUnavailableError("store unavailable")

    async def get(self, key: types.KeyT) -> types.StoreValueT | None:
        raise StoreUnavailableError("store unavailable")

    async def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        raise StoreUnavailableError("store unavailable")

    async def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        raise StoreUnavailableError("store unavailable")


class _InitUnavailableStore(_OperationUnavailableStore):
    def make_atomic(self, action_cls: type[_MakeAtomicT]) -> _MakeAtomicT:
        raise StoreUnavailableError("store unavailable")


def _build_rate_limiter(
    limiter_type: str, store: types.AsyncStoreP | None = None
) -> BaseRateLimiter:
    limiter_cls = RateLimiterRegistry.get(limiter_type)
    return limiter_cls(per_sec(1), store or _OperationUnavailableStore())


@pytest.mark.asyncio
class TestRateLimiter:
    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    async def test_init__store_unavailable(cls, limiter_type: str) -> None:
        with pytest.raises(StoreUnavailableError):
            _build_rate_limiter(limiter_type, _InitUnavailableStore())

    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    async def test_limit__store_unavailable(cls, limiter_type: str) -> None:
        rate_limiter = _build_rate_limiter(limiter_type)
        with pytest.raises(StoreUnavailableError):
            await rate_limiter.limit("key")

    @classmethod
    @pytest.mark.parametrize("limiter_type", constants.RateLimiterType.choice())
    async def test_peek__store_unavailable(cls, limiter_type: str) -> None:
        rate_limiter = _build_rate_limiter(limiter_type)
        with pytest.raises(StoreUnavailableError):
            await rate_limiter.peek("key")
