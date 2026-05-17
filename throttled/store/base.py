import abc
from collections.abc import Sequence
from typing import Any

from .. import exceptions, types
from .wraps import AutoWrapMethodsMixin


class BaseStoreBackend:
    """Base class for store backends with shared configuration state."""

    # Base exceptions that may be raised by the backend,
    # used for error handling in stores.
    base_exceptions: tuple[type[Exception], ...] = ()

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        self.server: str | None = server
        self.options: dict[str, Any] = options or {}


class BaseAtomicAction(AutoWrapMethodsMixin, abc.ABC):
    """Abstract class for all atomic actions performed by a store backend."""

    TYPE: types.AtomicActionTypeT = ""
    STORE_TYPE: str = ""

    _WRAPPED_METHOD_NAMES: tuple[str, ...] = ("do",)

    def __init__(self, backend: BaseStoreBackend) -> None:
        self._backend = backend

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


class StoreSpec:
    """Shared identity and wrapped-command declaration for stores."""

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


class StoreValidationLogic:
    """Pure validation helpers shared by sync and async stores."""

    @classmethod
    def _validate_timeout(cls, timeout: int) -> None:
        """Validate the timeout.

        :param timeout: The timeout in seconds.
        :raise: DataError.
        """
        if isinstance(timeout, int) and timeout > 0:
            return

        raise exceptions.DataError(
            f"Invalid timeout: {timeout}, Must be an integer greater than 0."
        )


class BaseStore(StoreSpec, StoreValidationLogic, AutoWrapMethodsMixin, abc.ABC):
    """Abstract class for all stores."""

    _BACKEND_CLASS: type[BaseStoreBackend] = BaseStoreBackend
    _backend: BaseStoreBackend

    def __init__(
        self,
        server: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the store and its backend.

        :param server: Store backend connection string.
        :param options: Store backend options.
        """
        self.server: str | None = server
        self.options: dict[str, Any] = options or {}
        self._backend = self._BACKEND_CLASS(server, options)

    def make_atomic(self, action_cls: type[BaseAtomicAction]) -> BaseAtomicAction:
        """Create an AtomicAction instance bound to the concrete store backend."""
        return action_cls(backend=self._backend)

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
