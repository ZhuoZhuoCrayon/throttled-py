import math
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional
from typing import OrderedDict as OrderedDictT
from typing import Type

from ..constants import STORE_TTL_STATE_NOT_EXIST, STORE_TTL_STATE_NOT_TTL, StoreType
from ..exceptions import DataError, SetUpError
from ..types import KeyT, LockP, StoreBucketValueT, StoreDictValueT, StoreValueT
from ..utils import now_mono_f
from .base import BaseAtomicAction, BaseStore, BaseStoreBackend


class MemoryStoreBackend(BaseStoreBackend):
    """Backend for Memory Store."""

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)

        max_size: int = self.options.get("MAX_SIZE", 1024)
        if not (isinstance(max_size, int) and max_size > 0):
            raise SetUpError("MAX_SIZE must be a positive integer")

        self.max_size: int = max_size
        self.expire_info: Dict[str, float] = {}
        self.lock: LockP = self._get_lock()
        self._client: OrderedDictT[KeyT, StoreBucketValueT] = OrderedDict()

    @classmethod
    def _get_lock(cls) -> LockP:
        return threading.Lock()

    def get_client(self) -> OrderedDictT[KeyT, StoreBucketValueT]:
        return self._client

    def exists(self, key: KeyT) -> bool:
        return key in self._client

    def has_expired(self, key: KeyT) -> bool:
        return self.ttl(key) == STORE_TTL_STATE_NOT_EXIST

    def ttl(self, key: KeyT) -> int:
        exp: Optional[float] = self.expire_info.get(key)
        if exp is None:
            if not self.exists(key):
                return STORE_TTL_STATE_NOT_EXIST
            return STORE_TTL_STATE_NOT_TTL

        ttl: float = exp - now_mono_f()
        if ttl <= 0:
            return STORE_TTL_STATE_NOT_EXIST
        return math.ceil(ttl)

    def check_and_evict(self, key: KeyT) -> None:
        is_full: bool = len(self._client) >= self.max_size
        if is_full and not self.exists(key):
            pop_key, __ = self._client.popitem(last=False)
            self.expire_info.pop(pop_key, None)

    def expire(self, key: KeyT, timeout: int) -> None:
        self.expire_info[key] = now_mono_f() + timeout

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        if self.has_expired(key):
            self.delete(key)
            return None

        value: Optional[StoreValueT] = self._client.get(key)
        if value is not None:
            self._client.move_to_end(key)
        return value

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self.check_and_evict(key)
        self._client[key] = value
        self._client.move_to_end(key)
        self.expire(key, timeout)

    def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")

        kv: StoreDictValueT = {}
        if key is not None:
            kv[key] = value
        if mapping:
            kv.update(mapping)

        origin: Optional[StoreBucketValueT] = self._client.get(name)
        if origin is not None:
            if not isinstance(origin, dict):
                raise DataError("origin must be a dict")
            origin.update(kv)
        else:
            self.check_and_evict(key)
            self._client[name] = kv

        self._client.move_to_end(name)

    def hgetall(self, name: KeyT) -> StoreDictValueT:
        if self.has_expired(name):
            self.delete(name)
            return {}

        kv: Optional[StoreBucketValueT] = self._client.get(name)
        if not (kv is None or isinstance(kv, dict)):
            raise DataError("NumberLike value does not support hgetall")

        if kv is not None:
            self._client.move_to_end(name)

        return kv or {}

    def delete(self, key: KeyT) -> bool:
        try:
            self.expire_info.pop(key, None)
            del self._client[key]
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

    _BACKEND_CLASS: Type[MemoryStoreBackend] = MemoryStoreBackend

    def __init__(
        self, server: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ):
        super().__init__(server, options)
        self._backend: MemoryStoreBackend = self._BACKEND_CLASS(server, options)

    def exists(self, key: KeyT) -> bool:
        return self._backend.exists(key)

    def ttl(self, key: KeyT) -> int:
        return self._backend.ttl(key)

    def expire(self, key: KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.expire(key, timeout)

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        with self._backend.lock:
            self._backend.set(key, value, timeout)

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        with self._backend.lock:
            return self._backend.get(key)

    def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        with self._backend.lock:
            self._backend.hset(name, key, value, mapping)

    def hgetall(self, name: KeyT) -> StoreDictValueT:
        with self._backend.lock:
            return self._backend.hgetall(name)

    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        return action_cls(backend=self._backend)
