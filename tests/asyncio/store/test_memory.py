import pytest

from throttled.asyncio import MemoryStore, constants


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.mark.asyncio
class TestMemoryStore:
    async def test_set__overflow(self, store: MemoryStore):
        timeout: int = 10
        size: int = store._backend.max_size
        for idx in range(size + 1):
            await store.set(str(idx), idx, timeout)

        for idx in range(size + 1):
            key: str = str(idx)
            exists: bool = idx != 0
            if exists:
                assert await store.ttl(key) <= timeout
            else:
                assert await store.ttl(key) == constants.STORE_TTL_STATE_NOT_EXIST

            assert await store.exists(key) is exists
