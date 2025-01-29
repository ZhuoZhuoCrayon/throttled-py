import threading
from collections import OrderedDict
from typing import Any, Dict, Optional
from typing import OrderedDict as OrderedDictT
from typing import Type

from ..constants import StoreType
from ..exceptions import DataError, SetUpError
from ..types import KeyT, StoreValueT
from ..utils import now_sec
from .base import BaseAtomicAction, BaseStore, BaseStoreBackend


class MemoryStoreBackend(BaseStoreBackend):
    """Backend for Memory Store."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)

        max_size: Any = self.options.get("MAX_SIZE", 1024)
        if not (isinstance(max_size, int) and max_size > 0):
            raise SetUpError("MAX_SIZE must be a positive integer")

        self.max_size: int = max_size
        self.expire_info: Dict[str, float] = {}
        self.lock: threading.RLock = threading.RLock()
        self._client: OrderedDictT[KeyT, StoreValueT] = OrderedDict()

    def get_client(self) -> OrderedDictT[KeyT, StoreValueT]:
        return self._client

    def exists(self, key: KeyT) -> bool:
        return key in self.get_client()

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
        is_full: bool = len(self.get_client()) >= self.max_size
        if is_full and not self.exists(key):
            pop_key, __ = self.get_client().popitem(last=False)
            self.expire_info.pop(pop_key, None)

    def expire(self, key: KeyT, timeout: int) -> None:
        self.expire_info[key] = now_sec() + timeout

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        if self.has_expired(key):
            self.delete(key)
            return None

        value: Optional[StoreValueT] = self.get_client().get(key)
        if value is not None:
            self.get_client().move_to_end(key)
        return value

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self.check_and_evict(key)
        self.get_client()[key] = value
        self.get_client().move_to_end(key)
        self.expire(key, timeout)

    def delete(self, key: KeyT) -> bool:
        try:
            self.expire_info.pop(key, None)
            del self.get_client()[key]
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

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        self._backend: MemoryStoreBackend = MemoryStoreBackend(server, options)

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
