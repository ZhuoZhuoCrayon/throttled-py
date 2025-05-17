import abc
from typing import Type

from ... import rate_limiter


class RateLimiterRegistry(rate_limiter.RateLimiterRegistry):
    """Registry for Async RateLimiter classes."""

    _NAMESPACE: str = "async"


class RateLimiterMeta(rate_limiter.RateLimiterMeta):
    """Metaclass for Async RateLimiter classes."""

    _REGISTRY_CLASS: Type[RateLimiterRegistry] = RateLimiterRegistry


class BaseRateLimiter(rate_limiter.BaseRateLimiterMixin, metaclass=RateLimiterMeta):
    """Base class for Async RateLimiter."""

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
