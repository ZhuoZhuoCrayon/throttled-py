import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from .. import constants, store, types, utils
from . import BaseRateLimiter, BaseRateLimiterMixin, RateLimitResult, RateLimitState

if TYPE_CHECKING:
    from redis.commands.core import Script as SyncScript


class RedisLimitAtomActionSpec:
    """Identity and Lua script shared by sync / async Redis sliding-window actions."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT

    SCRIPTS: str = """
    local period = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])
    local now_ms = tonumber(ARGV[4])

    local exists = true
    local current = redis.call("GET", KEYS[1])
    if current == false then
        current = 0
        exists = false
    end

    local previous = redis.call("GET", KEYS[2])
    if previous == false then
        previous = 0
    end

    local period_ms = period * 1000
    local current_proportion = (now_ms % period_ms) / period_ms
    local previous_proportion = 1 - current_proportion
    previous = math.floor(previous_proportion * previous)

    local retry_after = 0
    local used = previous + current + cost
    local limited = used > limit and cost ~= 0
    if limited then
        if cost <= previous then
            retry_after = previous_proportion * period * cost / previous
        else
            retry_after = previous_proportion * period
        end
    else
        if exists then
            redis.call("INCRBY", KEYS[1], cost)
        else
            redis.call("SET", KEYS[1], cost, "EX", 3 * period)
        end
    end

    return {limited, used, tostring(retry_after)}
    """


class RedisLimitAtomicAction(RedisLimitAtomActionSpec, store.BaseRedisAtomicAction):
    """Redis-based implementation of AtomicAction for SlidingWindowRateLimiter."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
        super().__init__(backend)
        self._script: SyncScript = self._register_script(self.SCRIPTS)

    def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float]:
        limited, used, retry_after = cast(
            "tuple[int, int, str]", self._script(keys, args)
        )
        return limited, used, float(retry_after)


class MemoryLimitActionLogic:
    """Pure logic shared by sync / async memory limit actions."""

    @classmethod
    def _do(
        cls,
        backend: store.BaseMemoryStoreBackend,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int, float]:
        if args is None:
            raise ValueError("args is required")
        current_key: str = keys[0]
        previous_key: str = keys[1]
        period: int = int(args[0])
        limit: int = int(args[1])
        cost: int = int(args[2])

        current_raw: types.StoreValueT | None = backend.get(current_key)
        current: int
        if current_raw is None:
            current = 0
            # set expiration only for the first request in a new window.
            backend.set(current_key, cost, 3 * period)
        else:
            current = int(current_raw)

        # calculate the current window count proportion.
        period_ms: int = period * 1000
        current_proportion: float = (int(args[3]) % period_ms) / period_ms
        previous_proportion: float = 1 - current_proportion
        previous_raw: types.StoreValueT | None = backend.get(previous_key)
        previous: int = math.floor(
            previous_proportion * (int(previous_raw) if previous_raw is not None else 0)
        )

        retry_after: float = 0.0
        used: int = previous + current + cost
        limited: int = int(used > limit and cost != 0)
        if limited:
            if cost <= previous:
                retry_after = previous_proportion * period * cost / previous
            else:
                retry_after = previous_proportion * period
        else:
            # increment the current key by cost.
            backend.get_client()[current_key] = current + cost

        return limited, used, retry_after


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for SlidingWindowRateLimiter."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class SlidingWindowRateLimiterCoreMixin(BaseRateLimiterMixin):
    """Core mixin for SlidingWindowRateLimiter."""

    class Meta(BaseRateLimiterMixin.Meta):
        type: types.RateLimiterTypeT = constants.RateLimiterType.SLIDING_WINDOW.value

    @classmethod
    def _supported_atomic_action_types(cls) -> Sequence[types.AtomicActionTypeT]:
        return [constants.ATOMIC_ACTION_TYPE_LIMIT]

    def _prepare(self, key: str) -> tuple[str, str, int, int]:
        period: int = self.quota.get_period_sec()
        current_idx: int = utils.now_sec() // period
        current_key: str = self._prepare_key(f"{key}:period:{current_idx}")
        previous_key: str = self._prepare_key(f"{key}:period:{current_idx - 1}")
        return current_key, previous_key, period, self.quota.get_limit()


class SlidingWindowRateLimiter(SlidingWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using sliding window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        current_key, previous_key, period, limit = self._prepare(key)
        limited, used, retry_after = cast(
            "tuple[int, int, float]",
            self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
                [current_key, previous_key], [period, limit, cost, utils.now_ms()]
            ),
        )
        return RateLimitResult(
            limited=bool(limited),
            state_values=(limit, max(0, limit - used), period, retry_after),
        )

    def _peek(self, key: str) -> RateLimitState:
        current_key, previous_key, period, limit = self._prepare(key)
        period_ms: int = period * 1000
        current_proportion: float = (utils.now_ms() % period_ms) / period_ms
        previous: int = math.floor(
            (1 - current_proportion) * int(self._store.get(previous_key) or 0)
        )
        used: int = previous + int(self._store.get(current_key) or 0)

        return RateLimitState(
            limit=limit, remaining=max(0, limit - used), reset_after=period
        )
