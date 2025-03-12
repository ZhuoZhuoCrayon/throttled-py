import threading
from typing import Callable, Optional, Type

from .constants import RateLimiterType
from .exceptions import DataError, LimitedError
from .rate_limter import (
    BaseRateLimiter,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    per_min,
)
from .store import BaseStore, MemoryStore
from .types import KeyT, RateLimiterTypeT


class Throttled:
    def __init__(
        self,
        key: Optional[KeyT] = None,
        using: Optional[RateLimiterTypeT] = None,
        quota: Optional[Quota] = None,
        store: Optional[BaseStore] = None,
    ):
        """Initializes the Throttled class.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :param using: The type of rate limiter to use, default: token_bucket.
        :param quota: The quota for the rate limiter, default: 60 requests per minute.
        :param store: The store to use for the rate limiter, default: MemoryStore.
        """
        # TODO Support key prefix.
        # TODO Support extract key from params.
        # TODO Support get cost weight by key.
        self.key: Optional[str] = key
        self._quota: Quota = quota or per_min(60)
        self._store: BaseStore = store or MemoryStore()
        self._limiter_cls: Type[BaseRateLimiter] = RateLimiterRegistry.get(
            using or RateLimiterType.TOKEN_BUCKET.value
        )

        self._lock: threading.Lock = threading.Lock()
        self._limiter: Optional[BaseRateLimiter] = None

    def _get_limiter(self) -> BaseRateLimiter:
        """Lazily initializes and returns the rate limiter instance."""
        if self._limiter:
            return self._limiter

        with self._lock:
            # Double-check locking to ensure thread safety.
            if self._limiter:
                return self._limiter

            self._limiter = self._limiter_cls(self._quota, self._store)
            return self._limiter

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting to a function."""

        if not self.key:
            raise DataError("Decorator requires a non-empty key.")

        def _inner(*args, **kwargs):
            # TODO Add options to ignore state.
            result: RateLimitResult = self.limit(self.key)
            if result.limited:
                raise LimitedError(rate_limit_result=result)
            return func(*args, **kwargs)

        return _inner

    @classmethod
    def _validate_cost(cls, cost: int) -> None:
        """Validate the cost of the current request.
        :param cost: The cost of the current request in terms of
                     how much of the rate limit quota it consumes.
        :raise: DataError if the cost is not a positive integer.
        """
        if isinstance(cost, int) and cost > 0:
            return

        raise DataError(
            "Invalid cost: {cost}, Must be an integer greater "
            "than 0.".format(cost=cost)
        )

    def limit(self, key: KeyT, cost: int = 1) -> RateLimitResult:
        """Apply rate limiting logic to a given key with a specified cost.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :param cost: The cost of the current request in terms of how much
                     of the rate limit quota it consumes.
        :return: RateLimitResult: The result of the rate limiting check.
        :raise: DataError
        """
        self._validate_cost(cost)
        return self._get_limiter().limit(key, cost)

    def peek(self, key: KeyT) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key
           without actually modifying the state.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :return: RateLimitState - Representing the current state of
                 the rate limiter for the given key.
        """
        return self._get_limiter().peek(key)
