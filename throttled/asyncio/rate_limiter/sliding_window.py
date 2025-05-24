import math
from typing import List, Optional, Sequence, Tuple, Type

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.sliding_window import (
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionCoreMixin,
    SlidingWindowRateLimiterCoreMixin,
)
from ...types import AtomicActionP, KeyT, StoreValueT
from ...utils import now_ms
from ..store import BaseAtomicAction
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for Async SlidingWindowRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float]:
        return await self._script(keys, args)


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for Async SlidingWindowRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class SlidingWindowRateLimiter(SlidingWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using sliding window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[AtomicActionP]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        current_key, previous_key, period, limit = self._prepare(key)
        limited, used, retry_after = await self._atomic_actions[
            ATOMIC_ACTION_TYPE_LIMIT
        ].do([current_key, previous_key], [period, limit, cost, now_ms()])
        return RateLimitResult(
            limited=bool(limited),
            state_values=(limit, max(0, limit - used), period, retry_after),
        )

    async def _peek(self, key: str) -> RateLimitState:
        current_key, previous_key, period, limit = self._prepare(key)
        period_ms: int = period * 1000
        current_proportion: float = (now_ms() % period_ms) / period_ms

        previous: int = math.floor(
            (1 - current_proportion) * (await self._store.get(previous_key) or 0)
        )
        used: int = previous + (await self._store.get(current_key) or 0)

        return RateLimitState(
            limit=limit, remaining=max(0, limit - used), reset_after=period
        )
