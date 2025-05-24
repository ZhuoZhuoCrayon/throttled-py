import math
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Type, Union

from ..constants import ATOMIC_ACTION_TYPE_LIMIT, RateLimiterType, StoreType
from ..store import BaseAtomicAction
from ..types import AtomicActionP, AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from ..utils import now_ms, now_sec
from . import BaseRateLimiter, BaseRateLimiterMixin, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript
    from redis.commands.core import Script as SyncScript

    from ..store import MemoryStoreBackend, RedisStoreBackend

    Script = Union[AsyncScript, SyncScript]


class RedisLimitAtomicActionCoreMixin:
    """Core mixin for RedisLimitAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
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
            retry_after = (1 - current_proportion) * period
        end
    end

    return {limited, used, tostring(retry_after)}
    """

    def __init__(self, backend: "RedisStoreBackend"):
        super().__init__(backend)
        self._script: Script = backend.get_client().register_script(self.SCRIPTS)


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for SlidingWindowRateLimiter."""

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float]:
        limited, used, retry_after = self._script(keys, args)
        return limited, used, float(retry_after)


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
        args: Optional[Sequence[StoreValueT]],
    ) -> Tuple[int, int, float]:
        current_key: str = keys[0]
        previous_key: str = keys[1]
        period: int = args[0]
        limit: int = args[1]
        cost: int = args[2]

        current: Optional[int] = backend.get(current_key)
        if current is None:
            current = cost
            backend.set(current_key, cost, 3 * period)
        else:
            current += cost
            backend.get_client()[current_key] = current

        period_ms: int = period * 1000
        current_proportion: float = (args[3] % period_ms) / period_ms
        previous: int = math.floor(
            (1 - current_proportion) * (backend.get(previous_key) or 0)
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


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for SlidingWindowRateLimiter."""

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float]:
        with self._backend.lock:
            return self._do(self._backend, keys, args)


class SlidingWindowRateLimiterCoreMixin(BaseRateLimiterMixin):
    """Core mixin for SlidingWindowRateLimiter."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[AtomicActionP]] = []

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.SLIDING_WINDOW.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[AtomicActionP]]:
        return cls._DEFAULT_ATOMIC_ACTION_CLASSES

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [ATOMIC_ACTION_TYPE_LIMIT]

    def _prepare(self, key: str) -> Tuple[str, str, int, int]:
        period: int = self.quota.get_period_sec()
        current_idx: int = now_sec() // period
        current_key: str = self._prepare_key(f"{key}:period:{current_idx}")
        previous_key: str = self._prepare_key(f"{key}:period:{current_idx - 1}")
        return current_key, previous_key, period, self.quota.get_limit()


class SlidingWindowRateLimiter(SlidingWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using sliding window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[BaseAtomicAction]] = [
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    ]

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        current_key, previous_key, period, limit = self._prepare(key)
        limited, used, retry_after = self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
            [current_key, previous_key], [period, limit, cost, now_ms()]
        )
        return RateLimitResult(
            limited=bool(limited),
            state_values=(limit, max(0, limit - used), period, retry_after),
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
