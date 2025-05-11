from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Type

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.fixed_window import (
    FixedWindowRateLimiterCoreMixin,
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionCoreMixin,
)
from ...types import KeyT, StoreValueT
from ..store import BaseAtomicAction
from . import BaseRateLimiter, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from ..store import MemoryStoreBackend, RedisStoreBackend


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for Async FixedWindowRateLimiter."""

    def __init__(self, backend: "RedisStoreBackend"):
        self._backend: RedisStoreBackend = backend

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        period, limit, cost = args
        current: int = await self._backend.get_client().incrby(keys[0], cost)
        if current == cost:
            await self._backend.get_client().expire(keys[0], period)
        return [0, 1][current > limit], current


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for Async FixedWindowRateLimiter."""

    def __init__(self, backend: "MemoryStoreBackend"):
        self._backend: MemoryStoreBackend = backend

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class FixedWindowRateLimiter(FixedWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[BaseAtomicAction]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(
            self.quota, self._prepare_key(key)
        )
        limited, current = await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
            [period_key], [period, limit, cost]
        )

        reset_after: float = period - (now % period)
        return RateLimitResult(
            limited=bool(limited),
            state_values=(
                limit,
                max(0, limit - current),
                reset_after,
                (0, reset_after)[limited],
            ),
        )

    async def _peek(self, key: str) -> RateLimitState:
        period_key, period, limit, now = self._prepare(
            self.quota, self._prepare_key(key)
        )
        current: int = int(await self._store.get(period_key) or 0)
        return RateLimitState(
            limit=limit,
            remaining=max(0, limit - current),
            reset_after=period - (now % period),
        )
