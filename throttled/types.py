from typing import Any, Dict, Optional, Protocol, Sequence, Type, Union

_StringLikeT = str
_NumberLikeT = Union[int, float]

KeyT = _StringLikeT
StoreValueT = _NumberLikeT
StoreDictValueT = Dict[KeyT, _NumberLikeT]
StoreBucketValueT = Union[_NumberLikeT, StoreDictValueT]

AtomicActionTypeT = str

RateLimiterTypeT = str

TimeLikeValueT = Union[int, float]


class _SyncLockP(Protocol):
    """Protocol for sync lock."""

    def acquire(self) -> bool:
        ...

    def release(self) -> None:
        ...

    def __exit__(self, exc_type, exc, tb) -> None:
        ...

    __enter__ = acquire


class _AsyncLockP(Protocol):
    """Protocol for async lock."""

    async def acquire(self) -> bool:
        ...

    def release(self) -> None:
        ...

    async def __aenter__(self) -> None:
        ...

    async def __aexit__(self, exc_type, exc, tb) -> None:
        ...


LockP = Union[_SyncLockP, _AsyncLockP]


class StoreBackendP(Protocol):
    def get_client(self):
        ...


class _SyncAtomicActionP(Protocol):
    """_SyncAtomicActionP is a protocol for all sync atomic actions."""

    TYPE: AtomicActionTypeT

    STORE_TYPE: str

    def __init__(self, backend: StoreBackendP) -> None:
        ...

    def do(self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]) -> Any:
        ...


class _AsyncAtomicActionP(Protocol):
    """_AsyncAtomicActionP is a protocol for all async atomic actions."""

    TYPE: AtomicActionTypeT

    STORE_TYPE: str

    def __init__(self, backend: StoreBackendP) -> None:
        ...

    async def do(
        self, keys: Sequence[KeyT], args: Optional[Sequence[StoreValueT]]
    ) -> Any:
        ...


AtomicActionP = Union[_SyncAtomicActionP, _AsyncAtomicActionP]


class _SyncStoreP(Protocol):
    """_SyncStoreP is a protocol for all sync store backends."""

    TYPE: str

    def exists(self, key: KeyT) -> bool:
        ...

    def ttl(self, key: KeyT) -> int:
        ...

    def expire(self, key: KeyT, timeout: int) -> None:
        ...

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        ...

    def get(self, key: KeyT) -> Optional[StoreValueT]:
        ...

    def hgetall(self, name: KeyT) -> StoreDictValueT:
        ...

    def make_atomic(self, action: Type[AtomicActionP]) -> AtomicActionP:
        ...

    def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        ...


class _AsyncStoreP(Protocol):
    """_AsyncStoreP is a protocol for all async store backends."""

    TYPE: str

    async def exists(self, key: KeyT) -> bool:
        ...

    async def ttl(self, key: KeyT) -> int:
        ...

    async def expire(self, key: KeyT, timeout: int) -> None:
        ...

    async def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        ...

    async def get(self, key: KeyT) -> Optional[StoreValueT]:
        ...

    async def hgetall(self, name: KeyT) -> StoreDictValueT:
        ...

    def make_atomic(self, action: Type[AtomicActionP]) -> AtomicActionP:
        ...

    async def hset(
        self,
        name: KeyT,
        key: Optional[KeyT] = None,
        value: Optional[StoreValueT] = None,
        mapping: Optional[StoreDictValueT] = None,
    ) -> None:
        ...


StoreP = Union[_SyncStoreP, _AsyncStoreP]
