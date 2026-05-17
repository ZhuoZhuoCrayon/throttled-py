import abc
from abc import ABC
from typing import TYPE_CHECKING

from ... import exceptions, rate_limiter
from ...rate_limiter.base import BaseRateLimiterRegistry

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar

    from ... import types
    from ..store import BaseAtomicAction, BaseStore


class RateLimiterRegistry(BaseRateLimiterRegistry["BaseRateLimiter"]):
    """Registry for Async RateLimiter classes."""

    _NAMESPACE: "ClassVar[str]" = "async"

    # Redeclare so sync and async class tables stay independent.
    _RATE_LIMITERS: "ClassVar[dict[types.RateLimiterTypeT, type[BaseRateLimiter]]]" = {}

    @classmethod
    def _rate_limiters(
        cls,
    ) -> "dict[types.RateLimiterTypeT, type[BaseRateLimiter]]":
        """Return the async RateLimiter class table."""
        return cls._RATE_LIMITERS


class RateLimiterMeta(rate_limiter.RateLimiterMeta):
    """Metaclass for Async RateLimiter classes."""

    _REGISTRY_CLASS: type[RateLimiterRegistry] = RateLimiterRegistry


class BaseRateLimiter(
    rate_limiter.BaseRateLimiterMixin,
    ABC,
    metaclass=RateLimiterMeta,
):
    """Base class for Async RateLimiter."""

    _store: "BaseStore"
    _atomic_actions: "dict[types.AtomicActionTypeT, BaseAtomicAction]"

    _DEFAULT_ATOMIC_ACTION_CLASSES: "Sequence[type[BaseAtomicAction]]" = ()

    def __init__(
        self,
        quota: rate_limiter.Quota,
        store: "BaseStore",
        additional_atomic_actions: "Sequence[type[BaseAtomicAction]] | None" = None,
    ) -> None:
        self.quota: rate_limiter.Quota = quota
        self._store = store
        self._atomic_actions = {}
        self._register_atomic_actions(additional_atomic_actions or ())

    @classmethod
    def _default_atomic_action_classes(
        cls,
    ) -> "Sequence[type[BaseAtomicAction]]":
        return cls._DEFAULT_ATOMIC_ACTION_CLASSES

    def _validate_registered_atomic_actions(self) -> None:
        supported_types = set(self._supported_atomic_action_types())
        registered_types = set(self._atomic_actions.keys())
        missing_types = supported_types - registered_types
        if missing_types:
            raise exceptions.SetUpError(
                "Missing AtomicActionTypes: expected [{expected}] but missing "
                "[{missing}].".format(
                    expected=",".join(sorted(supported_types)),
                    missing=",".join(sorted(missing_types)),
                )
            )

    def _register_atomic_actions(
        self, classes: "Sequence[type[BaseAtomicAction]]"
    ) -> None:
        all_classes = list(self._default_atomic_action_classes()) + list(classes)
        for action_cls in all_classes:
            if action_cls.STORE_TYPE != self._store.TYPE:
                continue
            self._atomic_actions[action_cls.TYPE] = self._store.make_atomic(action_cls)

        self._validate_registered_atomic_actions()

    @abc.abstractmethod
    async def _limit(self, key: str, cost: int) -> rate_limiter.RateLimitResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def _peek(self, key: str) -> rate_limiter.RateLimitState:
        raise NotImplementedError

    async def limit(self, key: str, cost: int = 1) -> rate_limiter.RateLimitResult:
        return await self._limit(key, cost)

    async def peek(self, key: str) -> rate_limiter.RateLimitState:
        return await self._peek(key)
