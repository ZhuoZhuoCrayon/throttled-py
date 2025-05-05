import pytest

from throttled.asyncio import BaseStore, MemoryStore, constants, utils


@pytest.fixture(params=[constants.StoreType.MEMORY.value])
def store(request) -> BaseStore:
    def _create_store(store_type: str) -> BaseStore:
        if store_type == constants.StoreType.MEMORY.value:
            return MemoryStore()

    store: BaseStore = _create_store(request.param)

    yield store

    if request.param == constants.StoreType.REDIS.value:
        store._backend.get_client().flushall()


@pytest.fixture(scope="class")
def benchmark() -> utils.Benchmark:
    return utils.Benchmark()
