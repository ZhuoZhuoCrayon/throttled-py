from collections.abc import MutableMapping, Sequence
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


class StoreBackendP(Protocol):
    """Protocol for store backends."""

    def get_client(self) -> object: ...


class AtomicActionIdentityP(Protocol):
    """Identity surface (``TYPE`` / ``STORE_TYPE``) shared by every AtomicAction."""

    TYPE: AtomicActionTypeT
    STORE_TYPE: str


class SyncAtomicActionP(AtomicActionIdentityP, Protocol):
    """Protocol for all sync atomic actions."""

    def do(
        self,
        keys: Sequence[KeyT],
        args: Sequence[StoreValueT] | None,
    ) -> tuple[int | float, ...]: ...


class AsyncAtomicActionP(AtomicActionIdentityP, Protocol):
    """Protocol for all async atomic actions."""

    async def do(
        self,
        keys: Sequence[KeyT],
        args: Sequence[StoreValueT] | None,
    ) -> tuple[int | float, ...]: ...


#: Deprecated compatibility alias; prefer :class:`SyncAtomicActionP` /
#: :class:`AsyncAtomicActionP` or the shared :class:`AtomicActionIdentityP`.
AtomicActionP = SyncAtomicActionP | AsyncAtomicActionP


_MakeAtomicT = TypeVar("_MakeAtomicT")


class StoreForLimiterP(Protocol):
    """Minimum store surface required by ``BaseRateLimiterMixin``.

    Both sync ``throttled.store.BaseStore`` and async
    ``throttled.asyncio.store.BaseStore`` satisfy this structurally. Runtime
    pairing between a backend and an AtomicAction is enforced by the
    ``STORE_TYPE`` filter inside ``_register_atomic_actions``.
    """

    TYPE: str

    def make_atomic(self, action_cls: type[_MakeAtomicT]) -> _MakeAtomicT: ...


class SyncStoreP(StoreForLimiterP, Protocol):
    """Protocol for all sync store backends."""

    def exists(self, key: KeyT) -> bool: ...
    def ttl(self, key: KeyT) -> int: ...
    def expire(self, key: KeyT, timeout: int) -> None: ...
    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None: ...
    def get(self, key: KeyT) -> StoreValueT | None: ...
    def hgetall(self, name: KeyT) -> StoreDictValueT: ...

    def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None: ...


class AsyncStoreP(StoreForLimiterP, Protocol):
    """Protocol for all async store backends."""

    async def exists(self, key: KeyT) -> bool: ...
    async def ttl(self, key: KeyT) -> int: ...
    async def expire(self, key: KeyT, timeout: int) -> None: ...
    async def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None: ...
    async def get(self, key: KeyT) -> StoreValueT | None: ...
    async def hgetall(self, name: KeyT) -> StoreDictValueT: ...

    async def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None: ...


#: Deprecated compatibility alias; prefer :class:`SyncStoreP` /
#: :class:`AsyncStoreP` or the shared :class:`StoreForLimiterP`.
StoreP = SyncStoreP | AsyncStoreP


class MemoryStoreBackendP(StoreBackendP, Protocol):
    """Protocol for memory-like backend surface used by rate limit algorithms."""

    def get_client(self) -> MutableMapping[KeyT, StoreBucketValueT]: ...
    def exists(self, key: KeyT) -> bool: ...
    def ttl(self, key: KeyT) -> int: ...
    def expire(self, key: KeyT, timeout: int) -> None: ...
    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None: ...
    def get(self, key: KeyT) -> StoreValueT | None: ...
    def hgetall(self, name: KeyT) -> StoreDictValueT: ...

    def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
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

MemoryStoreBackendT = TypeVar(
    "MemoryStoreBackendT",
    bound=MemoryStoreBackendP,
)

StoreT = TypeVar("StoreT", bound=StoreForLimiterP)

ActionT = TypeVar("ActionT", bound=AtomicActionIdentityP)
