from collections.abc import Sequence
from types import TracebackType
from typing import Protocol

_StringLikeT = str
_NumberLikeT = int | float

KeyT = _StringLikeT
StoreValueT = _NumberLikeT
StoreDictValueT = dict[KeyT, _NumberLikeT]
StoreBucketValueT = _NumberLikeT | StoreDictValueT

AtomicActionTypeT = str

RateLimiterTypeT = str

TimeLikeValueT = int | float


class _SyncLockP(Protocol):
    """Protocol for sync lock."""

    def acquire(self) -> bool: ...

    def release(self) -> None: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    def __enter__(self) -> bool: ...


class _AsyncLockP(Protocol):
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


LockP = _SyncLockP | _AsyncLockP


class StoreBackendP(Protocol):
    """Protocol for store backends."""

    def get_client(self) -> object: ...


class _SyncAtomicActionP(Protocol):
    """_SyncAtomicActionP is a protocol for all sync atomic actions."""

    TYPE: AtomicActionTypeT

    STORE_TYPE: str

    def __init__(self, backend: StoreBackendP) -> None: ...

    def do(
        self,
        keys: Sequence[KeyT],
        args: Sequence[StoreValueT] | None,
    ) -> tuple[int, ...]: ...


class _AsyncAtomicActionP(Protocol):
    """_AsyncAtomicActionP is a protocol for all async atomic actions."""

    TYPE: AtomicActionTypeT

    STORE_TYPE: str

    def __init__(self, backend: StoreBackendP) -> None: ...

    async def do(
        self,
        keys: Sequence[KeyT],
        args: Sequence[StoreValueT] | None,
    ) -> tuple[int, ...]: ...


AtomicActionP = _SyncAtomicActionP | _AsyncAtomicActionP


class _SyncStoreP(Protocol):
    """_SyncStoreP is a protocol for all sync store backends."""

    TYPE: str

    def exists(self, key: KeyT) -> bool: ...

    def ttl(self, key: KeyT) -> int: ...

    def expire(self, key: KeyT, timeout: int) -> None: ...

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None: ...

    def get(self, key: KeyT) -> StoreValueT | None: ...

    def hgetall(self, name: KeyT) -> StoreDictValueT: ...

    def make_atomic(self, action_cls: type[AtomicActionP]) -> AtomicActionP: ...

    def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None: ...


class _AsyncStoreP(Protocol):
    """_AsyncStoreP is a protocol for all async store backends."""

    TYPE: str

    async def exists(self, key: KeyT) -> bool: ...

    async def ttl(self, key: KeyT) -> int: ...

    async def expire(self, key: KeyT, timeout: int) -> None: ...

    async def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None: ...

    async def get(self, key: KeyT) -> StoreValueT | None: ...

    async def hgetall(self, name: KeyT) -> StoreDictValueT: ...

    def make_atomic(self, action_cls: type[AtomicActionP]) -> AtomicActionP: ...

    async def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None: ...


StoreP = _SyncStoreP | _AsyncStoreP
