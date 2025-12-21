from typing import Any

from ... import constants, store, utils
from ...exceptions import DataError
from ...types import AtomicActionP, KeyT, StoreDictValueT, StoreValueT
from . import BaseStore


class RedisStoreBackend(store.RedisStoreBackend):
    """Backend for Async RedisStore."""

    @classmethod
    def _set_options(cls, options: dict[str, Any]):
        super()._set_options(options)
        options.setdefault("REUSE_CONNECTION", False)
        options.setdefault("REDIS_CLIENT_CLASS", "redis.asyncio.Redis")
        options.setdefault("PARSER_CLASS", "redis.asyncio.connection.DefaultParser")

    @classmethod
    def _set_sentinel_options(cls, options: dict[str, Any]):
        super()._set_sentinel_options(options)
        options.setdefault("SENTINEL_CLASS", "redis.asyncio.Sentinel")
        options.setdefault(
            "CONNECTION_POOL_CLASS", "redis.asyncio.SentinelConnectionPool"
        )

    @classmethod
    def _set_standalone_options(cls, options: dict[str, Any]):
        super()._set_standalone_options(options)
        options.setdefault("CONNECTION_POOL_CLASS", "redis.asyncio.ConnectionPool")


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = constants.StoreType.REDIS.value

    _BACKEND_CLASS: type[RedisStoreBackend] = RedisStoreBackend

    def __init__(self, server: str | None = None, options: dict[str, Any] | None = None):
        super().__init__(server, options)
        self._backend: RedisStoreBackend = self._BACKEND_CLASS(server, options)

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

    async def get(self, key: KeyT) -> StoreValueT | None:
        value: StoreValueT | None = await self._backend.get_client().get(key)
        if value is None:
            return None

        return utils.format_value(value)

    async def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")
        await self._backend.get_client().hset(name, key, value, mapping)

    async def hgetall(self, name: KeyT) -> StoreDictValueT:
        return utils.format_kv(await self._backend.get_client().hgetall(name))

    def make_atomic(self, action_cls: type[AtomicActionP]) -> AtomicActionP:
        return action_cls(backend=self._backend)
