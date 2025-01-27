from typing import Optional, Type

from redis import Redis

from ..constants import StoreType
from ..exceptions import DataError
from ..typing import KeyT, StoreValueT
from .base import BaseAtomicAction, BaseStore, BaseStoreBackend


class RedisStoreBackend(BaseStoreBackend):
    """Backend for Redis store."""

    def __init__(self, client: Redis):
        self.client: Redis = client


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend."""

    TYPE: str = StoreType.REDIS.value

    def __init__(self, client: Redis):
        self._backend: RedisStoreBackend = RedisStoreBackend(client)

    def exists(self, key: KeyT) -> bool:
        return bool(self._backend.client.exists(key))

    def ttl(self, key: KeyT) -> int:
        ttl: int = int(self._backend.client.ttl(key))
        if ttl == -2:
            raise DataError("Key not found: {key}".format(key=key))
        return ttl

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.client.set(key, value, ex=timeout)

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        value: Optional[StoreValueT] = self._backend.client.get(key)
        if value is None:
            return None

        float_value: float = float(value)
        if float_value.is_integer():
            return int(float_value)
        return float_value

    def make_atomic(self, action_cls: Type[BaseAtomicAction]) -> BaseAtomicAction:
        return action_cls(backend=self._backend)
