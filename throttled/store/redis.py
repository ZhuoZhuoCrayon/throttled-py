from typing import Any, Dict, Optional, Type

from redis import Redis

from ..constants import StoreType
from ..exceptions import DataError
from ..types import KeyT, StoreValueT
from .base import BaseAtomicAction, BaseStore, BaseStoreBackend
from .redis_pool import BaseConnectionFactory, get_connection_factory


class RedisStoreBackend(BaseStoreBackend):
    """Backend for Redis store."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)

        self._client: Optional[Redis] = None

        connection_factory_cls_path: Optional[str] = self.options.get(
            "CONNECTION_FACTORY_CLASS"
        )
        self._connection_factory: BaseConnectionFactory = get_connection_factory(
            connection_factory_cls_path, self.options
        )

    def get_client(self) -> Redis:
        if self._client is None:
            self._client = self._connection_factory.connect(self.server)
        return self._client


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = StoreType.REDIS.value

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        self._backend: RedisStoreBackend = RedisStoreBackend(server, options)

    def exists(self, key: KeyT) -> bool:
        return bool(self._backend.get_client().exists(key))

    def ttl(self, key: KeyT) -> int:
        ttl: int = int(self._backend.get_client().ttl(key))
        if ttl == -2:
            raise DataError("Key not found: {key}".format(key=key))
        return ttl

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().set(key, value, ex=timeout)

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        value: Optional[StoreValueT] = self._backend.get_client().get(key)
        if value is None:
            return None

        float_value: float = float(value)
        if float_value.is_integer():
            return int(float_value)
        return float_value

    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        return action_cls(backend=self._backend)
