from throttled import Throttled, rate_limiter


# 🌟 Use the global MemoryStore as the storage backend.
@Throttled(key="/api/products", quota=rate_limiter.per_min(1))
def products() -> list:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


def demo():
    products()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    products()


if __name__ == "__main__":
    demo()
