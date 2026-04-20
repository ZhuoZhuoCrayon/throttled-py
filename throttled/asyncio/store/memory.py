import asyncio
from typing import Any, cast

from ... import constants, store, types
from . import BaseStore


class MemoryStoreBackend(store.BaseMemoryStoreBackend):
    """Backend for Async MemoryStore."""

    lock: types.AsyncLockP

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(server, options)
        self.lock = cast("types.AsyncLockP", cast("object", asyncio.Lock()))


class MemoryStore(BaseStore[MemoryStoreBackend]):
    """Concrete implementation of BaseStore using Memory as backend."""

    TYPE: str = constants.StoreType.MEMORY.value

    _BACKEND_CLASS: type[MemoryStoreBackend] = MemoryStoreBackend

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(server, options)
        self._backend: MemoryStoreBackend = self._BACKEND_CLASS(server, options)

    async def exists(self, key: types.KeyT) -> bool:
        return self._backend.exists(key)

    async def ttl(self, key: types.KeyT) -> int:
        return self._backend.ttl(key)

    async def expire(self, key: types.KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.expire(key, timeout)

    async def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        async with self._backend.lock:
            self._backend.set(key, value, timeout)

    async def get(self, key: types.KeyT) -> types.StoreValueT | None:
        async with self._backend.lock:
            return self._backend.get(key)

    async def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        async with self._backend.lock:
            self._backend.hset(name, key, value, mapping)

    async def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        async with self._backend.lock:
            return self._backend.hgetall(name)
