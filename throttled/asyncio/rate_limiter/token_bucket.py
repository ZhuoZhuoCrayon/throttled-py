import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ...constants import ATOMIC_ACTION_TYPE_LIMIT
from ...rate_limiter.token_bucket import (
    MemoryLimitAtomicActionCoreMixin,
    RedisLimitAtomicActionConstants,
    TokenBucketRateLimiterCoreMixin,
)
from ...store.base import BaseAtomicActionMixin
from ...types import (
    AsyncAtomicActionP,
    AsyncStoreP,
    KeyT,
    StoreDictValueT,
    StoreValueT,
)
from ...utils import now_sec
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
    """Redis-based implementation of AtomicAction for Async TokenBucketRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int]:
        limited, tokens = cast("tuple[int, int]", await self._script(keys, args))
        return limited, tokens


class MemoryLimitAtomicAction(
    MemoryLimitAtomicActionCoreMixin[MemoryStoreBackend],
    BaseAtomicAction[MemoryStoreBackend],
):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    async def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int]:
        async with self._backend.lock:
            return self._do(self._backend, keys, args)


class TokenBucketRateLimiter(
    TokenBucketRateLimiterCoreMixin[AsyncStoreP, AsyncAtomicActionP],
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using leaking bucket as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[AsyncAtomicActionP]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, rate, capacity = self._prepare(key)
        limited, tokens = cast(
            "tuple[int, int]",
            await self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
                [formatted_key], [rate, capacity, cost]
            ),
        )
        return self._to_result(limited, cost, tokens, capacity)

    async def _peek(self, key: str) -> RateLimitState:
        now: int = now_sec()
        formatted_key, rate, capacity = self._prepare(key)

        bucket: StoreDictValueT = await self._store.hgetall(formatted_key)
        last_tokens: int = int(bucket.get("tokens", capacity))
        last_refreshed: int = int(bucket.get("last_refreshed", now))

        time_elapsed: int = max(0, now - last_refreshed)
        tokens: int = min(capacity, last_tokens + (math.floor(time_elapsed * rate)))
        reset_after: int = math.ceil((capacity - tokens) / rate)

        return RateLimitState(limit=capacity, remaining=tokens, reset_after=reset_after)
