from throttled import RateLimiterType, Throttled, rate_limter, store


@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limter.per_min(1),
    # use Redis as storage
    store=store.RedisStore(server="redis://127.0.0.1:6379/0", options={"PASSWORD": ""}),
)
def products() -> list:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


def demo():
    products()
    # raise LimitedError: Rate limit exceeded: remaining=0, reset_after=60
    products()


if __name__ == "__main__":
    demo()
