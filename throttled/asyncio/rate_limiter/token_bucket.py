import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from ... import constants, types, utils
from ...rate_limiter.token_bucket import (
    MemoryLimitActionLogic,
    RedisLimitAtomicActionSpec,
    TokenBucketRateLimiterCoreMixin,
)
from .. import store
from . import BaseRateLimiter, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


class RedisLimitAtomicAction(RedisLimitAtomicActionSpec, store.BaseRedisAtomicAction):
    """Redis-based implementation of AtomicAction for Async TokenBucketRateLimiter."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: AsyncScript = self._register_script(self.SCRIPTS)

    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int]:
        limited, tokens = cast("tuple[int, int]", await self._script(keys, args))
        return limited, tokens


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for Async LeakingBucketRateLimiter."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class TokenBucketRateLimiter(TokenBucketRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using leaking bucket as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    async def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, rate, capacity = self._prepare(key)
        limited, tokens = cast(
            "tuple[int, int]",
            await self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
                [formatted_key], [rate, capacity, cost]
            ),
        )
        return self._to_result(limited, cost, tokens, capacity)

    async def _peek(self, key: str) -> RateLimitState:
        now: int = utils.now_sec()
        formatted_key, rate, capacity = self._prepare(key)

        bucket: types.StoreDictValueT = await self._store.hgetall(formatted_key)
        last_tokens: int = int(bucket.get("tokens", capacity))
        last_refreshed: int = int(bucket.get("last_refreshed", now))

        time_elapsed: int = max(0, now - last_refreshed)
        tokens: int = min(capacity, last_tokens + (math.floor(time_elapsed * rate)))
        reset_after: int = math.ceil((capacity - tokens) / rate)

        return RateLimitState(limit=capacity, remaining=tokens, reset_after=reset_after)
