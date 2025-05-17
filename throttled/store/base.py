import abc
from typing import Any, Dict, Optional, Sequence, Type

from ..exceptions import DataError, SetUpError
from ..types import KeyT, StoreDictValueT, StoreValueT


class BaseStoreBackend(abc.ABC):
    """Abstract class for all store backends."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ) -> None:
        self.server: Optional[str] = server
        self.options: Dict[str, Any] = options or {}

    @abc.abstractmethod
    def get_client(self) -> Any:
        raise NotImplementedError


class BaseAtomicActionMixin:
    """Mixin class for AtomicAction.

    This class provides shared logic for both sync and async implementations of
    AtomicAction. It includes type checking and helper methods that ensure
    compatibility between store types.
    """

    # TYPE is the identifier of AtomicAction, must be unique under STORE_TYPE.
    TYPE: str = ""
    # STORE_TYPE is the expected type of store with which AtomicAction is compatible.
    STORE_TYPE: str = ""

    def __init__(self, backend: BaseStoreBackend):
        pass

    @classmethod
    def match_or_raise(cls, store_type: str) -> None:
        """Ensure the store type matches the expected type, or raise SetUpError.
        :param store_type: The type of the store to be checked.
        :raise: SetUpError
        """
        if cls.STORE_TYPE != store_type:
            raise SetUpError(
                "Unmatched store type: expected {expected} but got {got}".format(
                    expected=cls.STORE_TYPE, got=store_type
                )
            )


class BaseAtomicAction(BaseAtomicActionMixin, abc.ABC):
    """Abstract class for all atomic actions performed by a store backend."""

    @abc.abstractmethod
    def do(self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]) -> Any:
        """Execute the AtomicAction on the specified keys with optional arguments.
        :param keys: A sequence of keys.
        :param args: Optional sequence of arguments.
        :return: Any: The result of the AtomicAction.
        """
        raise NotImplementedError


class BaseStoreMixin:
    """Mixin class for async / sync BaseStore."""

    # TYPE is a unique identifier for the type of store.
    TYPE: str = ""

    @classmethod
    def _validate_timeout(cls, timeout: int) -> None:
        """Validate the timeout.
        :param timeout: The timeout in seconds.
        :raise: DataError
        """
        if isinstance(timeout, int) and timeout > 0:
            return

        raise DataError(
            "Invalid timeout: {timeout}, Must be an integer greater "
            "than 0.".format(timeout=timeout)
        )

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        pass


class BaseStore(BaseStoreMixin, abc.ABC):
    """Abstract class for all stores."""

    @abc.abstractmethod
    def exists(self, key: KeyT) -> bool:
        """Check if the specified key exists.
        :param key: The key to check.
        :return: True if the specified key exists, False otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def ttl(self, key: KeyT) -> int:
        """Returns the number of seconds until the specified key will expire.
        :param key: The key to check.
        :raise: DataError
        """
        raise NotImplementedError

    @abc.abstractmethod
    def expire(self, key: KeyT, timeout: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        """Set a value for the specified key with specified timeout.
        :param key: The key to set.
        :param value: The value to set.
        :param timeout: The timeout in seconds.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, key: KeyT) -> Optional[StoreValueT]:
        """Get a value for the specified key.
        :param key: The key for which to get a value.
        :return: The value for the specified key, or None if it does not exist.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def hset(
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
    def hgetall(self, name: KeyT) -> StoreDictValueT:
        raise NotImplementedError

    @abc.abstractmethod
    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        """Create an instance of an AtomicAction for this store.
        :param action_cls: The class of the AtomicAction.
        :return: The AtomicAction instance.
        """
        raise NotImplementedError
