from collections.abc import Sequence
from typing import cast

from ... import constants, types
from ...rate_limiter.fixed_window import (
    FixedWindowRateLimiterCoreMixin,
    MemoryLimitActionLogic,
    RedisLimitAtomicActionSpec,
)
from .. import store
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class RedisLimitAtomicAction(RedisLimitAtomicActionSpec, store.BaseRedisAtomicAction):
    """Redis-based implementation of AtomicAction for Async FixedWindowRateLimiter."""

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
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
        limited: int = int(current > limit and cost != 0)
        return limited, current


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for Async FixedWindowRateLimiter."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class FixedWindowRateLimiter(FixedWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(key)
        limited, current = cast(
            "tuple[int, int]",
            await self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
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
                reset_after if limited else 0,
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
