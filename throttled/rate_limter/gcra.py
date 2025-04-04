import math
import time
from enum import Enum
from typing import List, Optional, Sequence, Tuple, Type

from redis.commands.core import Script

from ..constants import RateLimiterType, StoreType
from ..store import BaseAtomicAction, MemoryStoreBackend, RedisStoreBackend
from ..types import AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class GCRAAtomicActionType(Enum):
    """Enumeration for types of AtomicActions used in GCRARateLimiter."""

    PEEK: AtomicActionTypeT = "peek"
    LIMIT: AtomicActionTypeT = "limit"


class RedisLimitAtomicAction(BaseAtomicAction):
    """Redis-based implementation of AtomicAction for GCRARateLimiter's limit operation.
    Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
    """

    TYPE: AtomicActionTypeT = GCRAAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.REDIS.value

    SCRIPTS: str = """
    local emission_interval = tonumber(ARGV[1])
    local capacity = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])

    local jan_1_2025 = 1735660800
    local now = redis.call("TIME")
    now = (now[1] - jan_1_2025) + (now[2] / 1000000)

    local last_tat = redis.call("GET", KEYS[1])
    if not last_tat then
        last_tat = now
    else
        last_tat = tonumber(last_tat)
    end

    -- Calculate the fill time required for the current cost.
    local fill_time_for_cost = cost * emission_interval
    -- Calculate the fill time required for the full capacity.
    local fill_time_for_capacity = capacity * emission_interval
    -- Calculate the theoretical arrival time (TAT) for the current request.
    local tat = math.max(now, last_tat) + fill_time_for_cost
    -- Calculate the the time when the request would be allowed.
    local allow_at = tat - fill_time_for_capacity
    -- Calculate the time elapsed since the request would be allowed.
    local time_elapsed = now - allow_at


    local limited = 0
    local retry_after = 0
    local reset_after = tat - now
    local remaining = math.floor(time_elapsed / emission_interval)
    if remaining < 0 then
        limited = 1
        retry_after = time_elapsed * -1
        reset_after = math.max(0, last_tat - now)
        remaining = math.min(capacity, cost + remaining)
    else
        redis.call("SET", KEYS[1], tat, "EX", math.ceil(reset_after))
    end

    -- use tostring to avoid lost precision.
    return {limited, remaining, tostring(reset_after), tostring(retry_after)}
    """

    def __init__(self, backend: RedisStoreBackend):
        self._script: Script = backend.get_client().register_script(self.SCRIPTS)

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = self._script(keys, args)
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicAction(RedisLimitAtomicAction):
    """
    Redis-based implementation of AtomicAction for GCRARateLimiter's peek operation.
    """

    TYPE: AtomicActionTypeT = GCRAAtomicActionType.PEEK.value

    SCRIPTS: str = """
    local emission_interval = tonumber(ARGV[1])
    local capacity = tonumber(ARGV[2])

    local jan_1_2025 = 1735660800
    local now = redis.call("TIME")
    now = (now[1] - jan_1_2025) + (now[2] / 1000000)

    local tat = redis.call("GET", KEYS[1])
    if not tat then
        tat = now
    else
        tat= tonumber(tat)
    end

    -- Calculate the fill time required for the full capacity.
    local fill_time_for_capacity = capacity * emission_interval
    -- Calculate the the time when the request would be allowed.
    local allow_at = math.max(tat, now) - fill_time_for_capacity
    -- Calculate the time elapsed since the request would be allowed.
    local time_elapsed = now - allow_at

    local limited = 0
    local retry_after = 0
    local reset_after = math.max(0, tat - now)
    local remaining = math.floor(time_elapsed / emission_interval)
    if remaining < 1 then
        limited = 1
        remaining = 0
        retry_after = math.abs(time_elapsed)
    end

    -- use tostring to avoid lost precision.
    return {limited, remaining, tostring(reset_after), tostring(retry_after)}
    """


class MemoryLimitAtomicAction(BaseAtomicAction):
    """Memory-based implementation of AtomicAction for GCRARateLimiter's limit operation.
    Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
    """

    TYPE: AtomicActionTypeT = GCRAAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.MEMORY.value

    def __init__(self, backend: MemoryStoreBackend):
        self._backend: MemoryStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        with self._backend.lock:
            key: str = keys[0]
            emission_interval: float = args[0]
            capacity: int = args[1]
            cost: int = args[2]

            now: float = time.time()
            last_tat: float = self._backend.get(key) or now

            fill_time_for_cost: float = cost * emission_interval
            fill_time_for_capacity: float = capacity * emission_interval
            tat: float = max(now, last_tat) + fill_time_for_cost
            allow_at: float = tat - fill_time_for_capacity
            time_elapsed: float = now - allow_at

            remaining: int = math.floor(time_elapsed / emission_interval)
            if remaining < 0:
                limited: int = 1
                retry_after: float = -time_elapsed
                reset_after: float = max(0, last_tat - now)
                remaining: int = min(capacity, cost + remaining)
            else:
                limited: int = 0
                retry_after: float = 0
                reset_after: float = tat - now
                self._backend.set(key, tat, math.ceil(reset_after))

        return limited, remaining, reset_after, retry_after


class MemoryPeekAtomicAction(MemoryLimitAtomicAction):
    """
    Memory-based implementation of AtomicAction for GCRARateLimiter's peek operation.
    """

    TYPE: AtomicActionTypeT = GCRAAtomicActionType.PEEK.value

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        with self._backend.lock:
            key: str = keys[0]
            emission_interval: float = args[0]
            capacity: int = args[1]

            now: float = time.time()
            tat: float = self._backend.get(key) or now
            fill_time_for_capacity: float = capacity * emission_interval
            allow_at: float = max(now, tat) - fill_time_for_capacity
            time_elapsed: float = now - allow_at

            reset_after: float = max(0, tat - now)
            remaining: int = math.floor(time_elapsed / emission_interval)
            if remaining < 1:
                limited: int = 1
                remaining: int = 0
                retry_after: float = math.fabs(time_elapsed)
            else:
                limited: int = 0
                retry_after: float = 0
        return limited, remaining, reset_after, retry_after


class GCRARateLimiter(BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.GCRA.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[BaseAtomicAction]]:
        return [
            RedisPeekAtomicAction,
            RedisLimitAtomicAction,
            MemoryLimitAtomicAction,
            MemoryPeekAtomicAction,
        ]

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [GCRAAtomicActionType.LIMIT.value, GCRAAtomicActionType.PEEK.value]

    def _prepare(self, key: str) -> Tuple[str, float, int]:
        emission_interval: float = self.quota.get_period_sec() / self.quota.get_limit()
        return self._prepare_key(key), emission_interval, self.quota.burst

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = self._atomic_actions[
            GCRAAtomicActionType.LIMIT.value
        ].do([formatted_key], [emission_interval, capacity, cost])

        return RateLimitResult(
            limited=bool(limited),
            state=RateLimitState(
                limit=capacity,
                remaining=remaining,
                reset_after=reset_after,
                retry_after=retry_after,
            ),
        )

    def _peek(self, key: str) -> RateLimitState:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = self._atomic_actions[
            GCRAAtomicActionType.PEEK.value
        ].do([formatted_key], [emission_interval, capacity])
        return RateLimitState(
            limit=capacity,
            remaining=remaining,
            reset_after=reset_after,
            retry_after=retry_after,
        )
