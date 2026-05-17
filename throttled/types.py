from types import TracebackType
from typing import TYPE_CHECKING, ParamSpec, Protocol, TypeVar

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript
    from redis.commands.core import Script as SyncScript


_StringLikeT = str
_NumberLikeT = int | float

KeyT = _StringLikeT
StoreValueT = _NumberLikeT
StoreDictValueT = dict[KeyT, _NumberLikeT]
StoreBucketValueT = _NumberLikeT | StoreDictValueT

AtomicActionTypeT = str

RateLimiterTypeT = str

TimeLikeValueT = int | float

P = ParamSpec("P")
R = TypeVar("R")


class SyncLockP(Protocol):
    """Protocol for sync lock."""

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool: ...
    def release(self) -> None: ...
    def __enter__(self) -> bool: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class AsyncLockP(Protocol):
    """Protocol for async lock."""

    async def acquire(self) -> bool: ...
    def release(self) -> None: ...
    async def __aenter__(self) -> None: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class SyncRedisClientP(Protocol):
    """Protocol declaring Redis methods used by sync RedisStore.

    Centralizes the redis-py boundary: ``_client()`` casts once to this
    Protocol, and all downstream method calls are fully type-safe.
    """

    def exists(self, name: str) -> int: ...
    def ttl(self, name: str) -> int: ...
    def expire(self, name: str, time: int) -> bool: ...
    def set(self, name: str, value: StoreValueT, ex: int | None = ...) -> object: ...
    def get(self, name: str) -> StoreValueT | None: ...
    def incrby(self, name: str, amount: int = 1) -> int: ...
    def delete(self, *names: str) -> int: ...
    def keys(self, pattern: str) -> list[str]: ...
    def flushall(self) -> bool: ...
    def register_script(self, script: str) -> "SyncScript": ...

    def hset(
        self,
        name: str,
        key: str | None = ...,
        value: StoreValueT | None = ...,
        mapping: StoreDictValueT | None = ...,
    ) -> int: ...

    def hgetall(self, name: str) -> StoreDictValueT: ...


class AsyncRedisClientP(Protocol):
    """Protocol declaring Redis methods used by async RedisStore.

    Centralizes the redis-py boundary: ``_client()`` casts once to this
    Protocol, and all downstream method calls are fully type-safe.
    """

    async def exists(self, name: str) -> int: ...
    async def ttl(self, name: str) -> int: ...
    async def expire(self, name: str, time: int) -> bool: ...
    async def get(self, name: str) -> StoreValueT | None: ...
    async def hgetall(self, name: str) -> StoreDictValueT: ...
    async def incrby(self, name: str, amount: int = 1) -> int: ...
    async def delete(self, *names: str) -> int: ...
    async def keys(self, pattern: str) -> list[str]: ...
    async def flushall(self) -> bool: ...
    def register_script(self, script: str) -> "AsyncScript": ...

    async def set(
        self, name: str, value: StoreValueT, ex: int | None = ...
    ) -> object: ...

    async def hset(
        self,
        name: str,
        key: str | None = ...,
        value: StoreValueT | None = ...,
        mapping: StoreDictValueT | None = ...,
    ) -> int: ...


RedisP = SyncRedisClientP | AsyncRedisClientP

RedisClientT = TypeVar("RedisClientT", bound=RedisP)
