from typing import Any, Dict, Optional, Type

from ... import constants, store, utils
from ...exceptions import DataError
from ...types import AtomicActionP, KeyT, StoreDictValueT, StoreValueT
from . import BaseStore


class RedisStoreBackend(store.RedisStoreBackend):
    """Backend for Async RedisStore."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        options = options or {}
        # Set default options for asyncio Redis.
        options.setdefault("REUSE_CONNECTION", False)
        options.setdefault("CONNECTION_POOL_CLASS", "redis.asyncio.ConnectionPool")
        options.setdefault("REDIS_CLIENT_CLASS", "redis.asyncio.Redis")
        options.setdefault("PARSER_CLASS", "redis.asyncio.connection.DefaultParser")

        super().__init__(server, options)


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = constants.StoreType.REDIS.value

    _BACKEND_CLASS: Type[RedisStoreBackend] = RedisStoreBackend

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
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

    async def get(self, key: KeyT) -> Optional[StoreValueT]:
        value: Optional[StoreValueT] = await self._backend.get_client().get(key)
        if value is None:
            return None

        return utils.format_value(value)

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
        return utils.format_kv(await self._backend.get_client().hgetall(name))

    def make_atomic(self, action_cls: Type[AtomicActionP]) -> AtomicActionP:
        return action_cls(backend=self._backend)
