from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from ...constants import StoreType
from ...exceptions import DataError
from ...store.redis import RedisFormatMixin
from ...store.redis_pool import BaseConnectionFactory, get_connection_factory
from ...types import KeyT, StoreDictValueT, StoreValueT
from .base import BaseAtomicAction, BaseStore, BaseStoreBackend

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisStoreBackend(BaseStoreBackend):
    """Backend for Async RedisStore."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)

        self._client: Optional[Redis] = None
        self.options.setdefault("CONNECTION_POOL_CLASS", "redis.asyncio.ConnectionPool")
        self.options.setdefault("REDIS_CLIENT_CLASS", "redis.asyncio.Redis")
        self.options.setdefault("PARSER_CLASS", "redis.asyncio.connection.DefaultParser")

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


class RedisStore(RedisFormatMixin, BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = StoreType.REDIS.value

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        self._backend: RedisStoreBackend = RedisStoreBackend(server, options)

    async def exists(self, key: KeyT) -> bool:
        return bool(await self._backend.get_client().exists(key))

    async def ttl(self, key: KeyT) -> int:
        return int(await self._backend.get_client().ttl(key))

    async def expire(self, key: KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        await self._backend.get_client().expire(key, timeout)

    async def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        await self._backend.get_client().set(key, value, ex=timeout)

    async def get(self, key: KeyT) -> Optional[StoreValueT]:
        value: Optional[StoreValueT] = await self._backend.get_client().get(key)
        if value is None:
            return None

        return self._format_value(value)

    async def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")
        await self._backend.get_client().hset(name, key, value, mapping)

    async def hgetall(self, name: KeyT) -> StoreDictValueT:
        return self._format_kv(await self._backend.get_client().hgetall(name))

    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        return action_cls(backend=self._backend)
