import asyncio
from typing import Any

from ... import constants, store
from ...types import (
    AsyncLockP,
    KeyT,
    StoreDictValueT,
    StoreValueT,
)
from . import BaseStore


class MemoryStoreBackend(store.BaseMemoryStoreBackend[AsyncLockP]):
    """Backend for Async MemoryStore."""

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(server, options)
        # ``asyncio.Lock()`` structurally matches ``AsyncLockP``.
        self.lock = asyncio.Lock()


class MemoryStore(BaseStore[MemoryStoreBackend]):
    """Concrete implementation of BaseStore using Memory as backend."""

    TYPE: str = constants.StoreType.MEMORY.value

    _BACKEND_CLASS: type[MemoryStoreBackend] = MemoryStoreBackend

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(server, options)
        self._backend: MemoryStoreBackend = self._BACKEND_CLASS(server, options)

    async def exists(self, key: KeyT) -> bool:
        return self._backend.exists(key)

    async def ttl(self, key: KeyT) -> int:
        return self._backend.ttl(key)

    async def expire(self, key: KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.expire(key, timeout)

    async def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        async with self._backend.lock:
            self._backend.set(key, value, timeout)

    async def get(self, key: KeyT) -> StoreValueT | None:
        async with self._backend.lock:
            return self._backend.get(key)

    async def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None:
        async with self._backend.lock:
            self._backend.hset(name, key, value, mapping)

    async def hgetall(self, name: KeyT) -> StoreDictValueT:
        async with self._backend.lock:
            return self._backend.hgetall(name)
