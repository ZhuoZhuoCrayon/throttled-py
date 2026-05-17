from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ... import constants, types
from ...rate_limiter.gcra import (
    GCRARateLimiterCoreMixin,
    MemoryLimitActionLogic,
    MemoryPeekActionLogic,
    RedisLimitAtomicActionSpec,
    RedisPeekAtomicActionSpec,
)
from .. import store
from . import BaseRateLimiter, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


class RedisLimitAtomicAction(RedisLimitAtomicActionSpec, store.BaseRedisAtomicAction):
    """Redis-based implementation of AtomicAction for Async GCRARateLimiter."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = self._register_script(self.SCRIPTS)

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", await self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicAction(RedisPeekAtomicActionSpec, store.BaseRedisAtomicAction):
    """Redis-based AtomicAction for GCRARateLimiter's peek operation."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = self._register_script(self.SCRIPTS)

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", await self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class MemoryPeekAtomicAction(MemoryPeekActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based AtomicAction for GCRARateLimiter's peek operation."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_PEEK


class GCRARateLimiter(
    GCRARateLimiterCoreMixin,
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisPeekAtomicAction,
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
        MemoryPeekAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, float, float]",
            await self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
                [formatted_key], [emission_interval, capacity, cost]
            ),
        )

        return RateLimitResult(
            limited=bool(limited),
            state_values=(capacity, remaining, reset_after, retry_after),
        )

    async def _peek(self, key: str) -> RateLimitState:
        formatted_key, emission_interval, capacity = self._prepare(key)
        _limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, float, float]",
            await self._atomic_actions[constants.ATOMIC_ACTION_TYPE_PEEK].do(
                [formatted_key], [emission_interval, capacity]
            ),
        )
        return RateLimitState(
            limit=capacity,
            remaining=remaining,
            reset_after=reset_after,
            retry_after=retry_after,
        )
