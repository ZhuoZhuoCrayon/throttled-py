from throttled import Throttled

throttle = Throttled(
    key="/api/ping",
    quota="100/s",
    # quota="100/s burst 200",
    # quota="100 per second",
    # quota="100 per second burst 200",
)


if __name__ == "__main__":
    print(throttle.limit())
