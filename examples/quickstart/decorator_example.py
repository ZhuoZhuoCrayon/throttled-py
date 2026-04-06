from throttled import Throttled, exceptions

quota = "2/m"


# Create a rate limiter that allows 2 request per minute.
@Throttled(key="/ping", quota=quota)
def ping() -> str:
    return "pong"


# Create a rate limiter that allows 2 cost per minute, consuming 2 Tokens per call.
@Throttled(key="/ping", quota=quota, cost=2)
def heavy_ping() -> str:
    return "heavy_pong"


def main() -> None:
    # The first call will not be rate limited.
    # >> pong
    print(ping())  # type: ignore[call-arg]

    try:
        # The second call will be rate limited, because heavy_ping consumes 2 Tokens
        # and 1 Token has been consumed by the first call.
        heavy_ping()  # type: ignore[call-arg]
    except exceptions.LimitedError as exc:
        # >> Rate limit exceeded: remaining=1, reset_after=30, retry_after=60.
        print(exc)


if __name__ == "__main__":
    main()
