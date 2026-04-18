import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.sliding_window import (
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionConstants,
    SlidingWindowRateLimiterCoreMixin,
)
from ...store.base import BaseAtomicActionMixin
from ...types import (
    AsyncAtomicActionP,
    AsyncStoreP,
    KeyT,
    StoreValueT,
)
from ...utils import now_ms
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
    """Redis-based implementation of AtomicAction for Async SlidingWindowRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int, float]:
        limited, used, retry_after = cast(
            "tuple[int, int, str]", await self._script(keys, args)
        )
        return limited, used, float(retry_after)


class MemoryLimitAtomicAction(
    MemoryLimitAtomicActionCoreMixin[MemoryStoreBackend],
    BaseAtomicAction[MemoryStoreBackend],
):
    """Memory-based implementation of AtomicAction for Async SlidingWindowRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int, float]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class SlidingWindowRateLimiter(
    SlidingWindowRateLimiterCoreMixin[AsyncStoreP, AsyncAtomicActionP],
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using sliding window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[AsyncAtomicActionP]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        current_key, previous_key, period, limit = self._prepare(key)
        limited, used, retry_after = cast(
            "tuple[int, int, float]",
            await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
                [current_key, previous_key], [period, limit, cost, now_ms()]
            ),
        )
        return RateLimitResult(
            limited=bool(limited),
            state_values=(limit, max(0, limit - used), period, retry_after),
        )

    async def _peek(self, key: str) -> RateLimitState:
        current_key, previous_key, period, limit = self._prepare(key)
        period_ms: int = period * 1000
        current_proportion: float = (now_ms() % period_ms) / period_ms

        previous: int = math.floor(
            (1 - current_proportion) * int(await self._store.get(previous_key) or 0)
        )
        used: int = previous + int(await self._store.get(current_key) or 0)

        return RateLimitState(
            limit=limit, remaining=max(0, limit - used), reset_after=period
        )
