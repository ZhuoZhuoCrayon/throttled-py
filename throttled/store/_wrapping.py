import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, Final, NoReturn, Protocol, TypeAlias, cast

from .. import types
from ..exceptions import StoreUnavailableError

StoreBaseExceptions: TypeAlias = tuple[type[Exception], ...]
WrapperFactory: TypeAlias = Callable[[Callable[..., Any]], Callable[..., Any]]

_STORE_WRAPPED_ATTR: Final = "__store_unavailable_wrapped__"


class _HasStoreBackendP(Protocol):
    _backend: types.StoreBackendP


def wrap_class_methods(cls: type[object], method_names: tuple[str, ...]) -> None:
    """Wrap specified methods declared by concrete subclasses."""
    for method_name in method_names:
        _wrap_class_method(cls, method_name, _wrap_method)


def _wrap_class_method(
    cls: type[object], method_name: str, wrapper_factory: WrapperFactory
) -> None:
    # Abstract base classes are just declaration points. Wait until a concrete
    # subclass is created, then wrap the inherited implementation on that class.
    if inspect.isabstract(cls):
        return

    method = getattr(cls, method_name, None)
    if method is None or getattr(method, _STORE_WRAPPED_ATTR, False):
        return

    # Mark the wrapper itself so repeated subclass initialization does not wrap
    # the same callable multiple times.
    wrapped = wrapper_factory(cast("Callable[..., Any]", method))
    setattr(wrapped, _STORE_WRAPPED_ATTR, True)
    setattr(cls, method_name, wrapped)


def _raise_store_unavailable(exc: Exception) -> NoReturn:
    raise StoreUnavailableError("Store backend is unavailable.") from exc


def _wrap_method(method: Callable[..., Any]) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(method):

        @wraps(method)
        async def async_wrapped(
            self: _HasStoreBackendP, *args: object, **kwargs: object
        ) -> object:
            # Fast path for backends that do not define transport-level
            # availability exceptions.
            if not self._backend.base_exceptions:
                return await method(self, *args, **kwargs)

            try:
                return await method(self, *args, **kwargs)
            except self._backend.base_exceptions as exc:
                _raise_store_unavailable(exc)

        return async_wrapped

    @wraps(method)
    def wrapped(self: _HasStoreBackendP, *args: object, **kwargs: object) -> object:
        # Keep the sync path aligned with the async branch above.
        if not self._backend.base_exceptions:
            return method(self, *args, **kwargs)

        try:
            return method(self, *args, **kwargs)
        except self._backend.base_exceptions as exc:
            _raise_store_unavailable(exc)

    return wrapped
