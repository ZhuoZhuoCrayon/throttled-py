from collections.abc import Sequence
from typing import Generic, cast

from .. import store, types
from ..constants import ATOMIC_ACTION_TYPE_LIMIT, RateLimiterType, StoreType
from ..utils import now_sec
from . import BaseRateLimiter, BaseRateLimiterMixin, RateLimitResult, RateLimitState


class RedisLimitAtomicActionConstants:
    """Identity shared by sync / async Redis fixed-window atomic actions."""

    TYPE: types.AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = StoreType.REDIS.value


class RedisLimitAtomicActionCoreMixin(
    RedisLimitAtomicActionConstants,
    store.BaseAtomicActionMixin[store.RedisStoreBackend],
):
    """Core mixin for RedisLimitAtomicAction."""

    def __init__(self, backend: store.RedisStoreBackend) -> None:
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
        super().__init__(backend)


class RedisLimitAtomicAction(
    RedisLimitAtomicActionCoreMixin,
    store.BaseAtomicAction[store.RedisStoreBackend],
):
    """Redis-based implementation of AtomicAction for FixedWindowRateLimiter."""

    def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int]:
        if args is None:
            raise ValueError("args is required")
        period: int = int(args[0])
        limit: int = int(args[1])
        cost: int = int(args[2])
        client = self._backend.get_client()
        current: int = client.incrby(keys[0], cost)
        if current == cost:
            client.expire(keys[0], period)
        limited: int = int(current > limit and cost != 0)
        return limited, current


class MemoryLimitAtomicActionCoreMixin(
    store.BaseAtomicActionMixin[types.MemoryStoreBackendT],
    Generic[types.MemoryStoreBackendT],
):
    """Core mixin for MemoryLimitAtomicAction."""

    TYPE: types.AtomicActionTypeT = ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = StoreType.MEMORY.value

    @classmethod
    def _do(
        cls,
        backend: types.MemoryStoreBackendP,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int]:
        if args is None:
            raise ValueError("args is required")
        key: str = keys[0]
        period: int = int(args[0])
        limit: int = int(args[1])
        cost: int = int(args[2])
        current_raw: types.StoreValueT | None = backend.get(key)
        current: int
        if current_raw is None:
            current = cost
            backend.set(key, current, period)
        else:
            current = int(current_raw) + cost
            backend.get_client()[key] = current

        limited: int = int(current > limit and cost != 0)
        return limited, current


class MemoryLimitAtomicAction(
    MemoryLimitAtomicActionCoreMixin[store.MemoryStoreBackend],
    store.BaseAtomicAction[store.MemoryStoreBackend],
):
    """Memory-based implementation of AtomicAction for FixedWindowRateLimiter."""

    def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int, int]:
        with self._backend.lock:
            return self._do(self._backend, keys, args)


class FixedWindowRateLimiterCoreMixin(
    BaseRateLimiterMixin[types.StoreT, types.ActionT],
    Generic[types.StoreT, types.ActionT],
):
    """Core mixin for FixedWindowRateLimiter."""

    class Meta(BaseRateLimiterMixin.Meta):
        type: types.RateLimiterTypeT = RateLimiterType.FIXED_WINDOW.value

    @classmethod
    def _supported_atomic_action_types(cls) -> Sequence[types.AtomicActionTypeT]:
        return [ATOMIC_ACTION_TYPE_LIMIT]

    def _prepare(self, key: str) -> tuple[str, int, int, int]:
        now: int = now_sec()
        period: int = self.quota.get_period_sec()
        period_key: str = f"{key}:period:{now // period}"
        return self._prepare_key(period_key), period, self.quota.get_limit(), now


class FixedWindowRateLimiter(
    FixedWindowRateLimiterCoreMixin[types.SyncStoreP, types.SyncAtomicActionP],
    BaseRateLimiter,
):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[types.SyncAtomicActionP]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(key)
        limited, current = cast(
            "tuple[int, int]",
            self._atomic_actions[ATOMIC_ACTION_TYPE_LIMIT].do(
                [period_key], [period, limit, cost]
            ),
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
                reset_after if limited else 0,
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
