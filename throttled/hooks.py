"""Hook system for throttled-py."""

import abc
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rate_limiter import RateLimitResult


@dataclass(frozen=True, slots=True)
class HookContext:
    """Contextual information passed to a hook.

    This context is created before the rate limit check and does not
    include the result. The result is obtained by calling call_next().
    """

    #: Represents the identifier of the subject being rate-limited (e.g., user_id, IP).
    key: str

    #: Represents the cost of the current request.
    cost: int

    #: Represents the algorithm being used (e.g., "token_bucket").
    algorithm: str

    #: Represents the type of storage being used (e.g., "memory", "redis").
    store_type: str


class Hook(abc.ABC):
    """Abstract base class for hooks using middleware pattern.

    Custom hooks should inherit from this class and implement on_limit.
    The middleware pattern allows hooks to wrap the rate limit check,
    enabling timing measurement, exception handling, and more.

    **Example**::

        class MyHook(Hook):
            def on_limit(
                self,
                call_next: Callable[[], RateLimitResult],
                context: HookContext,
            ) -> RateLimitResult:
                start = time.time()
                result = call_next()
                elapsed = time.time() - start
                print(f"Key {context.key}: {elapsed:.3f}s, limited={result.limited}")
                return result
    """

    @abc.abstractmethod
    def on_limit(
        self,
        call_next: Callable[[], "RateLimitResult"],
        context: HookContext,
    ) -> "RateLimitResult":
        """Middleware that wraps a rate limit check.

        :param call_next: Function to call the next hook or the actual rate limiter.
        :param context: The rate-limiting context information.
        :return: The result from call_next() (RateLimitResult).
        """
        raise NotImplementedError


def build_hook_chain(
    hooks: list[Hook],
    do_limit: Callable[[], "RateLimitResult"],
    context: HookContext,
) -> Callable[[], "RateLimitResult"]:
    """Build a hook chain using middleware pattern.

    hooks = [A, B] results in: A.on_limit(B.on_limit(do_limit))
    Execution order: A_before → B_before → do_limit → B_after → A_after

    Exceptions raised in hooks are caught and the chain continues.

    :param hooks: List of hooks to chain.
    :param do_limit: The actual rate limit function to be wrapped.
    :param context: The hook context containing rate limit metadata.
    :return: A callable that executes the hook chain.
    """
    if not hooks:
        return do_limit

    chain = do_limit
    for hook in reversed(hooks):
        post_chain = chain

        def make_chain(h: Hook, next_fn: Callable[[], "RateLimitResult"]):
            def chain_fn() -> "RateLimitResult":
                try:
                    return h.on_limit(next_fn, context)
                except Exception:
                    # Hook exception: skip this hook, continue chain
                    return next_fn()

            return chain_fn

        chain = make_chain(hook, post_chain)

    return chain
