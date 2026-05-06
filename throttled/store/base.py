import abc
from collections.abc import Callable, Sequence
from typing import Any, Generic, TypeVar

from .. import types
from ..exceptions import DataError
from ._wrapping import wrap_class_methods

_ClientT = TypeVar("_ClientT", bound=object)

_BackendT = TypeVar("_BackendT", bound=types.StoreBackendP)

_ActionT = TypeVar("_ActionT")


class BaseStoreBackend(abc.ABC, Generic[_ClientT]):
    """Abstract class for all store backends."""

    # Base exceptions that may be raised by the backend,
    # used for error handling in stores.
    base_exceptions: tuple[type[Exception], ...] = ()

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        self.server: str | None = server
        self.options: dict[str, Any] = options or {}

    @abc.abstractmethod
    def get_client(self) -> _ClientT:
        """Return the underlying client."""
        raise NotImplementedError


class AutoWrapMethodsMixin:
    """Mixin class for auto-wrapping subclass-declared methods.

    Subclasses declare ``_WRAPPED_METHOD_NAMES`` to describe which methods should
    be wrapped once the class becomes concrete.
    """

    # List of method names to wrap, declared by concrete subclasses.
    _WRAPPED_METHOD_NAMES: tuple[str, ...] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        wrap_class_methods(cls, cls._WRAPPED_METHOD_NAMES)


class BaseAtomicActionMixin(AutoWrapMethodsMixin, Generic[_BackendT]):
    """Mixin class for AtomicAction."""

    # Identifier of AtomicAction, must be unique under STORE_TYPE.
    TYPE: types.AtomicActionTypeT = ""
    # Expected store type with which AtomicAction is compatible.
    STORE_TYPE: str = ""

    _WRAPPED_METHOD_NAMES: tuple[str, ...] = ("do",)

    def __init__(self, backend: _BackendT) -> None:
        self._backend: _BackendT = backend


class BaseAtomicAction(BaseAtomicActionMixin[_BackendT], abc.ABC, Generic[_BackendT]):
    """Abstract class for all atomic actions performed by a store backend."""

    @abc.abstractmethod
    def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int | float, ...]:
        """Execute the AtomicAction on the specified keys with optional arguments.

        :param keys: A sequence of keys.
        :param args: Optional sequence of arguments.
        :return: Any: The result of the AtomicAction.
        """
        raise NotImplementedError


class BaseStoreMixin(AutoWrapMethodsMixin):
    """Mixin class for async / sync BaseStore."""

    # Unique identifier for the type of store.
    TYPE: str = ""

    _WRAPPED_METHOD_NAMES: tuple[str, ...] = (
        "exists",
        "ttl",
        "expire",
        "set",
        "get",
        "hset",
        "hgetall",
        "make_atomic",
    )

    @classmethod
    def _validate_timeout(cls, timeout: int) -> None:
        """Validate the timeout.

        :param timeout: The timeout in seconds.
        :raise: DataError.
        """
        if isinstance(timeout, int) and timeout > 0:
            return

        raise DataError(
            f"Invalid timeout: {timeout}, Must be an integer greater than 0."
        )

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        self.server: str | None = server
        self.options: dict[str, Any] = options or {}


class BaseStore(BaseStoreMixin, abc.ABC, Generic[_BackendT]):
    """Abstract class for all stores."""

    _backend: _BackendT

    @abc.abstractmethod
    def exists(self, key: types.KeyT) -> bool:
        """Check if the specified key exists.

        :param key: The key to check.
        :return: ``True`` if the specified key exists, ``False`` otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def ttl(self, key: types.KeyT) -> int:
        """Returns the number of seconds until the specified key will expire.

        :param key: The key to check.
        :raise: :class:`throttled.exceptions.DataError` if the key does not exist
            or is not set.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def expire(self, key: types.KeyT, timeout: int) -> None:
        """Set the expiration time for the specified key.

        :param key: The key to set the expiration for.
        :param timeout: The timeout in seconds.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        """Set a value for the specified key with specified timeout.

        :param key: The key to set.
        :param value: The value to set.
        :param timeout: The timeout in seconds.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, key: types.KeyT) -> types.StoreValueT | None:
        """Get a value for the specified key.

        :param key: The key for which to get a value.
        :return: The value for the specified key, or None if it does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        """Set a value for the specified key in the specified hash.

        :param name: The name of the hash.
        :param key: The key in the hash.
        :param value: The value to set.
        :param mapping: A dictionary of key-value pairs to set.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        raise NotImplementedError

    def make_atomic(self, action_cls: type[_ActionT]) -> _ActionT:
        """Create an instance of an AtomicAction bound to this store's backend."""
        factory: Callable[..., _ActionT] = action_cls
        return factory(backend=self._backend)
