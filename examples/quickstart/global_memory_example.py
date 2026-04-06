from throttled import Throttled


# 🌟 Use the global MemoryStore as the storage backend.
@Throttled(key="/api/products", quota="1/m")
def products() -> list[dict[str, str]]:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


def demo() -> None:
    products()  # type: ignore[call-arg]
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    products()  # type: ignore[call-arg]


if __name__ == "__main__":
    demo()
