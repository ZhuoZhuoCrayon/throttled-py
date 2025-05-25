import asyncio
from typing import Any, Dict, Optional, Type

from ... import constants, store
from ...types import AtomicActionP, KeyT, LockP, StoreDictValueT, StoreValueT
from . import BaseStore


class MemoryStoreBackend(store.MemoryStoreBackend):
    """Backend for Async MemoryStore."""

    def _get_lock(self) -> LockP:
        return asyncio.Lock()


class MemoryStore(BaseStore):
    """Concrete implementation of BaseStore using Memory as backend."""

    TYPE: str = constants.StoreType.MEMORY.value

    _BACKEND_CLASS: Type[MemoryStoreBackend] = MemoryStoreBackend

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
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

    async def get(self, key: KeyT) -> Optional[StoreValueT]:
        async with self._backend.lock:
            return self._backend.get(key)

    async def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        async with self._backend.lock:
            self._backend.hset(name, key, value, mapping)

    async def hgetall(self, name: KeyT) -> StoreDictValueT:
        async with self._backend.lock:
            return self._backend.hgetall(name)

    def make_atomic(self, action_cls: Type[AtomicActionP]) -> AtomicActionP:
        return action_cls(backend=self._backend)
