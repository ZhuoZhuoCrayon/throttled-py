from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Type

from ..constants import ATOMIC_ACTION_TYPE_LIMIT, RateLimiterType, StoreType
from ..store import BaseAtomicAction
from ..types import AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from ..utils import now_sec
from . import BaseRateLimiter, Quota, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from ..store import MemoryStoreBackend, RedisStoreBackend


class RedisLimitAtomicActionCoreMixin:
    """Core mixin for RedisLimitAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
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


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for FixedWindowRateLimiter."""

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
        period, limit, cost = args
        current: int = self._backend.get_client().incrby(keys[0], cost)
        if current == cost:
            self._backend.get_client().expire(keys[0], period)
        return [0, 1][current > limit], current


class MemoryLimitAtomicActionCoreMixin:
    """Core mixin for MemoryLimitAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = StoreType.MEMORY.value

    @classmethod
    def _do(
        cls,
        backend: "MemoryStoreBackend",
        keys: Sequence[KeyT],
        args: Optional[Sequence[StoreValueT]],
    ) -> Tuple[int, int]:
        key: str = keys[0]
        period, limit, cost = args
        current: Optional[int] = backend.get(key)
        if current is None:
            current = cost
            backend.set(key, current, period)
        else:
            current += cost
            backend.get_client()[key] = current

        return (0, 1)[current > limit], current


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for FixedWindowRateLimiter."""

    def __init__(self, backend: "MemoryStoreBackend"):
        self._backend: MemoryStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        with self._backend.lock:
            return self._do(self._backend, keys, args)


class FixedWindowRateLimiterCoreMixin:
    """Core mixin for FixedWindowRateLimiter."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[BaseAtomicAction]] = []

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.FIXED_WINDOW.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[BaseAtomicAction]]:
        return cls._DEFAULT_ATOMIC_ACTION_CLASSES

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [ATOMIC_ACTION_TYPE_LIMIT]

    @classmethod
    def _prepare(cls, quota: Quota, key: str) -> Tuple[str, int, int, int]:
        now: int = now_sec()
        period: int = quota.get_period_sec()
        period_key: str = f"{key}:period:{now // period}"
        return period_key, period, quota.get_limit(), now


class FixedWindowRateLimiter(FixedWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[BaseAtomicAction]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(
            self.quota, self._prepare_key(key)
        )
        limited, current = self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
            [period_key], [period, limit, cost]
        )

        # |-- now % period --|-- reset_after --|----- next period -----|
        # |--------------- period -------------|
        reset_after: float = period - (now % period)
        return RateLimitResult(
            limited=bool(limited),
            state_values=(
                limit,
                max(0, limit - current),
                reset_after,
                (0, reset_after)[limited],
            ),
        )

    def _peek(self, key: str) -> RateLimitState:
        period_key, period, limit, now = self._prepare(
            self.quota, self._prepare_key(key)
        )
        current: int = int(self._store.get(period_key) or 0)
        return RateLimitState(
            limit=limit,
            remaining=max(0, limit - current),
            reset_after=period - (now % period),
        )
