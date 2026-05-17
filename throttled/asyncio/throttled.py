import abc
import asyncio
from collections.abc import Callable, Coroutine, Sequence
from functools import wraps
from types import TracebackType
from typing import Any

from .. import exceptions, types, utils
from .._throttled.logic import ThrottledLogic
from .hooks import Hook, HookContext, build_hook_chain
from .rate_limiter import (
    BaseRateLimiter,
    Quota,
    RateLimiterRegistry,
    RateLimitResult,
    RateLimitState,
)
from .store import BaseStore, MemoryStore

AsyncFunc = Callable[types.P, Coroutine[Any, Any, types.R]]


class BaseThrottled(ThrottledLogic, abc.ABC):
    """Abstract class for all throttled classes."""

    __slots__ = (
        "key",
        "timeout",
        "_quota",
        "_cost",
        "_store",
        "_limiter_cls",
        "_limiter",
        "_hooks",
    )

    _ALLOWED_HOOK_TYPES = (Hook,)
    _REGISTRY_CLASS: type[RateLimiterRegistry] = RateLimiterRegistry
    _DEFAULT_GLOBAL_STORE: BaseStore = MemoryStore()

    def __init__(
        self,
        key: types.KeyT | None = None,
        timeout: float | None = None,
        using: types.RateLimiterTypeT | None = None,
        quota: Quota | str | None = None,
        store: BaseStore | None = None,
        cost: int = 1,
        hooks: Sequence[Hook] | None = None,
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
            the global shared :class:`throttled.asyncio.store.MemoryStore` instance
            with maximum capacity of 1024, so you don't usually need to create it
            manually.
        :type store: :class:`throttled.asyncio.store.BaseStore`
        :param cost: The cost of each request in terms of how much of the rate limit
            quota it consumes, default: 1.
        :param hooks: A sequence of hooks invoked by the middleware before and/or after
            each ``limit()`` operation, including any internal retries.
        """
        self.key: str | None = key

        self.timeout: float = self._NON_BLOCKING if timeout is None else timeout
        self._validate_timeout(self.timeout)

        self._quota: Quota = self._parse_quota(quota)
        self._store: BaseStore = store or self._DEFAULT_GLOBAL_STORE
        self._limiter_cls: type[BaseRateLimiter] = self._REGISTRY_CLASS.get(
            using or self._DEFAULT_RATE_LIMITER_TYPE
        )
        self._limiter: BaseRateLimiter | None = None
        self._hooks: tuple[Hook, ...] = self._validate_hooks(hooks)

        self._validate_cost(cost)
        self._cost: int = cost

    @property
    def limiter(self) -> BaseRateLimiter:
        """Lazily initializes and returns the async rate limiter instance."""
        limiter: BaseRateLimiter | None = self._limiter
        if limiter is not None:
            return limiter

        created_limiter: BaseRateLimiter = self._limiter_cls(self._quota, self._store)
        self._limiter = created_limiter
        return created_limiter

    def _validate_hooks(self, hooks: Sequence[Hook] | None) -> tuple[Hook, ...]:
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
    ) -> None:
        """Exit the context manager."""

    @abc.abstractmethod
    async def _wait(self, timeout: float, retry_after: float) -> None:
        """Wait for the specified timeout or until retry_after is reached."""
        raise NotImplementedError

    @abc.abstractmethod
    async def limit(
        self,
        key: types.KeyT | None = None,
        cost: int = 1,
        timeout: float | None = None,
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
    async def peek(self, key: types.KeyT) -> RateLimitState:
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

    async def __aenter__(self) -> RateLimitResult:
        result: RateLimitResult = await self.limit()
        if result.limited:
            raise exceptions.LimitedError(rate_limit_result=result)
        return result

    async def _wait(self, timeout: float, retry_after: float) -> None:
        if retry_after <= 0:
            return

        start_time: float = utils.now_mono_f()
        while True:
            # Sleep for the specified time.
            wait_time = self._get_wait_time(retry_after)
            await asyncio.sleep(wait_time)

            if self._is_exit_waiting(start_time, retry_after, timeout):
                break

    async def _do_limit(
        self, key: types.KeyT, cost: int, timeout: float
    ) -> RateLimitResult:
        """Execute rate limit check with retry logic.

        This method contains the entire limit logic including
        blocking/retry, so hooks can measure the total duration.
        """
        result: RateLimitResult = await self.limiter.limit(key, cost)

        if timeout == self._NON_BLOCKING or not result.limited:
            return result

        # TODO: When cost > limit, return early instead of waiting.
        start_time: float = utils.now_mono_f()
        while True:
            if result.state.retry_after > timeout:
                break

            await self._wait(timeout, result.state.retry_after)

            result = await self.limiter.limit(key, cost)

            if not result.limited:
                break

            elapsed: float = utils.now_mono_f() - start_time
            if elapsed >= timeout:
                break

        return result

    async def limit(
        self,
        key: types.KeyT | None = None,
        cost: int = 1,
        timeout: float | None = None,
    ) -> RateLimitResult:
        self._validate_cost(cost)
        current_key = self._get_key(key)
        current_timeout = self._get_timeout(timeout)

        if not self._hooks:
            return await self._do_limit(current_key, cost, current_timeout)

        async def do_limit() -> RateLimitResult:
            return await self._do_limit(current_key, cost, current_timeout)

        context = HookContext(
            key=current_key,
            cost=cost,
            algorithm=self._limiter_cls.Meta.type,
            store_type=self._store.TYPE,
        )
        chain = build_hook_chain(self._hooks, do_limit, context)
        return await chain()

    async def peek(self, key: types.KeyT) -> RateLimitState:
        return await self.limiter.peek(key)

    def __call__(self, func: AsyncFunc[types.P, types.R]) -> AsyncFunc[types.P, types.R]:
        """Decorator to apply rate limiting to an async function.

        The cost value is taken from the Throttled instance's initialization.

        Usage:
        @Throttled(key="key")
        async def func(): pass

        or with cost:
        @Throttled(key="key", cost=2)
        async def func(): pass
        """

        def decorator(
            f: AsyncFunc[types.P, types.R],
        ) -> AsyncFunc[types.P, types.R]:
            if not self.key:
                raise exceptions.DataError(
                    f"Invalid key: {self.key}, must be a non-empty key."
                )

            @wraps(f)
            async def _inner(*args: types.P.args, **kwargs: types.P.kwargs) -> types.R:
                result: RateLimitResult = await self.limit(cost=self._cost)
                if result.limited:
                    raise exceptions.LimitedError(rate_limit_result=result)
                return await f(*args, **kwargs)

            return _inner

        return decorator(func)
