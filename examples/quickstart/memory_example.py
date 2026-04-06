from throttled import Throttled, store

# 🌟 Use MemoryStore as the storage backend.
mem_store = store.MemoryStore()


@Throttled(key="ping-pong", quota="1/m", store=mem_store)
def ping() -> str:
    return "ping"


@Throttled(key="ping-pong", quota="1/m", store=mem_store)
def pong() -> str:
    return "pong"


def demo() -> None:
    # >> ping
    ping()  # type: ignore[call-arg]
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    pong()  # type: ignore[call-arg]


if __name__ == "__main__":
    demo()
