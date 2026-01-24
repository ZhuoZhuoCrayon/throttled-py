import abc
import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from types import TracebackType

from ..exceptions import DataError, LimitedError
from ..throttled import BaseThrottledMixin
from ..types import KeyT, StoreP
from ..utils import now_mono_f
from .rate_limiter import RateLimiterRegistry, RateLimitResult, RateLimitState
from .store import MemoryStore


class BaseThrottled(BaseThrottledMixin, abc.ABC):
    """Abstract class for all throttled classes."""

    @abc.abstractmethod
    async def __aenter__(self) -> RateLimitResult:
        """Context manager to apply rate limiting to a block of code.

        :return: RateLimitResult
        :raise: LimitedError if rate limit is exceeded.
        """
        raise NotImplementedError

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        """Exit the context manager."""

    @abc.abstractmethod
    def __call__(
        self, func: Callable[..., Coroutine] | None = None
    ) -> (
        Callable[..., Coroutine]
        | Callable[[Callable[..., Coroutine]], Callable[..., Coroutine]]
    ):
        """Decorator to apply rate limiting to an async function."""
        raise NotImplementedError

    @abc.abstractmethod
    async def _wait(self, timeout: float, retry_after: float) -> None:
        """Wait for the specified timeout or until retry_after is reached."""
        raise NotImplementedError

    @abc.abstractmethod
    async def limit(
        self, key: KeyT | None = None, cost: int = 1, timeout: float | None = None
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
        raise NotImplementedError

    @abc.abstractmethod
    async def peek(self, key: KeyT) -> RateLimitState:
        """Retrieve the current state of rate limiter for the given key.

        This does not modify the rate limiter state.

        :param key: The unique identifier for the rate limit subject.
                    eg: user ID or IP address.
        :return: RateLimitState - Representing the current state of
                 the rate limiter for the given key.
        """
        raise NotImplementedError


class Throttled(BaseThrottled):
    """Async rate limiter that provides throttling functionality."""

    _REGISTRY_CLASS: type[RateLimiterRegistry] = RateLimiterRegistry

    _DEFAULT_GLOBAL_STORE: StoreP = MemoryStore()

    async def __aenter__(self) -> RateLimitResult:
        result: RateLimitResult = await self.limit()
        if result.limited:
            raise LimitedError(rate_limit_result=result)
        return result

    async def _wait(self, timeout: float, retry_after: float) -> None:
        if retry_after <= 0:
            return

        start_time: float = now_mono_f()
        while True:
            # Sleep for the specified time.
            wait_time = self._get_wait_time(retry_after)
            await asyncio.sleep(wait_time)

            if self._is_exit_waiting(start_time, retry_after, timeout):
                break

    async def limit(
        self, key: KeyT | None = None, cost: int = 1, timeout: float | None = None
    ) -> RateLimitResult:
        self._validate_cost(cost)
        key: KeyT = self._get_key(key)
        timeout: float = self._get_timeout(timeout)
        result: RateLimitResult = await self.limiter.limit(key, cost)
        if timeout == self._NON_BLOCKING or not result.limited:
            return result

        start_time: float = now_mono_f()
        while True:
            if result.state.retry_after > timeout:
                break

            await self._wait(timeout, result.state.retry_after)

            result: RateLimitResult = await self.limiter.limit(key, cost)
            if not result.limited:
                break

            elapsed: float = now_mono_f() - start_time
            if elapsed >= timeout:
                break

        return result

    async def peek(self, key: KeyT) -> RateLimitState:
        return await self.limiter.peek(key)

    def __call__(
        self, func: Callable[..., Coroutine] | None = None
    ) -> (
        Callable[..., Coroutine]
        | Callable[[Callable[..., Coroutine]], Callable[..., Coroutine]]
    ):
        """Decorator to apply rate limiting to an async function.

        The cost value is taken from the Throttled instance's initialization.

        Usage:
        @Throttled(key="key")
        async def func(): pass

        or with cost:
        @Throttled(key="key", cost=2)
        async def func(): pass
        """

        def decorator(f: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            if not self.key:
                raise DataError(f"Invalid key: {self.key}, must be a non-empty key.")

            @wraps(f)
            async def _inner(*args, **kwargs):
                result: RateLimitResult = await self.limit(cost=self._cost)
                if result.limited:
                    raise LimitedError(rate_limit_result=result)
                return await f(*args, **kwargs)

            return _inner

        if func is None:
            return decorator

        return decorator(func)
