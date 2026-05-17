import abc
from collections.abc import Sequence
from typing import Any

from ... import types
from ...store.base import BaseStoreBackend, StoreSpec, StoreValidationLogic
from ...store.wraps import AutoWrapMethodsMixin

__all__ = ["BaseAtomicAction", "BaseStore"]


class BaseAtomicAction(AutoWrapMethodsMixin, abc.ABC):
    """Abstract class for all async atomic actions performed by a store backend."""

    TYPE: types.AtomicActionTypeT = ""
    STORE_TYPE: str = ""

    _WRAPPED_METHOD_NAMES: tuple[str, ...] = ("do",)

    def __init__(self, backend: BaseStoreBackend) -> None:
        self._backend = backend

    @abc.abstractmethod
    async def do(
        self, keys: Sequence[types.KeyT], args: Sequence[types.StoreValueT] | None
    ) -> tuple[int | float, ...]:
        """Execute the AtomicAction on the specified keys with optional arguments.

        :param keys: A sequence of keys.
        :param args: Optional sequence of arguments.
        :return: The result of the AtomicAction.
        """
        raise NotImplementedError


class BaseStore(StoreSpec, StoreValidationLogic, AutoWrapMethodsMixin, abc.ABC):
    """Abstract class for all async stores."""

    _BACKEND_CLASS: type[BaseStoreBackend] = BaseStoreBackend
    _backend: BaseStoreBackend

    def __init__(
        self,
        server: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the async store and its backend.

        :param server: Store backend connection string.
        :param options: Store backend options.
            For backend-specific configuration details, see
            :doc:`/advance_usage/store-configuration`.
        """
        self.server: str | None = server
        self.options: dict[str, Any] = options or {}
        self._backend = self._BACKEND_CLASS(server, options)

    def make_atomic(self, action_cls: type[BaseAtomicAction]) -> BaseAtomicAction:
        """Create an async AtomicAction instance bound to the concrete backend."""
        return action_cls(backend=self._backend)

    @abc.abstractmethod
    async def exists(self, key: types.KeyT) -> bool:
        """Check if the specified key exists.

        :param key: The key to check.
        :return: True if the specified key exists, False otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def ttl(self, key: types.KeyT) -> int:
        """Returns the number of seconds until the specified key will expire.

        :param key: The key to check.
        :raise: DataError.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def expire(self, key: types.KeyT, timeout: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        """Set a value for the specified key with specified timeout.

        :param key: The key to set.
        :param value: The value to set.
        :param timeout: The timeout in seconds.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: types.KeyT) -> types.StoreValueT | None:
        """Get a value for the specified key.

        :param key: The key for which to get a value.
        :return: The value for the specified key, or None if it does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def hset(
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
    async def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        raise NotImplementedError
