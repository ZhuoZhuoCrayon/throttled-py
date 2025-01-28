import threading
from collections import OrderedDict
from typing import Dict, Optional, Type

from ..constants import StoreType
from ..exceptions import DataError
from ..types import KeyT, StoreValueT
from ..utils import now_sec
from .base import BaseAtomicAction, BaseStore, BaseStoreBackend


class MemoryStoreBackend(BaseStoreBackend):
    """Backend for Memory Store."""

    def __init__(self, max_size: int = 1024):
        self.max_size: int = max_size
        self.expire_info: Dict[str, float] = {}
        self.store: OrderedDict[KeyT, StoreValueT] = OrderedDict()
        self.lock: threading.RLock = threading.RLock()

    def exists(self, key: KeyT) -> bool:
        return key in self.store

    def has_expired(self, key: KeyT) -> bool:
        return self.ttl(key) <= 0

    def ttl(self, key: KeyT) -> int:
        exp: Optional[float] = self.expire_info.get(key)
        if exp is None:
            return -2

        ttl: int = int(exp) - now_sec()
        if ttl <= 0:
            return -2
        return ttl

    def check_and_evict(self, key: KeyT) -> None:
        is_full: bool = len(self.store) >= self.max_size
        if is_full and not self.exists(key):
            pop_key, __ = self.store.popitem(last=False)
            self.expire_info.pop(pop_key, None)

    def expire(self, key: KeyT, timeout: int) -> None:
        self.expire_info[key] = now_sec() + timeout

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        if self.has_expired(key):
            self.delete(key)
            return None

        value: Optional[StoreValueT] = self.store.get(key)
        if value is not None:
            self.store.move_to_end(key)
        return value

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self.check_and_evict(key)
        self.store[key] = value
        self.store.move_to_end(key)
        self.expire(key, timeout)

    def delete(self, key: KeyT) -> bool:
        try:
            self.expire_info.pop(key, None)
            del self.store[key]
        except KeyError:
            return False
        return True


class MemoryStore(BaseStore):
    """Concrete implementation of BaseStore using Memory as backend.

    Below are the performance benchmarks for different configurations of the LRU cache,
    tested using LeetCode problems (https://leetcode.cn/problems/lru-cache/):
    - LRU with Lock and Expiry  -> 265 ms, 76.8 MB
    - LRU with Lock only        -> 211 ms, 76.8 MB
    - LRU only                  -> 103 ms, 76.8 MB  (Beat 92.77% of submissions)
    - LRU implemented in Golang -> 86 ms,  76.43 MB (Beat 52.98% of submissions)
    """

    TYPE: str = StoreType.MEMORY.value

    def __init__(self, max_size: int = 1024):
        self._backend: MemoryStoreBackend = MemoryStoreBackend(max_size)

    def exists(self, key: KeyT) -> bool:
        return self._backend.exists(key)

    def ttl(self, key: KeyT) -> int:
        ttl: int = self._backend.ttl(key)
        if ttl == -2:
            raise DataError("Key not found: {key}".format(key=key))
        return ttl

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        with self._backend.lock:
            self._backend.set(key, value, timeout)

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        with self._backend.lock:
            return self._backend.get(key)

    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        return action_cls(backend=self._backend)
