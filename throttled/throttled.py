import abc
import threading
import time
from _thread import LockType
from collections.abc import Callable, Sequence
from functools import wraps
from types import TracebackType
from typing import Generic, TypeVar, cast

from . import types
from .asyncio.hooks import Hook as AsyncHook
from .asyncio.rate_limiter import BaseRateLimiter as AsyncBaseRateLimiter
from .constants import RateLimiterType
from .exceptions import DataError, LimitedError
from .hooks import Hook, HookContext, build_hook_chain
from .rate_limiter import (
    BaseRateLimiter,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
    per_min,
)
from .rate_limiter.quota_parser import parse as parse_quota
from .store import MemoryStore
from .utils import now_mono_f

HookP = Hook | AsyncHook
Func = Callable[types.P, types.R]

_LimiterT = TypeVar("_LimiterT", bound=BaseRateLimiter | AsyncBaseRateLimiter)
_HookT = TypeVar("_HookT", bound=HookP)
_StoreT = TypeVar("_StoreT", bound=types.StoreP)


class BaseThrottledMixin(Generic[_LimiterT, _HookT, _StoreT]):
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
        "_hooks",
    )

    _REGISTRY_CLASS: type[RateLimiterRegistry] | None = None
    _ALLOWED_HOOK_TYPES: tuple[type[HookP], ...] = ()

    # Default store for the rate limiter.
    # By default, the global shared MemoryStore is used, when no store is specified.
    _DEFAULT_GLOBAL_STORE: types.StoreP | None = None

    # Non-blocking mode constant
    _NON_BLOCKING: float = -1
    # Interval between retries in seconds
    _WAIT_INTERVAL: float = 0.5
    # Minimum interval between retries in seconds
    _WAIT_MIN_INTERVAL: float = 0.2

    def __init__(
        self,
        key: types.KeyT | None = None,
        timeout: float | None = None,
        using: types.RateLimiterTypeT | None = None,
        quota: Quota | str | None = None,
        store: _StoreT | None = None,
        cost: int = 1,
        hooks: Sequence[_HookT] | None = None,
    ) -> None:
        """Initializes the Throttled class.

        :param key: The unique identifier for the rate limit subject,
            e.g. user ID or IP address.
        :param timeout: Maximum wait time in seconds when rate limit is exceeded.
            (Default) If set to -1, it will return immediately.
            Otherwise, it will block until the request can be processed
            or the timeout is reached.
        :param using: The type of rate limiter to use, you can choose from
            :class:`RateLimiterType`, default: ``token_bucket``.
        :param quota: The quota for the rate limiter, default: 60 requests per minute.
            It accepts either:
            - :class:`throttled.rate_limiter.Quota`
            - A quota DSL string, e.g. ``"100/s burst 200"``
        :param store: The store to use for the rate limiter. By default, it uses
            the global shared :class:`throttled.store.MemoryStore` instance with
            maximum capacity of 1024, so you don't usually need to create it manually.
        :type store: :class:`throttled.store.BaseStore`
        :param cost: The cost of each request in terms of how much of the rate limit
            quota it consumes, default: 1.
        :param hooks: A sequence of hooks invoked by the middleware before and/or after
            each ``limit()`` operation, including any internal retries.
        """
        # TODO Support key prefix.
        # TODO Support extract key from params.
        # TODO Support get cost weight by key.
        self.key: str | None = key

        self.timeout: float = self._NON_BLOCKING if timeout is None else timeout
        self._validate_timeout(self.timeout)

        self._quota: Quota = self._parse_quota(quota)
        default_store: _StoreT | None = store or cast(
            "_StoreT | None", self._DEFAULT_GLOBAL_STORE
        )
        if default_store is None:
            raise DataError("Invalid store: store is required for current throttler.")
        self._store: _StoreT = default_store

        if self._REGISTRY_CLASS is None:
            raise DataError(
                "Invalid throttler setup: rate limiter registry is not configured."
            )
        self._limiter_cls: type[_LimiterT] = cast(
            "type[_LimiterT]",
            self._REGISTRY_CLASS.get(using or RateLimiterType.TOKEN_BUCKET.value),
        )

        self._lock: LockType = self._get_lock()
        self._limiter: _LimiterT | None = None
        self._hooks: tuple[_HookT, ...] = self._validate_hooks(hooks)

        self._validate_cost(cost)
        self._cost: int = cost

    @classmethod
    def _get_lock(cls) -> LockType:
        return threading.Lock()

    def _make_limiter(self) -> _LimiterT:
        """Create a typed limiter instance from the registry-selected class."""
        limiter_factory: Callable[[Quota, _StoreT], _LimiterT] = cast(
            "Callable[[Quota, _StoreT], _LimiterT]", self._limiter_cls
        )
        return limiter_factory(self._quota, self._store)

    @property
    def limiter(self) -> _LimiterT:
        """Lazily initializes and returns the rate limiter instance."""
        limiter: _LimiterT | None = self._limiter
        if limiter is not None:
            return limiter

        with self._lock:
            # Double-check locking to ensure thread safety.
            limiter = self._limiter
            if limiter is not None:
                return limiter

            created_limiter: _LimiterT = self._make_limiter()
            self._limiter = created_limiter
            return created_limiter

    def _validate_hooks(self, hooks: Sequence[_HookT] | None) -> tuple[_HookT, ...]:
        """Validate that all hooks are of the expected type and return as tuple."""
        if not hooks:
            return ()
        for hook in hooks:
            if not isinstance(hook, self._ALLOWED_HOOK_TYPES):
                expected = ", ".join(t.__name__ for t in self._ALLOWED_HOOK_TYPES)
                raise TypeError(
                    f"Invalid hook type: {type(hook).__name__}. Expected: {expected}"
                )
        return tuple(hooks)

    @classmethod
    def _validate_cost(cls, cost: int) -> None:
        """Validate the cost of the current request.

        :param cost: The cost of the current request in terms of how much of
            the rate limit quota it consumes.
            It must be an integer greater than or equal to 0.
        :raise: :class:`throttled.exceptions.DataError` if the cost is
            not a non-negative integer.
        """
        if isinstance(cost, int) and cost >= 0:
            return

        raise DataError(
            f"Invalid cost: {cost}, must be an integer greater than or equal to 0."
        )

    @classmethod
    def _validate_timeout(cls, timeout: float) -> None:
        """Validate the timeout value.

        :param timeout: Maximum wait time in seconds when rate limit is exceeded.
        :raise: DataError if the timeout is not a positive float or -1(non-blocking).
        """
        if timeout == cls._NON_BLOCKING:
            return

        if isinstance(timeout, (int, float)) and timeout > 0:
            return

        raise DataError(
            f"Invalid timeout: {timeout}, must be a positive float or -1(non-blocking)."
        )

    @classmethod
    def _parse_quota(cls, quota: Quota | str | None) -> Quota:
        if quota is None:
            return per_min(60)

        if isinstance(quota, Quota):
            return quota

        parsed_quotas = parse_quota(quota)
        if len(parsed_quotas) > 1:
            raise DataError(
                "Invalid quota: multiple quota rules are not supported in "
                "Throttled(quota=...) yet."
            )
        return parsed_quotas[0]

    def _get_key(self, key: types.KeyT | None = None) -> types.KeyT:
        # Use the provided key if available.
        if key:
            return key

        if self.key:
            return self.key

        raise DataError(f"Invalid key: {key}, must be a non-empty key.")

    def _get_timeout(self, timeout: float | None = None) -> float:
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
        return elapsed >= retry_after or elapsed >= timeout


