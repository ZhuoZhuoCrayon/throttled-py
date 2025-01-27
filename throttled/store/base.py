import abc
from typing import Any, Optional, Sequence, Type

from ..exceptions import DataError, SetUpError
from ..typing import KeyT, StoreValueT


class BaseStoreBackend(abc.ABC):
    """Abstract class for all store backends."""

    pass


class BaseAtomicAction(abc.ABC):
    """Abstract class for all atomic actions performed by a store backend."""

    # TYPE is the identifier of AtomicAction, must be unique under STORE_TYPE.
    TYPE: str = ""
    # STORE_TYPE is the expected type of store with which AtomicAction is compatible.
    STORE_TYPE: str = ""

    @abc.abstractmethod
    def __init__(self, backend: BaseStoreBackend):
        raise NotImplementedError

    @abc.abstractmethod
    def do(self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]) -> Any:
        """Execute the AtomicAction on the specified keys with optional arguments.
        :param keys: A sequence of keys.
        :param args: Optional sequence of arguments.
        :return: Any: The result of the AtomicAction.
        """
        raise NotImplementedError

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


class BaseStore(abc.ABC):
    """Abstract class for all stores."""

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
    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        """Create an instance of an AtomicAction for this store.
        :param action_cls: The class of the AtomicAction.
        :return: The AtomicAction instance.
        """
        raise NotImplementedError
