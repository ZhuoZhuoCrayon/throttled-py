import abc
from typing import Dict, List, Optional, Type

from ... import rate_limiter
from ...rate_limiter.base import BaseRateLimiterMixin
from ...types import AtomicActionTypeT
from ..store import BaseAtomicAction, BaseStore


class RateLimiterRegistry(rate_limiter.RateLimiterRegistry):
    """Registry for Async RateLimiter classes."""

    _NAMESPACE: str = "async"


class RateLimiterMeta(rate_limiter.RateLimiterMeta):
    """Metaclass for Async RateLimiter classes."""

    _REGISTRY_CLASS: Type[RateLimiterRegistry] = RateLimiterRegistry


class BaseRateLimiter(BaseRateLimiterMixin, metaclass=RateLimiterMeta):
    """Base class for Async RateLimiter."""

    def __init__(
        self,
        quota: rate_limiter.Quota,
        store: BaseStore,
        additional_atomic_actions: Optional[List[Type[BaseAtomicAction]]] = None,
    ) -> None:
        self.quota: rate_limiter.Quota = quota
        self._store: BaseStore = store
        self._atomic_actions: Dict[AtomicActionTypeT, BaseAtomicAction] = {}
        self._register_atomic_actions(additional_atomic_actions or [])

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
