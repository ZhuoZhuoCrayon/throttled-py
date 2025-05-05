import abc
from typing import Any, Optional, Sequence, Type

from ...store.base import BaseAtomicActionMixin, BaseStoreBackendMixin, BaseStoreMixin
from ...types import KeyT, StoreDictValueT, StoreValueT


class BaseStoreBackend(BaseStoreBackendMixin, abc.ABC):
    """Abstract class for all async store backends."""

    @abc.abstractmethod
    async def get_client(self) -> Any:
        raise NotImplementedError


class BaseAtomicAction(BaseAtomicActionMixin, abc.ABC):
    """Abstract class for all async atomic actions performed by a store backend."""

    @abc.abstractmethod
    def __init__(self, backend: BaseStoreBackend):
        raise NotImplementedError

    @abc.abstractmethod
    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Any:
        """Execute the AtomicAction on the specified keys with optional arguments.
        :param keys: A sequence of keys.
        :param args: Optional sequence of arguments.
        :return: Any: The result of the AtomicAction.
        """
        raise NotImplementedError


class BaseStore(BaseStoreMixin, abc.ABC):
    """Abstract class for all async stores."""

    @abc.abstractmethod
    async def exists(self, key: KeyT) -> bool:
        """Check if the specified key exists.
        :param key: The key to check.
        :return: True if the specified key exists, False otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def ttl(self, key: KeyT) -> int:
        """Returns the number of seconds until the specified key will expire.
        :param key: The key to check.
        :raise: DataError
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def expire(self, key: KeyT, timeout: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        """Set a value for the specified key with specified timeout.
        :param key: The key to set.
        :param value: The value to set.
        :param timeout: The timeout in seconds.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: KeyT) -> Optional[StoreValueT]:
        """Get a value for the specified key.
        :param key: The key for which to get a value.
        :return: The value for the specified key, or None if it does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        """Set a value for the specified key in the specified hash.
        :param name: The name of the hash.
        :param key: The key in the hash.
        :param value: The value to set.
        :param mapping: A dictionary of key-value pairs to set.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def hgetall(self, name: KeyT) -> StoreDictValueT:
        raise NotImplementedError

    @abc.abstractmethod
    async def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        """Create an instance of an AtomicAction for this store.
        :param action_cls: The class of the AtomicAction.
        :return: The AtomicAction instance.
        """
        raise NotImplementedError
