from collections.abc import Sequence

from throttled import BaseAtomicAction, BaseStore, BaseStoreBackend, constants, types


class OpError(Exception):
    pass


class UnavailableStoreBackend(BaseStoreBackend):
    base_exceptions = (OpError,)


class UnavailableAtomicAction(BaseAtomicAction):
    TYPE: types.AtomicActionTypeT = constants.ATOMIC_ACTION_TYPE_LIMIT
    STORE_TYPE: str = constants.StoreType.REDIS.value

    def do(
        self, keys: Sequence[types.KeyT], args: Sequence[types.StoreValueT] | None
    ) -> tuple[int | float, ...]:
        raise OpError()


class OperationUnavailableStore(BaseStore):
    TYPE: str = constants.StoreType.REDIS.value
    _BACKEND_CLASS: type[UnavailableStoreBackend] = UnavailableStoreBackend

    def make_atomic(self, action_cls: type[BaseAtomicAction]) -> BaseAtomicAction:
        action = UnavailableAtomicAction(self._backend)
        action.TYPE = action_cls.TYPE
        action.STORE_TYPE = action_cls.STORE_TYPE
        return action

    def exists(self, key: types.KeyT) -> bool:
        raise OpError()

    def ttl(self, key: types.KeyT) -> int:
        raise OpError()

    def expire(self, key: types.KeyT, timeout: int) -> None:
        raise OpError()

    def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        raise OpError()

    def get(self, key: types.KeyT) -> types.StoreValueT | None:
        raise OpError()

    def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        raise OpError()

    def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        raise OpError()


class UnavailableStore(OperationUnavailableStore):
    def make_atomic(self, action_cls: type[BaseAtomicAction]) -> BaseAtomicAction:
        raise OpError()
