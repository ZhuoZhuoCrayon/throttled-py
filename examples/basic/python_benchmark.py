import sys

import redis

from throttled import utils

url: str = "redis://127.0.0.1:6379/0"
client: redis.Redis = redis.Redis(connection_pool=redis.ConnectionPool.from_url(url=url))


def redis_baseline():
    client.set("ping:baseline", 1)


def main():
    benchmark: utils.Benchmark = utils.Benchmark()
    print("场景（Redis）：SET key value")
    print("串行 x 100,000 -> ")
    benchmark.serial(redis_baseline, 100_000)
    print("多线程并发 x 100,000（16 workers） -> ")
    benchmark.current(redis_baseline, 5000_000, 3)


if __name__ == "__main__":
    try:
        print(f"version: {sys.version} \nis_gil_enabled: {sys._is_gil_enabled()}")
    except AttributeError:
        print(f"version: {sys.version} \nis_gil_enabled: True")

    main()
