"""Async hook system for throttled-py."""

import abc
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from ..hooks import HookContext

if TYPE_CHECKING:
    from ..rate_limiter import RateLimitResult


class Hook(abc.ABC):
    """Abstract base class for async hooks using middleware pattern.

    Custom hooks should inherit from this class and implement on_limit.
    The middleware pattern allows hooks to wrap the rate limit check,
    enabling timing measurement, exception handling, and more.

    **Example**::

        class MyHook(Hook):
            async def on_limit(
                self,
                call_next: Callable[[], Awaitable[RateLimitResult]],
                context: HookContext,
            ) -> RateLimitResult:
                start = time.time()
                result = await call_next()
                elapsed = time.time() - start
                print(f"Key {context.key}: {elapsed:.3f}s, limited={result.limited}")
                return result
    """

    @abc.abstractmethod
    async def on_limit(
        self,
        call_next: Callable[[], Awaitable["RateLimitResult"]],
        context: HookContext,
    ) -> "RateLimitResult":
        """Middleware that wraps an async rate limit check.

        :param call_next: Async function to call the next hook or the actual rate limiter.
        :param context: The rate-limiting context information.
        :return: The result from call_next() (RateLimitResult).
        """
        raise NotImplementedError


def build_hook_chain(
    hooks: list[Hook],
    do_limit: Callable[[], Awaitable["RateLimitResult"]],
    context: HookContext,
) -> Callable[[], Awaitable["RateLimitResult"]]:
    """Build an async hook chain using middleware pattern.

    hooks = [A, B] results in: A.on_limit(B.on_limit(do_limit))
    Execution order: A_before → B_before → do_limit → B_after → A_after

    Exceptions raised in hooks are caught and the chain continues.

    :param hooks: List of async hooks to chain.
    :param do_limit: The actual async rate limit function to be wrapped.
    :param context: The hook context containing rate limit metadata.
    :return: A callable that executes the async hook chain.
    """
    if not hooks:
        return do_limit

    chain = do_limit
    for hook in reversed(hooks):
        post_chain = chain

        def make_chain(
            h: Hook,
            next_fn: Callable[[], Awaitable["RateLimitResult"]],
        ):
            async def chain_fn() -> "RateLimitResult":
                next_called = False
                next_result = None

                async def tracked_next() -> "RateLimitResult":
                    """Track whether call_next() was already invoked by the hook.

                    This prevents double-execution of the downstream chain when
                    a hook raises an exception AFTER calling call_next().
                    Without tracking, the except block would call next_fn() again,
                    causing the rate limiter to consume quota twice.

                    Case 1: Hook raises BEFORE call_next() → next_called is False
                    → skip this hook and call next_fn() normally.
                    Case 2: Hook raises AFTER call_next()  → next_called is True
                    → return the cached result without re-executing.
                    Case 3: next_fn() itself raises → next_called stays False
                    → except calls next_fn() again → exception propagates.
                    """
                    nonlocal next_called, next_result
                    next_result = await next_fn()
                    next_called = True
                    return next_result

                try:
                    return await h.on_limit(tracked_next, context)
                except Exception:
                    # TODO - Logging strategy should be developed
                    if next_called:
                        return next_result
                    return await next_fn()

            return chain_fn

        chain = make_chain(hook, post_chain)

    return chain
