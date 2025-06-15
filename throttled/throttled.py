import abc
import threading
import time
from types import TracebackType
from typing import Callable, Optional, Type, Union

from .asyncio.rate_limiter import BaseRateLimiter as AsyncBaseRateLimiter
from .constants import RateLimiterType
from .exceptions import DataError, LimitedError
from .rate_limiter import (
    BaseRateLimiter,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    per_min,
)
from .store import MemoryStore
from .types import KeyT, LockP, RateLimiterTypeT, StoreP
from .utils import now_mono_f

RateLimiterP = Union[BaseRateLimiter, AsyncBaseRateLimiter]


class BaseThrottledMixin:
    """Mixin class for async / sync BaseThrottled."""

    __slots__ = (
        "key",
        "timeout",
        "_quota",
        "_store",
        "_limiter_cls",
        "_limiter",
        "_lock",
        "_cost",
    )

    _REGISTRY_CLASS: Type[RateLimiterRegistry] = None

    # Default store for the rate limiter.
    # By default, the global shared MemoryStore is used, when no store is specified.
    _DEFAULT_GLOBAL_STORE: StoreP = None

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
        store: Optional[StoreP] = None,
        cost: int = 1,
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
        :param cost: The cost of each request in terms of how much of the rate limit
                    quota it consumes, default: 1.
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
        self._store: StoreP = store or self._DEFAULT_GLOBAL_STORE
        self._limiter_cls: Type[RateLimiterP] = self._REGISTRY_CLASS.get(
            using or RateLimiterType.TOKEN_BUCKET.value
        )

        self._lock: LockP = self._get_lock()
        self._limiter: Optional[RateLimiterP] = None

        self._validate_cost(cost)
        self._cost: int = cost

    @classmethod
    def _get_lock(cls) -> LockP:
        return threading.Lock()

    @property
    def limiter(self) -> RateLimiterP:
        """Lazily initializes and returns the rate limiter instance."""
        if self._limiter:
            return self._limiter

        with self._lock:
            # Double-check locking to ensure thread safety.
            if self._limiter:
                return self._limiter

            self._limiter = self._limiter_cls(self._quota, self._store)
            return self._limiter

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

    def _get_wait_time(self, retry_after: float) -> float:
        """Calculate the wait time based on the retry_after value."""

        # WAIT_INTERVAL: Chunked waiting interval to avoid long blocking periods.
        # Also helps reduce actual wait time considering thread context switches.
        # WAIT_MIN_INTERVAL: Minimum wait interval to prevent busy-waiting.
        return max(min(retry_after, self._WAIT_INTERVAL), self._WAIT_MIN_INTERVAL)

    @classmethod
    def _is_exit_waiting(
        cls, start_time: float, retry_after: float, timeout: float
    ) -> bool:
        # Calculate the elapsed time since the start time.
        # Due to additional context switching overhead in multithread contexts,
        # we don't directly use sleep_time to calculate elapsed time.
        # Instead, we re-fetch the current time and subtract it from the start time.
        elapsed: float = now_mono_f() - start_time
        if elapsed >= retry_after or elapsed >= timeout:
            return True
        return False


class BaseThrottled(BaseThrottledMixin, abc.ABC):
    """Abstract class for all throttled classes."""

    @abc.abstractmethod
    def __enter__(self) -> RateLimitResult:
        """Context manager to apply rate limiting to a block of code.
        :return: RateLimitResult
        :raise: LimitedError if rate limit is exceeded.
        """
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        """Exit the context manager."""
        pass

    @abc.abstractmethod
    def __call__(
        self, func: Optional[Callable] = None
    ) -> Union[Callable, Callable[[Callable], Callable]]:
        """Decorator to apply rate limiting to a function."""
        raise NotImplementedError

    @abc.abstractmethod
    def _wait(self, timeout: float, retry_after: float) -> None:
        """Wait for the specified timeout or until retry_after is reached."""
        raise NotImplementedError

    @abc.abstractmethod
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
                        exceeded, overrides the instance timeout if provided.
                        When invoked with the ``timeout`` argument set to a
                        positive float (defaults to -1, which means return immediately):

                        * If timeout < ``RateLimitState.retry_after``, it will
                          return immediately.
                        * If timeout >= ``RateLimitState.retry_after``, it will block
                          until the request can be processed or the timeout is reached.

        :return: The result of the rate limiting check.
        :rtype: RateLimitResult
        :raises DataError: if invalid parameters are provided.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def peek(self, key: KeyT) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key
           without actually modifying the state.
        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :return: RateLimitState - Representing the current state of
                 the rate limiter for the given key.
        """
        raise NotImplementedError


class Throttled(BaseThrottled):
    _REGISTRY_CLASS: Type[RateLimiterRegistry] = RateLimiterRegistry

    _DEFAULT_GLOBAL_STORE: StoreP = MemoryStore()

    def __enter__(self) -> RateLimitResult:
        result: RateLimitResult = self.limit()
        if result.limited:
            raise LimitedError(rate_limit_result=result)
        return result

    def __call__(
        self, func: Optional[Callable] = None
    ) -> Union[Callable, Callable[[Callable], Callable]]:
        """Decorator to apply rate limiting to a function.
        The cost value is taken from the Throttled instance's initialization.

        Usage:
        @Throttled(key="key")
        def func(): pass

        or with cost:
        @Throttled(key="key", cost=2)
        def func(): pass
        """

        def decorator(f: Callable) -> Callable:
            if not self.key:
                raise DataError(f"Invalid key: {self.key}, must be a non-empty key.")

            def _inner(*args, **kwargs):
                # TODO Add options to ignore state.
                result: RateLimitResult = self.limit(cost=self._cost)
                if result.limited:
                    raise LimitedError(rate_limit_result=result)
                return f(*args, **kwargs)

            return _inner

        if func is None:
            return decorator

        return decorator(func)

    def _wait(self, timeout: float, retry_after: float) -> None:
        if retry_after <= 0:
            return

        start_time: float = now_mono_f()
        while True:
            # Sleep for the specified time.
            wait_time = self._get_wait_time(retry_after)
            time.sleep(wait_time)

            if self._is_exit_waiting(start_time, retry_after, timeout):
                break

    def limit(
        self, key: Optional[KeyT] = None, cost: int = 1, timeout: Optional[float] = None
    ) -> RateLimitResult:
        self._validate_cost(cost)
        key: KeyT = self._get_key(key)
        timeout: float = self._get_timeout(timeout)
        result: RateLimitResult = self.limiter.limit(key, cost)
        if timeout == self._NON_BLOCKING or not result.limited:
            return result

        # TODO: When cost > limit, return early instead of waiting.
        start_time: float = now_mono_f()
        while True:
            if result.state.retry_after > timeout:
                break

            self._wait(timeout, result.state.retry_after)

            result = self.limiter.limit(key, cost)
            if not result.limited:
                break

            elapsed: float = now_mono_f() - start_time
            if elapsed >= timeout:
                break

        return result

    def peek(self, key: KeyT) -> RateLimitState:
        return self.limiter.peek(key)
