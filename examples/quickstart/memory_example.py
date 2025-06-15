from throttled import Throttled, rate_limiter, store

# 🌟 Use MemoryStore as the storage backend.
mem_store = store.MemoryStore()


@Throttled(key="ping-pong", quota=rate_limiter.per_min(1), store=mem_store)
def ping() -> str:
    return "ping"


@Throttled(key="ping-pong", quota=rate_limiter.per_min(1), store=mem_store)
def pong() -> str:
    return "pong"


def demo():
    # >> ping
    ping()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    pong()


if __name__ == "__main__":
    demo()
