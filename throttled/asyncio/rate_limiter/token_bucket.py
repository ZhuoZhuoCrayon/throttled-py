import math
from typing import List, Optional, Sequence, Tuple, Type

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.token_bucket import (
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionCoreMixin,
    TokenBucketRateLimiterCoreMixin,
)
from ...types import AtomicActionP, KeyT, StoreDictValueT, StoreValueT
from ...utils import now_sec
from ..store import BaseAtomicAction
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for Async TokenBucketRateLimiter."""

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


class TokenBucketRateLimiter(TokenBucketRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using leaking bucket as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[AtomicActionP]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, rate, capacity = self._prepare(key)
        limited, tokens = await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
            [formatted_key], [rate, capacity, cost, now_sec()]
        )
        reset_after: int = math.ceil((capacity - tokens) / rate)
        retry_after: int = 0
        if limited:
            retry_after = math.ceil(cost / rate)
        return RateLimitResult(
            limited=bool(limited),
            state_values=(capacity, tokens, reset_after, retry_after),
        )

    async def _peek(self, key: str) -> RateLimitState:
        now: int = now_sec()
        formatted_key, rate, capacity = self._prepare(key)

        bucket: StoreDictValueT = await self._store.hgetall(formatted_key)
        last_tokens: int = bucket.get("tokens", capacity)
        last_refreshed: int = bucket.get("last_refreshed", now)

        time_elapsed: int = max(0, now - last_refreshed)
        tokens: int = min(capacity, last_tokens + (math.floor(time_elapsed * rate)))
        reset_after: int = math.ceil((capacity - tokens) / rate)

        return RateLimitState(limit=capacity, remaining=tokens, reset_after=reset_after)
