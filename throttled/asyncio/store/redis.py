import abc
from typing import TYPE_CHECKING, Any

from ... import constants, exceptions, store, types, utils
from .base import BaseAtomicAction, BaseStore

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


class RedisStoreBackend(store.BaseRedisStoreBackend[types.AsyncRedisClientP]):
    """Backend for Async RedisStore."""

    @classmethod
    def _set_options(cls, options: dict[str, Any]) -> None:
        super()._set_options(options)
        options.setdefault("REUSE_CONNECTION", False)
        options.setdefault("REDIS_CLIENT_CLASS", "redis.asyncio.Redis")
        options.setdefault("PARSER_CLASS", "redis.asyncio.connection.DefaultParser")

    @classmethod
    def _set_sentinel_options(cls, options: dict[str, Any]) -> None:
        super()._set_sentinel_options(options)
        options.setdefault("SENTINEL_CLASS", "redis.asyncio.Sentinel")
        options.setdefault(
            "CONNECTION_POOL_CLASS", "redis.asyncio.SentinelConnectionPool"
        )

    @classmethod
    def _set_standalone_options(cls, options: dict[str, Any]) -> None:
        super()._set_standalone_options(options)
        options.setdefault("CONNECTION_POOL_CLASS", "redis.asyncio.ConnectionPool")

    @classmethod
    def _set_cluster_options(cls, options: dict[str, Any]) -> None:
        super()._set_cluster_options(options)
        options.setdefault(
            "REDIS_CLIENT_CLASS",
            "redis.asyncio.cluster.RedisCluster",
        )
        options.setdefault(
            "REDIS_CLUSTER_NODE_CLASS", "redis.asyncio.cluster.ClusterNode"
        )


class BaseRedisAtomicAction(BaseAtomicAction, abc.ABC):
    """Base class for async Redis atomic actions bound to RedisStoreBackend."""

    STORE_TYPE: str = constants.StoreType.REDIS.value
    _backend: RedisStoreBackend

    def _register_script(self, scripts: str) -> "AsyncScript":
        return self._backend.get_client().register_script(scripts)


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = constants.StoreType.REDIS.value

    _BACKEND_CLASS: type[RedisStoreBackend] = RedisStoreBackend
    _backend: RedisStoreBackend

    async def exists(self, key: types.KeyT) -> bool:
        return bool(await self._backend.get_client().exists(key))

    async def ttl(self, key: types.KeyT) -> int:
        return int(await self._backend.get_client().ttl(key))

    async def expire(self, key: types.KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        await self._backend.get_client().expire(key, timeout)

    async def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        await self._backend.get_client().set(key, value, ex=timeout)

    async def get(self, key: types.KeyT) -> types.StoreValueT | None:
        value: types.StoreValueT | None = await self._backend.get_client().get(key)
        if value is None:
            return None

        return utils.format_value(value)

    async def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        if key is None and not mapping:
            raise exceptions.DataError("hset must with key value pairs")
        await self._backend.get_client().hset(name, key, value, mapping)

    async def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        return utils.format_kv(await self._backend.get_client().hgetall(name))