class BaseThrottled(
    BaseThrottledMixin[BaseRateLimiter, Hook, types.SyncStoreP], abc.ABC
):
    """Abstract class for all throttled classes."""

    _ALLOWED_HOOK_TYPES = (Hook,)

    @abc.abstractmethod
    def __enter__(self) -> RateLimitResult:
        """Context manager to apply rate limiting to a block of code.

        :return: :class:`RateLimitResult` - The result of the rate limiting check.
        :raise: :class:`throttled.exceptions.LimitedError` if the rate limit
            is exceeded.
        """
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager."""

    @abc.abstractmethod
    def __call__(self, func: Func[types.P, types.R]) -> Func[types.P, types.R]:
        """Decorator to apply rate limiting to a function."""
        raise NotImplementedError

    @abc.abstractmethod
    def _wait(self, timeout: float, retry_after: float) -> None:
        """Wait for the specified timeout or until retry_after is reached."""
        raise NotImplementedError

    @abc.abstractmethod
    def limit(
        self,
        key: types.KeyT | None = None,
        cost: int = 1,
        timeout: float | None = None,
    ) -> RateLimitResult:
        """Apply rate limiting logic to a given key with a specified cost.

        :param key: The unique identifier for the rate limit subject,
            e.g. user ID or IP address, it will override the instance key if provided.
        :param cost: The cost of the current request in terms of how much
            of the rate limit quota it consumes.
        :param timeout: Maximum wait time in seconds when rate limit is
            exceeded, overrides the instance timeout if provided.
            When invoked with the ``timeout`` argument set to a
            positive float (defaults to -1, which means return immediately):

            * If timeout < ``RateLimitState.retry_after``, it will return immediately.
            * If timeout >= ``RateLimitState.retry_after``, it will block until
              the request can be processed or the timeout is reached.

        :return: The result of the rate limiting check.
        :raise: :class:`throttled.exceptions.DataError` if invalid parameters
            are provided.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def peek(self, key: types.KeyT) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key.

        :param key: The unique identifier for the rate limit subject,
            e.g. user ID or IP address.

        :return: :class:`throttled.RateLimitState` - The current state of the
            rate limiter for the given key.
        """
        raise NotImplementedError


class Throttled(BaseThrottled):
    """Throttled class for synchronous rate limiting."""

    _REGISTRY_CLASS: type[RateLimiterRegistry] = RateLimiterRegistry

    _DEFAULT_GLOBAL_STORE: types.SyncStoreP = MemoryStore()

    def __enter__(self) -> RateLimitResult:
        result: RateLimitResult = self.limit()
        if result.limited:
            raise LimitedError(rate_limit_result=result)
        return result

    def __call__(self, func: Func[types.P, types.R]) -> Func[types.P, types.R]:
        """Decorator to apply rate limiting to a function.

        The cost value is taken from the Throttled instance's initialization.

        Usage::

        >>> from throttled import Throttled
        >>>
        >>> @Throttled(key="key")
        >>> def demo(): pass

        or with cost:

        >>> from throttled import Throttled
        >>>
        >>> @Throttled(key="key", cost=2)
        >>> def demo(): pass
        """

        def decorator(f: Func[types.P, types.R]) -> Func[types.P, types.R]:
            if not self.key:
                raise DataError(f"Invalid key: {self.key}, must be a non-empty key.")

            @wraps(f)
            def _inner(*args: types.P.args, **kwargs: types.P.kwargs) -> types.R:
                # TODO Add options to ignore state.
                result: RateLimitResult = self.limit(cost=self._cost)
                if result.limited:
                    raise LimitedError(rate_limit_result=result)
                return f(*args, **kwargs)

            return _inner

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

    def _do_limit(self, key: types.KeyT, cost: int, timeout: float) -> RateLimitResult:
        """Execute rate limit check with retry logic.

        This method contains the entire limit logic including
        blocking/retry, so hooks can measure the total duration.
        """
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

    def limit(
        self,
        key: types.KeyT | None = None,
        cost: int = 1,
        timeout: float | None = None,
    ) -> RateLimitResult:
        self._validate_cost(cost)
        resolved_key: types.KeyT = self._get_key(key)
        resolved_timeout: float = self._get_timeout(timeout)

        if not self._hooks:
            return self._do_limit(resolved_key, cost, resolved_timeout)

        def do_limit() -> RateLimitResult:
            return self._do_limit(resolved_key, cost, resolved_timeout)

        # Build the hook chain
        context = HookContext(
            key=resolved_key,
            cost=cost,
            algorithm=self._limiter_cls.Meta.type,
            store_type=self._store.TYPE,
        )
        chain = build_hook_chain(self._hooks, do_limit, context)
        return chain()

    def peek(self, key: types.KeyT) -> RateLimitState:
        return self.limiter.peek(key)
