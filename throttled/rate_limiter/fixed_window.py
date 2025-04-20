from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Type

from ..constants import RateLimiterType, StoreType
from ..store import BaseAtomicAction
from ..types import AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from ..utils import now_sec
from . import BaseRateLimiter, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from ..store import MemoryStoreBackend, RedisStoreBackend


class FixedWindowAtomicActionType(Enum):
    """Enumeration for types of AtomicActions used in FixedWindowRateLimiter."""

    LIMIT: AtomicActionTypeT = "limit"


class RedisLimitAtomicAction(BaseAtomicAction):
    """Redis-based implementation of AtomicAction for FixedWindowRateLimiter."""

    TYPE: AtomicActionTypeT = FixedWindowAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.REDIS.value

    SCRIPTS: str = """
    local period = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])
    local current = redis.call("INCRBY", KEYS[1], cost)

    if current == cost then
        redis.call("EXPIRE", KEYS[1], period)
    end

    return {current > limit and 1 or 0, current}
    """

    def __init__(self, backend: "RedisStoreBackend"):
        # In single command scenario, lua has no performance advantage, and even causes
        # a decrease in performance due to the increase in transmission content.
        # Benchmarks(Python 3.8, Darwin 23.6.0, Arm)
        # >> Redis baseline
        # command    -> set key value
        # serial     -> 🕒Latency: 0.0609 ms/op, 🚀Throughput: 16271 req/s
        # concurrent -> 🕒Latency: 0.4515 ms/op, 💤Throughput: 12100 req/s
        # >> Lua
        # serial     -> 🕒Latency: 0.0805 ms/op, 🚀Throughput: 12319 req/s
        # concurrent -> 🕒Latency: 0.6959 ms/op, 💤Throughput: 10301 req/s
        # >> 👍 Single Command
        # serial     -> 🕒Latency: 0.0659 ms/op, 🚀Throughput: 15040 req/s
        # concurrent -> 🕒Latency: 0.9084 ms/op, 💤Throughput: 11539 req/s
        # self._script: Script = backend.get_client().register_script(self.SCRIPTS)
        self._backend: RedisStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        period, limit, cost = args[0], args[1], args[2]
        current: int = self._backend.get_client().incrby(keys[0], cost)
        if current == cost:
            self._backend.get_client().expire(keys[0], period)
        return [0, 1][current > limit], current


class MemoryLimitAtomicAction(BaseAtomicAction):
    """Memory-based implementation of AtomicAction for FixedWindowRateLimiter."""

    TYPE: AtomicActionTypeT = FixedWindowAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.MEMORY.value

    def __init__(self, backend: "MemoryStoreBackend"):
        self._backend: MemoryStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        key: str = keys[0]
        period: int = args[0]
        limit: int = args[1]
        cost: int = args[2]
        with self._backend.lock:
            current: Optional[int] = self._backend.get(key)
            if current is None:
                current = cost
                self._backend.set(key, current, period)
            else:
                current += cost
                self._backend.get_client()[key] = current

        return (0, 1)[current > limit], current


class FixedWindowRateLimiter(BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.FIXED_WINDOW.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[BaseAtomicAction]]:
        return [RedisLimitAtomicAction, MemoryLimitAtomicAction]

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [FixedWindowAtomicActionType.LIMIT.value]

    def _prepare(self, key: str) -> Tuple[str, int, int, int]:
        now: int = now_sec()
        period: int = self.quota.get_period_sec()
        period_key: str = f"{key}:period:{now // period}"
        return self._prepare_key(period_key), period, self.quota.get_limit(), now

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(key)
        limited, current = self._atomic_actions[
            FixedWindowAtomicActionType.LIMIT.value
        ].do([period_key], [period, limit, cost])

        # |-- now % period --|-- reset_after --|----- next period -----|
        # |--------------- period -------------|
        reset_after: float = period - (now % period)
        return RateLimitResult(
            limited=bool(limited),
            state=RateLimitState(
                limit=limit,
                remaining=max(0, limit - current),
                reset_after=reset_after,
                retry_after=(0, reset_after)[limited],
            ),
        )

    def _peek(self, key: str) -> RateLimitState:
        period_key, period, limit, now = self._prepare(key)
        current: int = int(self._store.get(period_key) or 0)
        return RateLimitState(
            limit=limit,
            remaining=max(0, limit - current),
            reset_after=period - (now % period),
        )
