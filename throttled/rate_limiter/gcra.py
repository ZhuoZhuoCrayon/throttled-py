import math
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple, Type, Union

from ..constants import (
    ATOMIC_ACTION_TYPE_LIMIT,
    ATOMIC_ACTION_TYPE_PEEK,
    RateLimiterType,
    StoreType,
)
from ..store import BaseAtomicAction
from ..types import AtomicActionP, AtomicActionTypeT, KeyT, RateLimiterTypeT, StoreValueT
from ..utils import now_mono_f
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

    local fill_time_for_cost = cost * emission_interval
    local fill_time_for_capacity = capacity * emission_interval
    local tat = math.max(now, last_tat) + fill_time_for_cost
    local allow_at = tat - fill_time_for_capacity
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
        if reset_after > 0 then
            redis.call("SET", KEYS[1], tat, "EX", math.ceil(reset_after))
        end
    end

    return {limited, remaining, tostring(reset_after), tostring(retry_after)}
    """

    def __init__(self, backend: "RedisStoreBackend"):
        super().__init__(backend)
        self._script: Script = backend.get_client().register_script(self.SCRIPTS)


class RedisLimitAtomicAction(RedisLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Redis-based implementation of AtomicAction for GCRARateLimiter's limit operation.
    Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
    """

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = self._script(keys, args)
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicActionCoreMixin:
    """Core mixin for RedisPeekAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_PEEK

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

    local fill_time_for_capacity = capacity * emission_interval
    local allow_at = math.max(tat, now) - fill_time_for_capacity
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

    return {limited, remaining, tostring(reset_after), tostring(retry_after)}
    """


class RedisPeekAtomicAction(RedisPeekAtomicActionCoreMixin, RedisLimitAtomicAction):
    """
    Redis-based implementation of AtomicAction for GCRARateLimiter's peek operation.
    """


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
    ) -> Tuple[int, int, float, float]:
        key: str = keys[0]
        emission_interval, capacity, cost = args
        now: float = now_mono_f()
        last_tat: float = backend.get(key) or now

        fill_time_for_cost: float = cost * emission_interval
        fill_time_for_capacity: float = capacity * emission_interval
        tat: float = max(now, last_tat) + fill_time_for_cost
        allow_at: float = tat - fill_time_for_capacity
        time_elapsed: float = now - allow_at

        remaining: int = math.floor(time_elapsed / emission_interval)
        if remaining < 0:
            limited: int = 1
            retry_after: float = -time_elapsed
            reset_after: float = max(0.0, last_tat - now)
            remaining: int = min(capacity, cost + remaining)
        else:
            limited: int = 0
            retry_after: float = 0
            reset_after: float = tat - now
            if reset_after > 0:
                # When cost equals 0, there's no need to update TAT.
                backend.set(key, tat, math.ceil(reset_after))

        return limited, remaining, reset_after, retry_after


class MemoryLimitAtomicAction(MemoryLimitAtomicActionCoreMixin, BaseAtomicAction):
    """Memory-based implementation of AtomicAction for GCRARateLimiter's limit operation.
    Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
    """

    def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Tuple[int, int, float, float]:
        with self._backend.lock:
            return self._do(self._backend, keys, args)


class MemoryPeekAtomicActionCoreMixin:
    """Core mixin for MemoryPeekAtomicAction."""

    TYPE: AtomicActionTypeT = ATOMIC_ACTION_TYPE_PEEK

    @classmethod
    def _do(
        cls,
        backend: "MemoryStoreBackend",
        keys: Sequence[KeyT],
        args: Optional[Sequence[StoreValueT]],
    ) -> Tuple[int, int, float, float]:
        key: str = keys[0]
        emission_interval: float = args[0]
        capacity: int = args[1]

        now: float = now_mono_f()
        tat: float = backend.get(key) or now
        fill_time_for_capacity: float = capacity * emission_interval
        allow_at: float = max(now, tat) - fill_time_for_capacity
        time_elapsed: float = now - allow_at

        reset_after: float = max(0.0, tat - now)
        remaining: int = math.floor(time_elapsed / emission_interval)
        if remaining < 1:
            limited: int = 1
            remaining: int = 0
            retry_after: float = math.fabs(time_elapsed)
        else:
            limited: int = 0
            retry_after: float = 0
        return limited, remaining, reset_after, retry_after


class MemoryPeekAtomicAction(MemoryPeekAtomicActionCoreMixin, MemoryLimitAtomicAction):
    """
    Memory-based implementation of AtomicAction for GCRARateLimiter's peek operation.
    """


class GCRARateLimiterCoreMixin(BaseRateLimiterMixin):
    """Core mixin for GCRARateLimiter."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[AtomicActionP]] = []

    class Meta:
        type: RateLimiterTypeT = RateLimiterType.GCRA.value

    @classmethod
    def _default_atomic_action_classes(cls) -> List[Type[AtomicActionP]]:
        return cls._DEFAULT_ATOMIC_ACTION_CLASSES

    @classmethod
    def _supported_atomic_action_types(cls) -> List[AtomicActionTypeT]:
        return [ATOMIC_ACTION_TYPE_LIMIT, ATOMIC_ACTION_TYPE_PEEK]

    def _prepare(self, key: str) -> Tuple[str, float, int]:
        return self._prepare_key(key), self.quota.emission_interval, self.quota.burst


class GCRARateLimiter(GCRARateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: List[Type[AtomicActionP]] = [
        RedisPeekAtomicAction,
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
        MemoryPeekAtomicAction,
    ]

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = self._atomic_actions[
            ATOMIC_ACTION_TYPE_LIMIT
        ].do([formatted_key], [emission_interval, capacity, cost])

        return RateLimitResult(
            limited=bool(limited),
            state_values=(capacity, remaining, reset_after, retry_after),
        )

    def _peek(self, key: str) -> RateLimitState:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = self._atomic_actions[
            ATOMIC_ACTION_TYPE_PEEK
        ].do([formatted_key], [emission_interval, capacity])
        return RateLimitState(
            limit=capacity,
            remaining=remaining,
            reset_after=reset_after,
            retry_after=retry_after,
        )
