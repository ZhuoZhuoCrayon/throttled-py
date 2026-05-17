import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from .. import constants, store, types, utils
from . import BaseRateLimiter, BaseRateLimiterMixin, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import Script as SyncScript


class RedisLimitAtomicActionSpec:
    """Identity and Lua script shared by sync / async Redis GCRA limit actions."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT

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


class RedisPeekAtomicActionSpec:
    """Identity and Lua script shared by sync / async Redis GCRA peek actions."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_PEEK

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


class RedisLimitAtomicAction(RedisLimitAtomicActionSpec, store.BaseRedisAtomicAction):
    """Redis-based implementation of AtomicAction for GCRARateLimiter's limit operation.

    Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
    """

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: SyncScript = self._register_script(self.SCRIPTS)

    def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class RedisPeekAtomicAction(RedisPeekAtomicActionSpec, store.BaseRedisAtomicAction):
    """Redis-based AtomicAction for GCRARateLimiter's peek operation."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: SyncScript = self._register_script(self.SCRIPTS)

    def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, str, str]", self._script(keys, args)
        )
        return limited, remaining, float(reset_after), float(retry_after)


class MemoryLimitActionLogic:
    """Pure logic shared by sync / async memory limit actions."""

    @classmethod
    def _do(
        cls,
        backend: store.BaseMemoryStoreBackend,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        if args is None:
            raise ValueError("args is required")
        key: str = keys[0]
        emission_interval: float = float(args[0])
        capacity: int = int(args[1])
        cost: int = int(args[2])
        now: float = utils.now_mono_f()
        last_tat: float = float(backend.get(key) or now)

        fill_time_for_cost: float = cost * emission_interval
        fill_time_for_capacity: float = capacity * emission_interval
        tat: float = max(now, last_tat) + fill_time_for_cost
        allow_at: float = tat - fill_time_for_capacity
        time_elapsed: float = now - allow_at

        remaining: int = math.floor(time_elapsed / emission_interval)
        limited: int = 0
        retry_after: float = 0.0
        reset_after: float = tat - now
        if remaining < 0:
            limited = 1
            retry_after = abs(time_elapsed)
            reset_after = max(0.0, last_tat - now)
            remaining = min(capacity, cost + remaining)
        elif reset_after > 0:
            # When cost equals 0, there's no need to update TAT.
            backend.set(key, tat, math.ceil(reset_after))

        return limited, remaining, reset_after, retry_after


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for GCRARateLimiter's limit operation.

    Inspire by [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting).
    """

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class MemoryPeekActionLogic:
    """Pure logic shared by sync / async memory peek actions."""

    @classmethod
    def _do(
        cls,
        backend: store.BaseMemoryStoreBackend,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float, float]:
        if args is None:
            raise ValueError("args is required")
        key: str = keys[0]
        emission_interval: float = float(args[0])
        capacity: int = int(args[1])

        now: float = utils.now_mono_f()
        tat: float = float(backend.get(key) or now)
        fill_time_for_capacity: float = capacity * emission_interval
        allow_at: float = max(now, tat) - fill_time_for_capacity
        time_elapsed: float = now - allow_at

        reset_after: float = max(0.0, tat - now)
        remaining: int = math.floor(time_elapsed / emission_interval)
        limited: int = 0
        retry_after: float = 0.0
        if remaining < 1:
            limited = 1
            remaining = 0
            retry_after = abs(time_elapsed)
        return limited, remaining, reset_after, retry_after


class MemoryPeekAtomicAction(MemoryPeekActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based AtomicAction for GCRARateLimiter's peek operation."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_PEEK


class GCRARateLimiterCoreMixin(BaseRateLimiterMixin):
    """Core mixin for GCRARateLimiter."""

    class Meta(BaseRateLimiterMixin.Meta):
        type: types.RateLimiterTypeT = constants.RateLimiterType.GCRA.value

    @classmethod
    def _supported_atomic_action_types(cls) -> Sequence[types.AtomicActionTypeT]:
        return [constants.ATOMIC_ACTION_TYPE_LIMIT, constants.ATOMIC_ACTION_TYPE_PEEK]

    def _prepare(self, key: str) -> tuple[str, float, int]:
        return self._prepare_key(key), self.quota.emission_interval, self.quota.burst


class GCRARateLimiter(GCRARateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using GCRA as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisPeekAtomicAction,
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
        MemoryPeekAtomicAction,
    )

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        formatted_key, emission_interval, capacity = self._prepare(key)
        limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, float, float]",
            self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
                [formatted_key], [emission_interval, capacity, cost]
            ),
        )

        return RateLimitResult(
            limited=bool(limited),
            state_values=(capacity, remaining, reset_after, retry_after),
        )

    def _peek(self, key: str) -> RateLimitState:
        formatted_key, emission_interval, capacity = self._prepare(key)
        _limited, remaining, reset_after, retry_after = cast(
            "tuple[int, int, float, float]",
            self._atomic_actions[constants.ATOMIC_ACTION_TYPE_PEEK].do(
                [formatted_key], [emission_interval, capacity]
            ),
        )
        return RateLimitState(
            limit=capacity,
            remaining=remaining,
            reset_after=reset_after,
            retry_after=retry_after,
        )
