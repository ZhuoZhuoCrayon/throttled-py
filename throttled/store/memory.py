import math
import threading
from collections import OrderedDict
from collections import OrderedDict as OrderedDictT
from typing import Any, cast

from .. import types
from ..constants import STORE_TTL_STATE_NOT_EXIST, STORE_TTL_STATE_NOT_TTL, StoreType
from ..exceptions import DataError, SetUpError
from ..utils import now_mono_f
from .base import BaseStore, BaseStoreBackend

_ClientT = OrderedDictT[types.KeyT, types.StoreBucketValueT]


class BaseMemoryStoreBackend(BaseStoreBackend[_ClientT]):
    """Base backend for Memory Store."""

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(server, options)

        max_size: int = self.options.get("MAX_SIZE", 1024)
        if not (isinstance(max_size, int) and max_size > 0):
            raise SetUpError("MAX_SIZE must be a positive integer")

        self.max_size: int = max_size
        self.expire_info: dict[str, float] = {}
        self._client: _ClientT = OrderedDict()

    def get_client(self) -> _ClientT:
        return self._client

    def exists(self, key: types.KeyT) -> bool:
        return key in self._client

    def has_expired(self, key: types.KeyT) -> bool:
        return self.ttl(key) == STORE_TTL_STATE_NOT_EXIST

    def ttl(self, key: types.KeyT) -> int:
        exp: float | None = self.expire_info.get(key)
        if exp is None:
            if not self.exists(key):
                return STORE_TTL_STATE_NOT_EXIST
            return STORE_TTL_STATE_NOT_TTL

        ttl: float = exp - now_mono_f()
        if ttl <= 0:
            return STORE_TTL_STATE_NOT_EXIST
        return math.ceil(ttl)

    def check_and_evict(self, key: types.KeyT) -> None:
        is_full: bool = len(self._client) >= self.max_size
        if is_full and not self.exists(key):
            pop_key, __ = self._client.popitem(last=False)
            self.expire_info.pop(pop_key, None)

    def expire(self, key: types.KeyT, timeout: int) -> None:
        self.expire_info[key] = now_mono_f() + timeout

    def get(self, key: types.KeyT) -> types.StoreValueT | None:
        if self.has_expired(key):
            self.delete(key)
            return None

        bucket_value: types.StoreBucketValueT | None = self._client.get(key)
        if bucket_value is not None and isinstance(bucket_value, dict):
            raise DataError("dict value does not support get")
        value: types.StoreValueT | None = bucket_value
        if value is not None:
            self._client.move_to_end(key)
        return value

    def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        self.check_and_evict(key)
        self._client[key] = value
        self._client.move_to_end(key)
        self.expire(key, timeout)

    def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")

        kv: types.StoreDictValueT = {}
        if key is not None:
            if value is None:
                raise DataError("hset with key requires non-empty value")
            kv[key] = value
        if mapping:
            kv.update(mapping)

        origin: types.StoreBucketValueT | None = self._client.get(name)
        if origin is not None:
            if not isinstance(origin, dict):
                raise DataError("origin must be a dict")
            origin.update(kv)
        else:
            self.check_and_evict(name)
            self._client[name] = kv

        self._client.move_to_end(name)

    def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        if self.has_expired(name):
            self.delete(name)
            return {}

        kv: types.StoreBucketValueT | None = self._client.get(name)
        if not (kv is None or isinstance(kv, dict)):
            raise DataError("NumberLike value does not support hgetall")

        if kv is not None:
            self._client.move_to_end(name)

        return kv or {}

    def delete(self, key: types.KeyT) -> bool:
        try:
            self.expire_info.pop(key, None)
            del self._client[key]
        except KeyError:
            return False
        return True


class MemoryStoreBackend(BaseMemoryStoreBackend):
    """Backend for sync Memory Store."""

    lock: types.SyncLockP

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(server, options)
        self.lock = cast("types.SyncLockP", cast("object", threading.Lock()))


class MemoryStore(BaseStore[MemoryStoreBackend]):
    """Concrete implementation of BaseStore using Memory as backend.

    :class:`throttled.store.MemoryStore` is essentially a memory-based
    `LRU Cache <https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU>`_
    with expiration time, it is thread-safe and can be used for rate limiting
    in a single process.
    """

    # Below are the performance benchmarks for different configurations of the LRU cache,
    # tested using LeetCode problems (https://leetcode.cn/problems/lru-cache/):
    #
    # * LRU with Lock and Expiry  -> 265 ms, 76.8 MB
    # * LRU with Lock only        -> 211 ms, 76.8 MB
    # * LRU only                  -> 103 ms, 76.8 MB  (Beat 92.77% of submissions)
    # * LRU implemented in Golang -> 86 ms,  76.43 MB (Beat 52.98% of submissions)

    TYPE: str = StoreType.MEMORY.value

    _BACKEND_CLASS: type[MemoryStoreBackend] = MemoryStoreBackend

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        """Initialize MemoryStore.

        :ref:`MemoryStore Arguments <store-configuration-memory-store-arguments>`.
        """
        super().__init__(server, options)
        self._backend: MemoryStoreBackend = self._BACKEND_CLASS(server, options)

    def exists(self, key: types.KeyT) -> bool:
        return self._backend.exists(key)

    def ttl(self, key: types.KeyT) -> int:
        return self._backend.ttl(key)

    def expire(self, key: types.KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.expire(key, timeout)

    def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        with self._backend.lock:
            self._backend.set(key, value, timeout)

    def get(self, key: types.KeyT) -> types.StoreValueT | None:
        with self._backend.lock:
            return self._backend.get(key)

    def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        with self._backend.lock:
            self._backend.hset(name, key, value, mapping)

    def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        with self._backend.lock:
            return self._backend.hgetall(name)
