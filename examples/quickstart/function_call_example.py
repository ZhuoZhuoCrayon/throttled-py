from throttled import Throttled


def main():
    # By Default, it initializes a rate limiter with In-Memory,
    # allowing 60 requests per minute, using the token bucket algorithm.
    # Default: In-Memory storage, Token Bucket algorithm, 60 reqs / min.
    throttle = Throttled()

    # Consume 1 token.
    result = throttle.limit("key")
    # Should not be limited.
    assert not result.limited

    # Get the state of the rate limiter:
    # >> RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0))
    print(result.state)

    # You can also get the state by using the `peek` method.
    # >> RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0)
    print(throttle.peek("key"))

    # You can also specify the cost of the request.
    result = throttle.limit("key", cost=60)
    # This will consume 60 tokens, which exceeds the limit of 60 tokens per minute.
    assert result.limited

    # >> RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=60))
    print(result.state)


if __name__ == "__main__":
    main()
