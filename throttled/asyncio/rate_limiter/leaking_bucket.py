import math
from typing import List, Optional, Sequence, Tuple, Type

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.leaking_bucket import (
    LeakingBucketRateLimiterCoreMixin,
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionCoreMixin,
)
from ...types import KeyT, StoreDictValueT, StoreValueT
from ...utils import now_sec
from ..store import BaseAtomicAction
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        return await self._script(keys, args)


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class LeakingBucketRateLimiter(LeakingBucketRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using leaking bucket as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[BaseAtomicAction]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, rate, capacity = self._prepare(key)
        limited, tokens = await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
            [formatted_key], [rate, capacity, cost, now_sec()]
        )
        return self._to_result(limited, cost, tokens, capacity)

    async def _peek(self, key: str) -> RateLimitState:
        now: int = now_sec()
        formatted_key, rate, capacity = self._prepare(key)

        bucket: StoreDictValueT = await self._store.hgetall(formatted_key)
        last_tokens: int = bucket.get("tokens", 0)
        last_refreshed: int = bucket.get("last_refreshed", now)

        time_elapsed: int = max(0, now - last_refreshed)
        tokens: int = max(0, last_tokens - math.floor(time_elapsed * rate))

        return RateLimitState(
            limit=capacity,
            remaining=capacity - tokens,
            reset_after=math.ceil(tokens / rate),
        )
