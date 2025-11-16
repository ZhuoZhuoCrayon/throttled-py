import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..constants import ATOMIC_ACTION_TYPE_LIMIT, RateLimiterType, StoreType
from ..store import BaseAtomicAction
from ..types import (
    AtomicActionP,
    AtomicActionTypeT,
    KeyT,
    RateLimiterTypeT,
    StoreDictValueT,
    StoreValueT,
)
from ..utils import now_sec
from . import BaseRateLimiter, BaseRateLimiterMixin, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript
    from redis.commands.core import Script as SyncScript

    from ..store import MemoryStoreBackend, RedisStoreBackend

    Script = AsyncScript | SyncScript


class RedisLimitAtomicActionCoreMixin:
    """Core mixin for RedisLimitAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = StoreType.REDIS.value

    SCRIPTS: str = """
    local rate = tonumber(ARGV[1])
    local capacity = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])
    local now = tonumber(redis.call("TIME")[1])

    local last_tokens = capacity
    local last_refreshed = now
    local bucket = redis.call("HMGET", KEYS[1], "tokens", "last_refreshed")

    if bucket[1] ~= false then
        last_tokens = tonumber(bucket[1])
        last_refreshed = tonumber(bucket[2])
    end

    local time_elapsed = math.max(0, now - last_refreshed)
    local tokens = math.min(capacity, last_tokens + (math.floor(time_elapsed * rate)))

    local limited = cost > tokens
    if limited then
        return {limited, tokens}
    end

    tokens = tokens - cost
    local fill_time = capacity / rate
    redis.call("HSET", KEYS[1], "tokens", tokens, "last_refreshed", now)
    redis.call("EXPIRE", KEYS[1], math.floor(2 * fill_time))

    return {limited, tokens}
    """

    def __init__(self, backend: "RedisStoreBackend"):
        super().__init__(backend)
        self._script: Script = backend.get_client().register_script(self.SCRIPTS)


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for TokenBucketRateLimiter."""

    def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int]:
        return self._script(keys, args)


class MemoryLimitAtomicActionCoreMixin:
    """Core mixin for MemoryLimitAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = StoreType.MEMORY.value

    def __init__(self, backend: "MemoryStoreBackend"):
        super().__init__(backend)
        self._backend: MemoryStoreBackend = backend

    @classmethod
    def _do(
        cls,
        backend: "MemoryStoreBackend",
        keys: Sequence[KeyT],
        args: Sequence[StoreValueT] | None,
    ) -> tuple[int, int]:
        key: str = keys[0]
        now: int = now_sec()
        rate, capacity, cost = args
        bucket: StoreDictValueT = backend.hgetall(key)
        last_tokens: int = bucket.get("tokens", capacity)
        last_refreshed: int = bucket.get("last_refreshed", now)

        time_elapsed: int = max(0, now - last_refreshed)
        tokens: int = min(capacity, last_tokens + (math.floor(time_elapsed * rate)))

        limited: int = (1, 0)[tokens >= cost]
        if limited:
            return limited, tokens

        tokens -= cost
        backend.hset(key, mapping={"tokens": tokens, "last_refreshed": now})

        fill_time: float = capacity / rate
        backend.expire(key, math.ceil(2 * fill_time))

        return limited, tokens


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for TokenBucketRateLimiter."""

    def do(
        self, keys: Sequence[KeyT], args: Sequence[StoreValueT] | None
    ) -> tuple[int, int]:
        with self._backend.lock:
            return self._do(self._backend, keys, args)


class TokenBucketRateLimiterCoreMixin(BaseRateLimiterMixin):
    """Core mixin for TokenBucketRateLimiter."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: list[type[AtomicActionP]] = []

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.TOKEN_BUCKET.value

    @classmethod
    def _default_atomic_action_classes(cls) -> list[type[AtomicActionP]]:
        return cls._DEFAULT_ATOMIC_ACTION_CLASSES

    @classmethod
    def _supported_atomic_action_types(cls) -> list[AtomicActionTypeT]:
        return [ATOMIC_ACTION_TYPE_LIMIT]

    def _prepare(self, key: str) -> tuple[str, float, int]:
        return self._prepare_key(key), self.quota.fill_rate, self.quota.burst

    def _refill_sec(self, upper: int, remaining: int) -> int:
        """Calculate the time in seconds until the bucket reaches the upper limit."""
        if remaining >= upper:
            return 0
        return math.ceil((upper - remaining) / self.quota.fill_rate)

    def _to_result(
        self, limited: int, cost: int, tokens: int, capacity: int
    ) -> RateLimitResult:
        """Convert the limiting result to a RateLimitResult."""
        reset_after: int = self._refill_sec(capacity, tokens)
        # When the tokens are filled to the cost, it can be retried.
        retry_after: int = self._refill_sec(cost, tokens) if limited else 0
        return RateLimitResult(
            limited=bool(limited),
            state_values=(capacity, tokens, reset_after, retry_after),
        )


class TokenBucketRateLimiter(TokenBucketRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using token bucket as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: list[type[AtomicActionP]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, rate, capacity = self._prepare(key)
        limited, tokens = self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
            [formatted_key], [rate, capacity, cost]
        )
        return self._to_result(limited, cost, tokens, capacity)

    def _peek(self, key: str) -> RateLimitState:
        now: int = now_sec()
        formatted_key, rate, capacity = self._prepare(key)

        bucket: StoreDictValueT = self._store.hgetall(formatted_key)
        last_tokens: int = bucket.get("tokens", capacity)
        last_refreshed: int = bucket.get("last_refreshed", now)

        time_elapsed: int = max(0, now - last_refreshed)
        tokens: int = min(capacity, last_tokens + (math.floor(time_elapsed * rate)))
        reset_after: int = math.ceil((capacity - tokens) / rate)

        return RateLimitState(limit=capacity, remaining=tokens, reset_after=reset_after)
