import pytest

from throttled import MemoryStore
from throttled.constants import StoreTTLState


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


class TestMemoryStore:
    def test_set__overflow(self, store: MemoryStore):
        timeout: int = 1
        size: int = store._backend.max_size
        for idx in range(size + 1):
            store.set(str(idx), idx, timeout)

        for idx in range(size + 1):
            key: str = str(idx)
            exists: bool = idx != 0
            assert store.ttl(key) == (StoreTTLState.NOT_EXIST.value, timeout)[exists]
            assert store.exists(key) is exists
