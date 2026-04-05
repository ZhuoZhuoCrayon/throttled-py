from throttled import Throttled

throttle = Throttled(
    key="/api/ping",
    quota="100/s burst 200",
)


if __name__ == "__main__":
    result = throttle.limit()
    print(result)
