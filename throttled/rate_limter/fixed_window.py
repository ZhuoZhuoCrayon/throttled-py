from enum import Enum
from typing import List, Optional, Sequence, Tuple, Type

from redis.commands.core import Script

from ..constants import RateLimiterType, StoreType
from ..store import BaseAtomicAction, MemoryStoreBackend, RedisStoreBackend
from ..types import AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from ..utils import now_sec
from . import BaseRateLimiter, RateLimitResult, RateLimitState


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

    def __init__(self, backend: RedisStoreBackend):
        self._script: Script = backend.client.register_script(self.SCRIPTS)

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        return self._script(keys, args)


class MemoryLimitAtomicAction(BaseAtomicAction):
    """Memory-based implementation of AtomicAction for FixedWindowRateLimiter."""

    TYPE: AtomicActionTypeT = FixedWindowAtomicActionType.LIMIT.value
    STORE_TYPE: str = StoreType.MEMORY.value

    def __init__(self, backend: MemoryStoreBackend):
        self._backend: MemoryStoreBackend = backend

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int]:
        with self._backend.lock:
            key: str = keys[0]
            period: int = args[0]
            limit: int = args[1]
            cost: int = args[2]

            current: Optional[int] = self._backend.get(key)
            if current is None:
                current = cost
                self._backend.set(key, current, period)
            else:
                current += cost
                self._backend.store[key] = current

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

    def _prepare(self, key: str) -> Tuple[str, int, int]:
        period: int = self.quota.get_period_sec()
        period_key: str = f"{key}:period:{now_sec() // period}"
        return period_key, period, self.quota.get_limit()

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit = self._prepare(key)
        limited, current = self._atomic_actions[
            FixedWindowAtomicActionType.LIMIT.value
        ].do([period_key], [period, limit, cost])
        return RateLimitResult(
            limited=bool(limited),
            state=RateLimitState(
                limit=limit, remaining=max(0, limit - current), reset_after=period
            ),
        )

    def _peek(self, key: str) -> RateLimitState:
        period_key, period, limit = self._prepare(key)
        current: int = int(self._store.get(period_key) or 0)
        return RateLimitState(
            limit=limit, remaining=max(0, limit - current), reset_after=period
        )
