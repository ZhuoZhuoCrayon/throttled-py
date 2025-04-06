import threading
import time
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
from .utils import now_sec_f


class Throttled:
    # Non-blocking mode constant
    _NON_BLOCKING: float = -1
    # Interval between retries in seconds
    _WAIT_INTERVAL: float = 0.5
    # Minimum interval between retries in seconds
    _WAIT_MIN_INTERVAL: float = 0.2

    def __init__(
        self,
        key: Optional[KeyT] = None,
        timeout: Optional[float] = None,
        using: Optional[RateLimiterTypeT] = None,
        quota: Optional[Quota] = None,
        store: Optional[BaseStore] = None,
    ):
        """Initializes the Throttled class.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :param timeout: Maximum wait time in seconds when rate limit is
                        exceeded.
                        (Default) If set to -1, it will return immediately.
                        Otherwise, it will block until the request can be
                        processed or the timeout is reached.
        :param using: The type of rate limiter to use, default: token_bucket.
        :param quota: The quota for the rate limiter, default: 60 requests per minute.
        :param store: The store to use for the rate limiter, default: MemoryStore.
        """
        # TODO Support key prefix.
        # TODO Support extract key from params.
        # TODO Support get cost weight by key.
        self.key: Optional[str] = key

        if timeout is None:
            timeout = self._NON_BLOCKING
        self.timeout: float = timeout
        self._validate_timeout(self.timeout)

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
            raise DataError(f"Invalid key: {self.key}, must be a non-empty key.")

        def _inner(*args, **kwargs):
            # TODO Add options to ignore state.
            result: RateLimitResult = self.limit()
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
            f"Invalid cost: {cost}, must be an integer greater than 0.".format(cost=cost)
        )

    @classmethod
    def _validate_timeout(cls, timeout: float) -> None:
        """Validate the timeout value.
        :param timeout: Maximum wait time in seconds when rate limit is exceeded.
        :raise: DataError if the timeout is not a positive float or -1(non-blocking).
        """

        if timeout == cls._NON_BLOCKING:
            return

        if (isinstance(timeout, float) or isinstance(timeout, int)) and timeout > 0:
            return

        raise DataError(
            f"Invalid timeout: {timeout}, must be a positive float or -1(non-blocking)."
        )

    def _get_key(self, key: Optional[KeyT] = None) -> KeyT:
        # Use the provided key if available.
        if key:
            return key

        if self.key:
            return self.key

        raise DataError(f"Invalid key: {key}, must be a non-empty key.")

    def _get_timeout(self, timeout: Optional[float] = None) -> float:
        if timeout is not None:
            self._validate_timeout(timeout)
            return timeout

        return self.timeout

    def _wait(self, timeout: float, retry_after: float) -> None:
        """Wait for the specified timeout or until retry_after is reached."""
        if retry_after <= 0:
            return

        start_time: float = now_sec_f()
        while True:
            # WAIT_INTERVAL: Chunked waiting interval to avoid long blocking periods.
            # Also helps reduce actual wait time considering thread context switches.
            # WAIT_MIN_INTERVAL: Minimum wait interval to prevent busy-waiting.
            sleep_time: float = max(
                min(retry_after, self._WAIT_INTERVAL), self._WAIT_MIN_INTERVAL
            )

            # Sleep for the specified time.
            time.sleep(sleep_time)

            # Calculate the elapsed time since the start time.
            # Due to additional context switching overhead in multithread contexts,
            # we don't directly use sleep_time to calculate elapsed time.
            # Instead, we re-fetch the current time and subtract it from the start time.
            elapsed: float = now_sec_f() - start_time
            if elapsed >= retry_after or elapsed >= timeout:
                break

    def limit(
        self, key: Optional[KeyT] = None, cost: int = 1, timeout: Optional[float] = None
    ) -> RateLimitResult:
        """Apply rate limiting logic to a given key with a specified cost.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
                    Overrides the instance key if provided.
        :param cost: The cost of the current request in terms of how much
                     of the rate limit quota it consumes.
        :param timeout: Maximum wait time in seconds when rate limit is
                        exceeded.
                        If set to -1, it will return immediately.
                        Otherwise, it will block until the request can
                        be processed or the timeout is reached.
                        Overrides the instance timeout if provided.
        :return: RateLimitResult: The result of the rate limiting check.
        :raise: DataError if invalid parameters.
        """
        self._validate_cost(cost)

        key: KeyT = self._get_key(key)
        timeout: float = self._get_timeout(timeout)
        result: RateLimitResult = self._get_limiter().limit(key, cost)
        if timeout == self._NON_BLOCKING or not result.limited:
            return result

        # TODO: When cost > limit, return early instead of waiting.
        start_time: float = now_sec_f()
        while True:
            if result.state.retry_after > timeout:
                break

            self._wait(timeout, result.state.retry_after)

            result = self._get_limiter().limit(key, cost)
            if not result.limited:
                break

            elapsed: float = now_sec_f() - start_time
            if elapsed >= timeout:
                break

        return result

    def peek(self, key: KeyT) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key
           without actually modifying the state.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :return: RateLimitState - Representing the current state of
                 the rate limiter for the given key.
        """
        return self._get_limiter().peek(key)
