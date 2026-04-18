from collections.abc import Sequence
from typing import cast

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.fixed_window import (
    FixedWindowRateLimiterCoreMixin,
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionConstants,
)
from ...store.base import BaseAtomicActionMixin
from ...types import (
    AsyncAtomicActionP,
    AsyncStoreP,
    KeyT,
    StoreValueT,
)
from ..store import BaseAtomicAction
from ..store.memory import MemoryStoreBackend
from ..store.redis import RedisStoreBackend
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class RedisLimitAtomicActionCoreMixin(
    RedisLimitAtomicActionConstants, BaseAtomicActionMixin[RedisStoreBackend]
):
    """Core mixin for async RedisLimitAtomicAction."""


class RedisLimitAtomicAction(
    RedisLimitAtomicActionCoreMixin, BaseAtomicAction[RedisStoreBackend]
):
    """Redis-based implementation of AtomicAction for Async FixedWindowRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int]:
        if args is None:
            raise ValueError("args is required")
        period: int = int(args[0])
        limit: int = int(args[1])
        cost: int = int(args[2])
        client = self._backend.get_client()
        current: int = await client.incrby(keys[0], cost)
        if current == cost:
            await client.expire(keys[0], period)
        return [0, 1][current > limit and cost != 0], current


class MemoryLimitAtomicAction(
    MemoryLimitAtomicActionCoreMixin[MemoryStoreBackend],
    BaseAtomicAction[MemoryStoreBackend],
):
    """Memory-based implementation of AtomicAction for Async FixedWindowRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class FixedWindowRateLimiter(
    FixedWindowRateLimiterCoreMixin[AsyncStoreP, AsyncAtomicActionP],
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[AsyncAtomicActionP]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(key)
        limited, current = cast(
            "tuple[int, int]",
            await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
                [period_key], [period, limit, cost]
            ),
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
        period_key, period, limit, now = self._prepare(key)
        current: int = int(await self._store.get(period_key) or 0)
        return RateLimitState(
            limit=limit,
            remaining=max(0, limit - current),
            reset_after=period - (now % period),
        )
