import time

from throttled import Throttled, per_sec, utils


def main():
    # Allow 1 burst request, producing 1 token per second.
    throttle = Throttled(key="key", quota=per_sec(1, burst=1))

    # Consume burst request quota.
    assert not throttle.limit().limited

    timer = utils.Timer(
        clock=time.time,
        callback=lambda elapsed, start, end: print(f"elapsed: {elapsed:.2f} seconds"),
    )
    with timer:
        # Enabled wait-retry, which will wait for the next available token
        # if the limit is reached.
        # > elapsed: 1.00 seconds
        assert not throttle.limit(timeout=1).limited

    with timer:
        # If the timeout is exceeded, it will return the last RateLimitResult.
        # timeout < ``RateLimitResult.retry_after``, return immediately.
        # > elapsed: 0 seconds
        assert throttle.limit(timeout=0.5).limited


if __name__ == "__main__":
    main()
