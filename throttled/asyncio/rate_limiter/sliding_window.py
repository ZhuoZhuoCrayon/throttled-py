import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ... import constants, types, utils
from ...rate_limiter.sliding_window import (
    MemoryLimitActionLogic,
    RedisLimitAtomActionSpec,
    SlidingWindowRateLimiterCoreMixin,
)
from .. import store
from . import BaseRateLimiter, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


class RedisLimitAtomicAction(RedisLimitAtomActionSpec, store.BaseRedisAtomicAction):
    """Redis-based implementation of AtomicAction for Async SlidingWindowRateLimiter."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = self._register_script(self.SCRIPTS)

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float]:
        limited, used, retry_after = cast(
            "tuple[int, int, str]", await self._script(keys, args)
        )
        return limited, used, float(retry_after)


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for Async SlidingWindowRateLimiter."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class SlidingWindowRateLimiter(SlidingWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using sliding window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        current_key, previous_key, period, limit = self._prepare(key)
        limited, used, retry_after = cast(
            "tuple[int, int, float]",
            await self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
                [current_key, previous_key], [period, limit, cost, utils.now_ms()]
            ),
        )
        return RateLimitResult(
            limited=bool(limited),
            state_values=(limit, max(0, limit - used), period, retry_after),
        )

    async def _peek(self, key: str) -> RateLimitState:
        current_key, previous_key, period, limit = self._prepare(key)
        period_ms: int = period * 1000
        current_proportion: float = (utils.now_ms() % period_ms) / period_ms

        previous: int = math.floor(
            (1 - current_proportion) * int(await self._store.get(previous_key) or 0)
        )
        used: int = previous + int(await self._store.get(current_key) or 0)

        return RateLimitState(
            limit=limit, remaining=max(0, limit - used), reset_after=period
        )
