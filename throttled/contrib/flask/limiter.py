"""Decorator-based rate limiter for Flask views."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, TypeAlias, TypeVar, cast

from flask import current_app, g, request
from throttled.constants import RateLimiterType
from throttled.exceptions import StoreUnavailableError
from throttled.rate_limiter import validate_key_prefix
from throttled.store import MemoryStore
from throttled.throttled import Throttled
from werkzeug.exceptions import ServiceUnavailable

from .exceptions import RateLimitExceededError
from .headers import (
    _DEFAULT_HEADER_POLICY,
    _G_KEY,
    RateLimitContext,
    _inject_rate_limit_headers,
)
from .keys import KeyParts, compose_key

if TYPE_CHECKING:
    from collections.abc import Sequence

    from flask import Flask, Response
    from throttled.hooks import Hook
    from throttled.rate_limiter import Quota, RateLimitResult
    from throttled.store import BaseStore
    from throttled.types import RateLimiterTypeT


P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

#: Zero-argument callable that returns the principal key for the
#: active request. Reads the thread-local ``flask.request`` proxy
#: (Flask convention; compare flask-limiter's ``key_func``).
KeyFunc: TypeAlias = Callable[[], str]

_DEFAULT_PRINCIPAL = "__throttled_global_principal__"

_EXTENSION_KEY = "throttled"

_STORE_UNAVAILABLE_DETAIL = "Rate limit store unavailable"
_STORE_UNAVAILABLE_LOG_MSG = "rate limit store unavailable"


def _registered_handler_types(app: "Flask") -> list[type[Exception]]:
    """Return every exception class with a registered errorhandler.

    ``app.error_handler_spec`` is a three-level mapping::

        {blueprint_name | None: {status_code | None: {exc_class: handler}}}

    Only the active request's blueprint chain (``request.blueprints``)
    and app-level (``None``) registrations can actually handle an
    exception raised by this request, mimicking Flask's own
    ``_find_error_handler`` dispatch scope.
    """
    registered: list[type[Exception]] = []
    for scope in (*request.blueprints, None):
        blueprint_spec = app.error_handler_spec.get(scope)
        if blueprint_spec is None:
            continue
        for code_spec in blueprint_spec.values():
            registered.extend(code_spec.keys())

    return registered


def _has_error_handler(app: "Flask", exc_type: type[Exception]) -> bool:
    """Mirror Flask's MRO-based handler lookup, excluding ``Exception``.

    A catch-all ``Exception`` handler is not an intentional opt-in for
    store outages, so it does not preempt the default 503. App-level
    and blueprint-level registrations both count.
    """
    return any(
        registered is not Exception and issubclass(exc_type, registered)
        for registered in _registered_handler_types(app)
    )


def _default_key_func() -> str:
    """Return the built-in shared principal for omitted ``key_func``."""
    return _DEFAULT_PRINCIPAL


def _route_template() -> str:
    """Return the matched route rule for the active request.

    ``request.url_rule.rule`` (e.g. ``"/api/users/<int:user_id>"``)
    already includes any blueprint ``url_prefix``, so two blueprints
    exposing the same child path do not collide into one rate-limit
    key, and concrete path-parameter values share one key.
    """
    url_rule = request.url_rule
    return url_rule.rule if url_rule is not None else request.path


def _apply_rate_limit_headers(response: "Response") -> "Response":
    """``after_request`` hook adding missing ``RateLimit-*`` headers.

    Pops the :class:`RateLimitContext` stored on ``flask.g`` by the
    :meth:`Limiter.limit` decorator wrapper. Existing response headers
    take precedence, preserving those rendered by a 429 exception. On
    success, stacked limiters leave the innermost context in the slot.

    Responses from views that did not run
    under a rate-limit check pass through untouched.
    """
    context: RateLimitContext | None = g.pop(_G_KEY, None)
    if context is not None:
        headers: dict[str, str] = {}
        _inject_rate_limit_headers(headers, context, include_retry_after=False)
        for name, value in headers.items():
            response.headers.setdefault(name, value)

    return response


class Limiter:
    """Decorator-based rate limiter for Flask views.

    :param quota: Required. Default quota for all decorated views.
        Accepts a :class:`Quota` instance or a DSL string such as
        ``"100/m"`` or ``"10/s burst 20"``
        (see :mod:`throttled.rate_limiter.quota_parser`).
    :param app: Optional Flask app for eager initialization. When
        ``None``, call :meth:`init_app` later (application factory
        pattern).
    :param store: Storage backend. Defaults to
        :class:`~throttled.store.MemoryStore` when ``None``.
    :param using: Rate-limit algorithm. Defaults to ``token_bucket`` to
        match :class:`throttled.throttled.Throttled`.
    :param key_func: Optional zero-argument callable that returns the
        principal key from the active request context. When ``None``,
        all callers share one quota bucket per method and route.
    :param key_prefix: Optional storage key namespace. Must be a non-blank
        string that does not start or end with ``:``. ``None`` keeps the
        default namespace.
    :param hooks: Optional hooks forwarded to the internal
        :class:`~throttled.throttled.Throttled` instances.
    """

    def __init__(
        self,
        quota: "Quota | str",
        *,
        app: "Flask | None" = None,
        store: "BaseStore | None" = None,
        using: "RateLimiterTypeT" = RateLimiterType.TOKEN_BUCKET.value,
        key_func: KeyFunc | None = None,
        key_prefix: str | None = None,
        hooks: "Sequence[Hook] | None" = None,
    ) -> None:
        if quota is None:
            raise TypeError("Limiter requires an explicit quota.")
        if key_prefix is not None:
            validate_key_prefix(key_prefix)

        self._default_quota: Quota | str = quota
        self._store: BaseStore = store or MemoryStore()
        self._using: RateLimiterTypeT = using
        self._key_func: KeyFunc = key_func or _default_key_func
        self._key_prefix: str | None = key_prefix
        self._hooks: Sequence[Hook] | None = hooks

        if app is not None:
            self.init_app(app)

    def init_app(self, app: "Flask") -> None:
        """Register the ``after_request`` header hook on ``app``.

        Idempotent per limiter, and the hook is registered once per
        app no matter how many limiters attach to it. Follows the
        Flask extension convention, so both eager
        (``Limiter(quota, app=app)``) and factory-pattern
        (``limiter.init_app(app)``) initialization work.
        """
        limiters: set[Limiter] = app.extensions.setdefault(_EXTENSION_KEY, set())
        if self in limiters:
            return
        if not limiters:
            app.after_request(_apply_rate_limit_headers)

        limiters.add(self)

    def limit(
        self,
        quota: "Quota | str | None" = None,
        *,
        key_func: KeyFunc | None = None,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Decorate a view function with rate limiting.

        Apply below the route registration so the wrapped view is what
        Flask registers::

            @app.get("/items")
            @limiter.limit()
            def list_items(): ...

        :param quota: Optional per-view quota override. Falls back to
            the instance default when ``None``.
        :param key_func: Optional per-view key function override.
            Falls back to the instance default when ``None``.
        """
        resolved_quota: Quota | str = quota if quota is not None else self._default_quota
        resolved_key_func: KeyFunc = key_func if key_func is not None else self._key_func
        throttled: Throttled = Throttled(
            quota=resolved_quota,
            using=self._using,
            store=self._store,
            key_prefix=self._key_prefix,
            hooks=self._hooks,
        )

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    result: RateLimitResult = _check(
                        throttled=throttled,
                        key_func=resolved_key_func,
                    )
                except StoreUnavailableError as exc:
                    if _has_error_handler(current_app, type(exc)):
                        raise
                    logger.exception(_STORE_UNAVAILABLE_LOG_MSG)
                    raise ServiceUnavailable(_STORE_UNAVAILABLE_DETAIL) from exc
                context: RateLimitContext = RateLimitContext(
                    result=result,
                    headers=_DEFAULT_HEADER_POLICY,
                )
                if result.limited:
                    logger.debug(
                        "Rate limit exceeded: %s %s",
                        request.method,
                        _route_template(),
                    )
                    raise RateLimitExceededError(context)

                logger.debug(
                    "Rate limit passed: %s %s, remaining=%s",
                    request.method,
                    _route_template(),
                    result.state.remaining if result.state else "unknown",
                )
                setattr(g, _G_KEY, context)
                # ensure_sync returns Any; the wrapped view still
                # produces R on the sync path Flask executes.
                return cast("R", current_app.ensure_sync(func)(*args, **kwargs))

            return wrapper

        return decorator


def _check(*, throttled: Throttled, key_func: KeyFunc) -> "RateLimitResult":
    """Run the rate-limit check for the active request.

    :param throttled: The per-view ``Throttled`` instance.
    :param key_func: Zero-argument callable that extracts the principal
        from the active request context.
    :returns: The :class:`RateLimitResult`. Caller inspects
        ``result.limited`` to decide between 429 and success.
    """
    key: str = compose_key(
        KeyParts(
            method=request.method,
            route=_route_template(),
            principal=key_func(),
        )
    )
    return throttled.limit(key=key)
