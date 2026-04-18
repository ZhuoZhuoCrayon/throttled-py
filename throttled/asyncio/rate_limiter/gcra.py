from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ...constants import ATOMIC_ACTION_TYPE_LIMIT, ATOMIC_ACTION_TYPE_PEEK
from ...rate_limiter.gcra import (
    GCRARateLimiterCoreMixin,
    MemoryLimitAtomicActionCoreMixin,
    MemoryPeekAtomicActionCoreMixin,
    RedisLimitAtomicActionConstants,
    RedisPeekAtomicActionConstants,
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

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


class RedisLimitAtomicActionCoreMixin(
    RedisLimitAtomicActionConstants, BaseAtomicActionMixin[RedisStoreBackend]
):
    """Core mixin for async RedisLimitAtomicAction."""

    def __init__(self, backend: RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = backend.get_client().register_script(self.SCRIPTS)


class RedisLimitAtomicAction(
    RedisLimitAtomicActionCoreMixin, BaseAtomicAction[RedisStoreBackend]
):
    """Redis-based implementation of AtomicAction for Async GCRARateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", await self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicActionCoreMixin(
    RedisPeekAtomicActionConstants, BaseAtomicActionMixin[RedisStoreBackend]
):
    """Core mixin for async RedisPeekAtomicAction."""

    def __init__(self, backend: RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = backend.get_client().register_script(self.SCRIPTS)


class RedisPeekAtomicAction(
    RedisPeekAtomicActionCoreMixin, BaseAtomicAction[RedisStoreBackend]
):
    """Redis-based AtomicAction for GCRARateLimiter's peek operation."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", await self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class MemoryLimitAtomicAction(
    MemoryLimitAtomicActionCoreMixin[MemoryStoreBackend],
    BaseAtomicAction[MemoryStoreBackend],
):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int, float, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class MemoryPeekAtomicAction(
    MemoryPeekAtomicActionCoreMixin[MemoryStoreBackend],
    BaseAtomicAction[MemoryStoreBackend],
):
    """Memory-based AtomicAction for GCRARateLimiter's peek operation."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int, float, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class GCRARateLimiter(
    GCRARateLimiterCoreMixin[AsyncStoreP, AsyncAtomicActionP],
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[AsyncAtomicActionP]] = (
        RedisPeekAtomicAction,
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
        MemoryPeekAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, float, float]",
            await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
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
            await self._atomic_actions[ATOMIC_ACTION_TYPE_PEEK].do(
                [formatted_key], [emission_interval, capacity]
            ),
        )
        return RateLimitState(
            limit=capacity,
            remaining=remaining,
            reset_after=reset_after,
            retry_after=retry_after,
        )
