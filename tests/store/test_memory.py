import pytest

from throttled.exceptions import DataError
from throttled.store.memory import MemoryStore


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
            exists: bool = (True, False)[idx == 0]
            if exists:
                assert store.ttl(key) == timeout
            else:
                with pytest.raises(DataError, match="Key not found"):
                    store.ttl(key)

            assert store.exists(key) is exists
