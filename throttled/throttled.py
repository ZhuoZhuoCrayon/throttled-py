from typing import Callable, Optional, Type

from .exceptions import LimitedError
from .rate_limter import (
    BaseRateLimiter,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
)
from .store import BaseStore
from .types import KeyT, RateLimiterTypeT


class Throttled:
    def __init__(
        self, key: KeyT, using: RateLimiterTypeT, quota: Quota, store: BaseStore
    ):
        # TODO Support key prefix.
        # TODO Support extract key from params.
        # TODO Support get cost weight by key.
        self.key: str = key
        self._quota: Quota = quota
        self._store: BaseStore = store
        self._limiter_cls: Type[BaseRateLimiter] = RateLimiterRegistry.get(using)

        self._limiter: Optional[BaseRateLimiter] = None

    def _get_limiter(self) -> BaseRateLimiter:
        if self._limiter is None:
            self._limiter = self._limiter_cls(self._quota, self._store)
        return self._limiter

    def __call__(self, func: Callable) -> Callable:
        def _inner(*args, **kwargs):
            # TODO add options to ignore state.
            if self.limit(self.key).limited:
                raise LimitedError
            return func(*args, **kwargs)

        return _inner

    def limit(self, key: KeyT, cost: int = 1) -> RateLimitResult:
        return self._get_limiter().limit(key, cost)

    def peek(self, key: KeyT) -> RateLimitState:
        return self._get_limiter().peek(key)
