import pytest

from throttled import MemoryStore
from throttled.constants import STORE_TTL_STATE_NOT_EXIST


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


class TestMemoryStore:
    def test_set__overflow(self, store: MemoryStore):
        timeout: int = 10
        size: int = store._backend.max_size
        for idx in range(size + 1):
            store.set(str(idx), idx, timeout)

        for idx in range(size + 1):
            key: str = str(idx)
            exists: bool = idx != 0
            if exists:
                assert store.ttl(key) <= timeout
            else:
                assert store.ttl(key) == STORE_TTL_STATE_NOT_EXIST

            assert store.exists(key) is exists
