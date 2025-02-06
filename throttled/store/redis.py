from typing import Any, Dict, Optional, Type, Union

from redis import Redis

from ..constants import StoreType
from ..exceptions import DataError
from ..types import KeyT, StoreDictValueT, StoreValueT
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
        return int(self._backend.get_client().ttl(key))

    def expire(self, key: KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().expire(key, timeout)

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().set(key, value, ex=timeout)

    @classmethod
    def _format_value(cls, value: StoreValueT) -> StoreValueT:
        float_value: float = float(value)
        if float_value.is_integer():
            return int(float_value)
        return float_value

    @classmethod
    def _format_key(cls, key: Union[bytes, str]) -> KeyT:
        if isinstance(key, bytes):
            return key.decode("utf-8")
        return key

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        value: Optional[StoreValueT] = self._backend.get_client().get(key)
        if value is None:
            return None

        return self._format_value(value)

    def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")
        self._backend.get_client().hset(name, key, value, mapping)

    def hgetall(self, name: KeyT) -> StoreDictValueT:
        kv: Dict[KeyT, Optional[StoreValueT]] = self._backend.get_client().hgetall(name)
        return {self._format_key(k): self._format_value(v) for k, v in kv.items()}

    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        return action_cls(backend=self._backend)
