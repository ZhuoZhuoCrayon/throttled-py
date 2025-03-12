from throttled import Throttled, rate_limter, store

# 🌟 使用 Memory 作为存储后端
mem_store = store.MemoryStore()


@Throttled(key="ping-pong", quota=rate_limter.per_min(1), store=mem_store)
def ping() -> str:
    return "ping"


@Throttled(key="ping-pong", quota=rate_limter.per_min(1), store=mem_store)
def pong() -> str:
    return "pong"


def demo():
    ping()
    # raise LimitedError: Rate limit exceeded: remaining=0, reset_after=60
    pong()


if __name__ == "__main__":
    demo()
