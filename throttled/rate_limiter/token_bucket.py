import math
from enum import Enum
from typing import List, Optional, Sequence, Tuple, Type

from redis.commands.core import Script

from ..constants import RateLimiterType, StoreType
from ..store import BaseAtomicAction, MemoryStoreBackend, RedisStoreBackend
from ..types import (
    AtomicActionTypeT,
    KeyT,
    RateLimiterTypeT,
    StoreDictValueT,
    StoreValueT,
)
from ..utils import now_sec
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class TokenBucketAtomicActionType(Enum):
    """Enumeration for types of AtomicActions used in TokenBucketRateLimiter."""

    LIMIT: AtomicActionTypeT = "limit"


class RedisLimitAtomicAction(BaseAtomicAction):
    """Redis-based implementation of AtomicAction for TokenBucketRateLimiter."""

    TYPE: AtomicActionTypeT = TokenBucketAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.REDIS.value

    SCRIPTS: str = """
    local rate = tonumber(ARGV[1])
    local capacity = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])
    local now = tonumber(ARGV[4])

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

    def __init__(self, backend: RedisStoreBackend):
        self._script: Script = backend.get_client().register_script(self.SCRIPTS)

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        return self._script(keys, args)


class MemoryLimitAtomicAction(BaseAtomicAction):
    """Memory-based implementation of AtomicAction for TokenBucketRateLimiter."""

    TYPE: AtomicActionTypeT = TokenBucketAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.MEMORY.value

    def __init__(self, backend: MemoryStoreBackend):
        self._backend: MemoryStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        with self._backend.lock:
            key: str = keys[0]
            rate: float = args[0]
            capacity: int = args[1]
            cost: int = args[2]
            now: int = args[3]

            bucket: StoreDictValueT = self._backend.hgetall(key)
            last_tokens: int = bucket.get("tokens", capacity)
            last_refreshed: int = bucket.get("last_refreshed", now)

            time_elapsed: int = max(0, now - last_refreshed)
            tokens: int = min(capacity, last_tokens + (math.floor(time_elapsed * rate)))

            limited: int = (1, 0)[tokens >= cost]
            if limited:
                return limited, tokens

            tokens -= cost
            self._backend.hset(key, mapping={"tokens": tokens, "last_refreshed": now})

            fill_time: float = capacity / rate
            self._backend.expire(key, math.ceil(2 * fill_time))

            return limited, tokens


class TokenBucketRateLimiter(BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using token bucket as algorithm."""

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.TOKEN_BUCKET.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[BaseAtomicAction]]:
        return [RedisLimitAtomicAction, MemoryLimitAtomicAction]

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [TokenBucketAtomicActionType.LIMIT.value]

    def _prepare(self, key: str) -> Tuple[str, float, int]:
        rate: float = self.quota.get_limit() / self.quota.get_period_sec()
        return self._prepare_key(key), rate, self.quota.burst

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, rate, capacity = self._prepare(key)
        limited, tokens = self._atomic_actions[
            TokenBucketAtomicActionType.LIMIT.value
        ].do([formatted_key], [rate, capacity, cost, now_sec()])
        reset_after: int = math.ceil((capacity - tokens) / rate)
        retry_after: int = 0
        if limited:
            retry_after = math.ceil(cost / rate)
        return RateLimitResult(
            limited=bool(limited),
            state=RateLimitState(
                limit=capacity,
                remaining=tokens,
                reset_after=reset_after,
                retry_after=retry_after,
            ),
        )

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
