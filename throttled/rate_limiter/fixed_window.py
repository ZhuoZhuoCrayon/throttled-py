from collections.abc import Sequence
from typing import cast

from .. import constants, store, types, utils
from . import BaseRateLimiter, BaseRateLimiterMixin, RateLimitResult, RateLimitState


class RedisLimitAtomicActionSpec:
    """Identity shared by sync / async Redis fixed-window atomic actions."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class RedisLimitAtomicAction(RedisLimitAtomicActionSpec, store.BaseRedisAtomicAction):
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


class MemoryLimitActionLogic:
    """Pure logic shared by sync / async memory limit actions."""

    @classmethod
    def _do(
        cls,
        backend: store.BaseMemoryStoreBackend,
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


class MemoryLimitAtomicAction(MemoryLimitActionLogic, store.BaseMemoryAtomicAction):
    """Memory-based implementation of AtomicAction for FixedWindowRateLimiter."""

    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT


class FixedWindowRateLimiterCoreMixin(BaseRateLimiterMixin):
    """Core mixin for FixedWindowRateLimiter."""

    class Meta(BaseRateLimiterMixin.Meta):
        type: types.RateLimiterTypeT = constants.RateLimiterType.FIXED_WINDOW.value

    @classmethod
    def _supported_atomic_action_types(cls) -> Sequence[types.AtomicActionTypeT]:
        return [constants.ATOMIC_ACTION_TYPE_LIMIT]

    def _prepare(self, key: str) -> tuple[str, int, int, int]:
        now: int = utils.now_sec()
        period: int = self.quota.get_period_sec()
        period_key: str = f"{key}:period:{now // period}"
        return self._prepare_key(period_key), period, self.quota.get_limit(), now


class FixedWindowRateLimiter(FixedWindowRateLimiterCoreMixin, BaseRateLimiter):
    """Concrete implementation of BaseRateLimiter using fixed window as algorithm."""

    _DEFAULT_ATOMIC_ACTION_CLASSES: Sequence[type[store.BaseAtomicAction]] = (
        RedisLimitAtomicAction,
        MemoryLimitAtomicAction,
    )

    def _limit(self, key: str, cost: int = 1) -> RateLimitResult:
        period_key, period, limit, now = self._prepare(key)
        limited, current = cast(
            "tuple[int, int]",
            self._atomic_actions[constants.ATOMIC_ACTION_TYPE_LIMIT].do(
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
