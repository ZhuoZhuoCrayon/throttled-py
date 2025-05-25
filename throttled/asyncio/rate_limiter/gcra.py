from typing import List, Optional, Sequence, Tuple, Type

from ...constants import ATOMIC_ACTION_TYPE_LIMIT, ATOMIC_ACTION_TYPE_PEEK
from ...rate_limiter.gcra import (
    GCRARateLimiterCoreMixin,
    MemoryLimitAtomicActionCoreMixin,
    MemoryPeekAtomicActionCoreMixin,
    RedisLimitAtomicActionCoreMixin,
    RedisPeekAtomicActionCoreMixin,
)
from ...types import AtomicActionP, KeyT, StoreValueT
from ..store import BaseAtomicAction
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for Async GCRARateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = await self._script(keys, args)
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicAction(RedisPeekAtomicActionCoreMixin, RedisLimitAtomicAction):
    """
    Redis-based implementation of AtomicAction for GCRARateLimiter's peek operation.
    """


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class MemoryPeekAtomicAction(MemoryPeekAtomicActionCoreMixin, MemoryLimitAtomicAction):
    """
    Memory-based implementation of AtomicAction for GCRARateLimiter's peek operation.
    """


class GCRARateLimiter(GCRARateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[AtomicActionP]] = [
        RedisPeekAtomicAction,
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
        MemoryPeekAtomicAction,
    ]

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = await self._atomic_actions[
            ATOMIC_ACTION_TYPE_LIMIT
        ].do([formatted_key], [emission_interval, capacity, cost])

        return RateLimitResult(
            limited=bool(limited),
            state_values=(capacity, remaining, reset_after, retry_after),
        )

    async def _peek(self, key: str) -> RateLimitState:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = await self._atomic_actions[
            ATOMIC_ACTION_TYPE_PEEK
        ].do([formatted_key], [emission_interval, capacity])
        return RateLimitState(
            limit=capacity,
            remaining=remaining,
            reset_after=reset_after,
            retry_after=retry_after,
        )
