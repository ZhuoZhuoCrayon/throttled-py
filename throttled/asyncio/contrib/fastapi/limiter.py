"""Async decorator-based rate limiter for FastAPI."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, TypeAlias, TypeVar

from starlette.requests import Request
from throttled.asyncio.store import MemoryStore
from throttled.asyncio.throttled import Throttled
from throttled.constants import RateLimiterType

from .exceptions import RateLimitExceededError
from .key_funcs import get_remote_address
from .keys import KeyParts, compose_key
from .middleware import _STATE_KEY

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from throttled.asyncio.hooks import Hook
    from throttled.asyncio.rate_limiter import Quota, RateLimitResult
    from throttled.types import RateLimiterTypeT, StoreP


P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

#: Sync or async callable that returns the principal key for a request.
KeyFunc: TypeAlias = Callable[[Request], str | Awaitable[str]]


class Limiter:
    """Async decorator-based rate limiter for FastAPI routes.

    :param quota: Required. Default quota for all decorated routes.
        Accepts a :class:`Quota` instance or a DSL string such as
        ``"100/m"`` or ``"10/s burst 20"``
        (see :mod:`throttled.rate_limiter.quota_parser`).
    :param store: Storage backend. Defaults to
        :class:`~throttled.asyncio.store.MemoryStore` when ``None``.
    :param using: Rate-limit algorithm. Defaults to ``token_bucket`` to
        match :class:`throttled.asyncio.throttled.Throttled`.
    :param key_func: Sync or async callable that returns the principal
        key. Defaults to :func:`.key_funcs.get_remote_address`.
    :param hooks: Optional async hooks forwarded to the internal
        :class:`~throttled.asyncio.throttled.Throttled` instances.
    """

    def __init__(
        self,
        quota: Quota | str,
        *,
        store: StoreP | None = None,
        using: RateLimiterTypeT = RateLimiterType.TOKEN_BUCKET.value,
        key_func: KeyFunc = get_remote_address,
        hooks: Sequence[Hook] | None = None,
    ) -> None:
        if quota is None:
            raise TypeError("Limiter requires an explicit quota.")
        self._default_quota: Quota | str = quota
        self._store: StoreP = store or MemoryStore()
        self._using: RateLimiterTypeT = using
        self._key_func: KeyFunc = key_func
        self._hooks: Sequence[Hook] | None = hooks

    def limit(
        self,
        quota: Quota | str | None = None,
        *,
        key_func: KeyFunc | None = None,
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        """Decorate an async route function with rate limiting.

        :param quota: Optional per-route quota override. Falls back to
            the instance default when ``None``.
        :param key_func: Optional per-route key function override.
            Falls back to the instance default when ``None``.
        :raises TypeError: when applied to a sync function.
        """
        resolved_quota: Quota | str = quota if quota is not None else self._default_quota
        resolved_key_func: KeyFunc = key_func if key_func is not None else self._key_func
        throttled: Throttled = Throttled(
            quota=resolved_quota,
            using=self._using,
            store=self._store,
            hooks=self._hooks,
        )

        def decorator(
            func: Callable[P, Awaitable[R]],
        ) -> Callable[P, Awaitable[R]]:
            if not inspect.iscoroutinefunction(func):
                raise TypeError(
                    "Async Limiter.limit() cannot wrap sync route "
                    f"function '{func.__qualname__}'. Use an "
                    "'async def' route function with throttled.asyncio."
                )

            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                request: Request = _extract_request(func, tuple(args), kwargs)
                result: RateLimitResult = await _check(
                    request=request,
                    throttled=throttled,
                    key_func=resolved_key_func,
                )
                if result.limited:
                    logger.debug(
                        "Rate limit exceeded: %s %s",
                        request.method,
                        _route_template(request),
                    )
                    raise RateLimitExceededError(result)

                logger.debug(
                    "Rate limit passed: %s %s, remaining=%d",
                    request.method,
                    _route_template(request),
                    result.state.remaining if result.state else -1,
                )
                setattr(request.state, _STATE_KEY, result)
                return await func(*args, **kwargs)

            return wrapper

        return decorator


async def _check(
    *,
    request: Request,
    throttled: Throttled,
    key_func: KeyFunc,
) -> RateLimitResult:
    """Run the rate-limit check for one request.

    :param request: Incoming FastAPI request.
    :param throttled: The per-route ``Throttled`` instance.
    :param key_func: Callable that extracts the principal from the
        request.
    :returns: The :class:`RateLimitResult`. Caller inspects
        ``result.limited`` to decide between 429 and success.
    """
    principal: str = await _resolve_principal(key_func, request)
    route: str = _route_template(request)
    key: str = compose_key(
        KeyParts(method=request.method, route=route, principal=principal)
    )

    return await throttled.limit(key=key)


async def _resolve_principal(key_func: KeyFunc, request: Request) -> str:
    """Run ``key_func`` and resolve its sync or async result to a string.

    Centralizes the sync-or-async branch so callers receive a plain
    ``str`` and do not need to narrow ``str | Awaitable[str]`` at the
    call site.

    :param key_func: User-provided principal extractor; may return
        either a string directly or an awaitable that resolves to one.
    :param request: Incoming FastAPI request.
    :returns: The resolved principal string.
    """
    key_value: str | Awaitable[str] = key_func(request)
    if inspect.isawaitable(key_value):
        return await key_value
    return key_value


def _route_template(request: Request) -> str:
    """Return the mount-aware matched route template.

    Combines ``scope["root_path"]`` (the mount prefix FastAPI sets
    when an app is mounted under another) with
    ``scope["route"].path_format`` so two mounts exposing the same
    child path do not collide into one rate-limit key.

    :param request: Incoming FastAPI request.
    :returns: Mount-aware route template string.
    """
    scope_route = request.scope["route"]
    path_format: str = scope_route.path_format
    root_path: str = request.scope.get("root_path", "") or ""
    return f"{root_path}{path_format}"


def _extract_request(
    func: Callable[..., object],
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> Request:
    """Find the :class:`Request` argument regardless of parameter name.

    :param func: Decorated route function, used only to produce a
        clear error message when no ``Request`` is found.
    :param args: Positional arguments passed to the route.
    :param kwargs: Keyword arguments passed to the route.
    :returns: The ``Request`` instance found in ``args`` or ``kwargs``.
    :raises TypeError: when no ``Request`` parameter is declared on
        the route function.
    """
    for value in kwargs.values():
        if isinstance(value, Request):
            return value
    for value in args:
        if isinstance(value, Request):
            return value
    raise TypeError(
        "@Limiter.limit requires a Request parameter in "
        f"'{func.__qualname__}'. Declare one like 'request: Request' "
        "(any name is fine)."
    )
