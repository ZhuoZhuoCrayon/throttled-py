from typing import Callable, Optional

from .exceptions import LimitedError
from .rate_limter.base import BaseRateLimiter, Quota, RateLimitResult, RateLimitState
from .rate_limter.fixed_window import FixedWindowRateLimiter
from .store.base import BaseStore
from .types import KeyT, RateLimiterTypeT


class Throttled:
    def __init__(
        self, key: KeyT, using: RateLimiterTypeT, quota: Quota, store: BaseStore
    ):
        # TODO Support key prefix.
        # TODO Support extract key from params.
        # TODO Support get cost weight by key.
        self.key: str = key
        self.using: RateLimiterTypeT = using
        self._quota: Quota = quota
        self._store: BaseStore = store

        self._limiter: Optional[BaseRateLimiter] = None

    def _get_limiter(self) -> BaseRateLimiter:
        if self._limiter is None:
            self._limiter = FixedWindowRateLimiter(self._quota, self._store)
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
