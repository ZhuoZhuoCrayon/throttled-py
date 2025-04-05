import math
from enum import Enum
from typing import List, Optional, Sequence, Tuple, Type

from redis.commands.core import Script

from ..constants import RateLimiterType, StoreType
from ..store import BaseAtomicAction, MemoryStoreBackend, RedisStoreBackend
from ..types import AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from ..utils import now_ms, now_sec
from . import BaseRateLimiter, RateLimitResult, RateLimitState


class SlidingWindowAtomicActionType(Enum):
    """Enumeration for types of AtomicActions used in SlidingWindowRateLimiter."""

    LIMIT: AtomicActionTypeT = "limit"


class RedisLimitAtomicAction(BaseAtomicAction):
    """Redis-based implementation of AtomicAction for SlidingWindowRateLimiter."""

    TYPE: AtomicActionTypeT = SlidingWindowAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.REDIS.value

    SCRIPTS: str = """
    local period = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])
    local now_ms = tonumber(ARGV[4])

    local current = redis.call("INCRBY", KEYS[1], cost)
    if current == cost then
        redis.call("EXPIRE", KEYS[1], 3 * period)
    end

    local previous = redis.call("GET", KEYS[2])
    if previous == false then
        previous = 0
    end

    local period_ms = period * 1000
    local current_proportion = (now_ms % period_ms) / period_ms
    previous = math.floor((1 - current_proportion) * previous)
    local used = previous + current

    local retry_after = 0
    local limited = used > limit
    if limited then
        if cost <= previous then
            retry_after = (1 - current_proportion) * period * cost / previous
        else
            retry_after = (1- current_proportion) * period
        end
    end

    return {limited, used, tostring(retry_after)}
    """

    def __init__(self, backend: RedisStoreBackend):
        self._script: Script = backend.get_client().register_script(self.SCRIPTS)

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float]:
        limited, used, retry_after = self._script(keys, args)
        return limited, used, float(retry_after)


class MemoryLimitAtomicAction(BaseAtomicAction):
    """Memory-based implementation of AtomicAction for SlidingWindowRateLimiter."""

    TYPE: AtomicActionTypeT = SlidingWindowAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.MEMORY.value

    def __init__(self, backend: MemoryStoreBackend):
        self._backend: MemoryStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float]:
        with self._backend.lock:
            current_key: str = keys[0]
            previous_key: str = keys[1]
            period: int = args[0]
            limit: int = args[1]
            cost: int = args[2]

            current: Optional[int] = self._backend.get(current_key)
            if current is None:
                current = cost
                self._backend.set(current_key, cost, 3 * period)
            else:
                current += cost
                self._backend.get_client()[current_key] = current

            period_ms: int = period * 1000
            current_proportion: float = (args[3] % period_ms) / period_ms
            previous: int = math.floor(
                (1 - current_proportion) * (self._backend.get(previous_key) or 0)
            )

            used: int = previous + current
            limited: int = (0, 1)[used > limit]
            if limited:
                if cost <= previous:
                    retry_after = (1 - current_proportion) * period * cost / previous
                else:
                    retry_after = (1 - current_proportion) * period
            else:
                retry_after = 0

            return limited, used, retry_after


class SlidingWindowRateLimiter(BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using sliding window as algorithm."""

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.SLIDING_WINDOW.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[BaseAtomicAction]]:
        return [RedisLimitAtomicAction, MemoryLimitAtomicAction]

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [SlidingWindowAtomicActionType.LIMIT.value]

    def _prepare(self, key: str) -> Tuple[str, str, int, int]:
        period: int = self.quota.get_period_sec()
        current_idx: int = now_sec() // period
        current_key: str = self._prepare_key(f"{key}:period:{current_idx}")
        previous_key: str = self._prepare_key(f"{key}:period:{current_idx - 1}")
        return current_key, previous_key, period, self.quota.get_limit()

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        current_key, previous_key, period, limit = self._prepare(key)
        limited, used, retry_after = self._atomic_actions[
            SlidingWindowAtomicActionType.LIMIT.value
        ].do([current_key, previous_key], [period, limit, cost, now_ms()])
        return RateLimitResult(
            limited=bool(limited),
            state=RateLimitState(
                limit=limit,
                remaining=max(0, limit - used),
                reset_after=period,
                retry_after=retry_after,
            ),
        )

    def _peek(self, key: str) -> RateLimitState:
        current_key, previous_key, period, limit = self._prepare(key)
        period_ms: int = period * 1000
        current_proportion: float = (now_ms() % period_ms) / period_ms
        previous: int = math.floor(
            (1 - current_proportion) * (self._store.get(previous_key) or 0)
        )
        used: int = previous + (self._store.get(current_key) or 0)

        return RateLimitState(
            limit=limit, remaining=max(0, limit - used), reset_after=period
        )
