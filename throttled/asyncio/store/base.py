import abc
from collections.abc import Callable, Sequence
from typing import Any, Generic, TypeVar

from ... import store, types

__all__ = ["BaseAtomicAction", "BaseStore"]

_BackendT = TypeVar("_BackendT", bound=store.BaseStoreBackend[Any])
_ActionT = TypeVar("_ActionT")


class BaseAtomicAction(
    store.BaseAtomicActionMixin[_BackendT], abc.ABC, Generic[_BackendT]
):
    """Abstract class for all async atomic actions performed by a store backend."""

    @abc.abstractmethod
    async def do(
        self,
        keys: Sequence[types.KeyT],
        args: Sequence[types.StoreValueT] | None,
    ) -> tuple[int | float, ...]:
        """Execute the AtomicAction on the specified keys with optional arguments.

        :param keys: A sequence of keys.
        :param args: Optional sequence of arguments.
        :return: The result of the AtomicAction.
        """
        raise NotImplementedError


class BaseStore(store.BaseStoreMixin, abc.ABC, Generic[_BackendT]):
    """Abstract class for all async stores."""

    _backend: _BackendT

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

    def make_atomic(self, action_cls: type[_ActionT]) -> _ActionT:
        """Create an instance of an async AtomicAction bound to the backend."""
        factory: Callable[..., _ActionT] = action_cls
        return factory(backend=self._backend)
