from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from ..constants import StoreType
from ..exceptions import DataError
from ..types import AtomicActionP, KeyT, StoreDictValueT, StoreValueT
from ..utils import format_kv, format_value
from .base import BaseStore, BaseStoreBackend
from .redis_pool import BaseConnectionFactory, get_connection_factory

if TYPE_CHECKING:
    import redis
    import redis.asyncio as aioredis

    Redis = Union[redis.Redis, aioredis.Redis]


class RedisStoreBackend(BaseStoreBackend):
    """Backend for Redis store."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)

        self._client: Optional["Redis"] = None

        connection_factory_cls_path: Optional[str] = self.options.get(
            "CONNECTION_FACTORY_CLASS"
        )

        self._connection_factory: BaseConnectionFactory = get_connection_factory(
            connection_factory_cls_path, self.options
        )

    def get_client(self) -> "Redis":
        if self._client is None:
            self._client = self._connection_factory.connect(self.server)
        return self._client


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = StoreType.REDIS.value

    _BACKEND_CLASS: Type[RedisStoreBackend] = RedisStoreBackend

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)
        self._backend: RedisStoreBackend = self._BACKEND_CLASS(server, options)

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

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        value: Optional[StoreValueT] = self._backend.get_client().get(key)
        if value is None:
            return None

        return format_value(value)

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
        return format_kv(self._backend.get_client().hgetall(name))

    def make_atomic(self, action_cls: Type[AtomicActionP]) -> AtomicActionP:
        return action_cls(backend=self._backend)
