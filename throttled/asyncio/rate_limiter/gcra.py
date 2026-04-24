from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ... import types
from ...constants import ATOMIC_ACTION_TYPE_LIMIT, ATOMIC_ACTION_TYPE_PEEK
from ...rate_limiter.gcra import (
    GCRARateLimiterCoreMixin,
    MemoryLimitAtomicActionCoreMixin,
    MemoryPeekAtomicActionCoreMixin,
    RedisLimitAtomicActionConstants,
    RedisPeekAtomicActionConstants,
)
from .. import store
from . import BaseRateLimiter, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


class RedisLimitAtomicActionCoreMixin(
    RedisLimitAtomicActionConstants,
    store.BaseAtomicActionMixin[store.RedisStoreBackend],
):
    """Core mixin for async RedisLimitAtomicAction."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = backend.get_client().register_script(self.SCRIPTS)


class RedisLimitAtomicAction(
    RedisLimitAtomicActionCoreMixin,
    store.BaseAtomicAction[store.RedisStoreBackend],
):
    """Redis-based implementation of AtomicAction for Async GCRARateLimiter."""

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", await self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicActionCoreMixin(
    RedisPeekAtomicActionConstants,
    store.BaseAtomicActionMixin[store.RedisStoreBackend],
):
    """Core mixin for async RedisPeekAtomicAction."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = backend.get_client().register_script(self.SCRIPTS)


class RedisPeekAtomicAction(
    RedisPeekAtomicActionCoreMixin,
    store.BaseAtomicAction[store.RedisStoreBackend],
):
    """Redis-based AtomicAction for GCRARateLimiter's peek operation."""

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", await self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class MemoryLimitAtomicAction(
    MemoryLimitAtomicActionCoreMixin[store.MemoryStoreBackend],
    store.BaseAtomicAction[store.MemoryStoreBackend],
):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class MemoryPeekAtomicAction(
    MemoryPeekAtomicActionCoreMixin[store.MemoryStoreBackend],
    store.BaseAtomicAction[store.MemoryStoreBackend],
):
    """Memory-based AtomicAction for GCRARateLimiter's peek operation."""

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class GCRARateLimiter(
    GCRARateLimiterCoreMixin[types.AsyncStoreP, types.AsyncAtomicActionP],
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[types.AsyncAtomicActionP]] = (
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
