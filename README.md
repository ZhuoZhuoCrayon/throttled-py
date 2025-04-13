<h1 align="center">throttled-py</h1>
<p align="center">
    <em>🔧 High-performance Python rate limiting library with multiple algorithms (Fixed Window, Sliding Window, Token Bucket, Leaky Bucket & GCRA) and storage backends (Redis, In-Memory).</em>
</p>

<p align="center">
    <a href="https://github.com/ZhuoZhuoCrayon/throttled-py">
        <img src="https://badgen.net/badge/python/%3E=3.8/green?icon=github" alt="Python">
    </a>
     <a href="https://github.com/ZhuoZhuoCrayon/throttled-py">
        <img src="https://codecov.io/gh/ZhuoZhuoCrayon/throttled-py/graph/badge.svg" alt="Coverage Status">
    </a>
</p>

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md) | English

## ✨ Features

* Provides thread-safe storage backends: Redis, In-Memory (with support for key expiration and eviction).
* Supports multiple rate limiting algorithms: [Fixed Window](https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8), [Sliding Window](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3), [Token Bucket](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6), [Leaky Bucket](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6) & [Generic Cell Rate Algorithm (GCRA)](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra).
* Provides flexible rate limiting policies, quota configuration, and detailed documentation.
* Supports immediate response and wait-retry modes, and provides function call, decorator, and context manager modes.
* Excellent performance,  The execution time for a single rate limiting API call is equivalent to(see [Benchmarks](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#-benchmarks) for details):
  * In-Memory: ~2.5-4.5x `dict[key] += 1` operations.
  * Redis: ~1.06-1.37x `INCRBY key increment` operations.


## 🔰 Installation

```shell
$ pip install throttled-py
```


## 🎨 Quick Start

### 1) Core API

* `limit`: Deduct requests and return [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult)
* `peek`: Check current rate limit state for a key (returns [**RateLimitState**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#2-ratelimitstate))

### 2) Example

```python
from throttled import RateLimiterType, Throttled, rate_limter, store, utils

throttle = Throttled(
    # 📈 Use Token Bucket algorithm
    using=RateLimiterType.TOKEN_BUCKET.value,
    # 🪣 Set quota: 1000 tokens per second (limit), bucket size 1000 (burst)
    quota=rate_limter.per_sec(1_000, burst=1_000),
    # 📁 Use In-Memory storage
    store=store.MemoryStore(),
)

def call_api() -> bool:
    # 💧 Deduct 1 token for key="/ping"
    result = throttle.limit("/ping", cost=1)
    return result.limited

if __name__ == "__main__":
    # ✅ Total: 100000, 🕒 Latency: 0.5463 ms/op, 🚀 Throughput: 55630 req/s (--)
    # ❌ Denied: 96314 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.concurrent(call_api, 100_000, workers=32))
    print(f"❌ Denied: {denied_num} requests")
```


## 📝 Usage

### 1) Basic Usage

#### Function Call

```python
from throttled import Throttled

# Default: In-Memory storage, Token Bucket algorithm, 60 reqs / min.
throttle = Throttled()

# Deduct 1 request -> RateLimitResult(limited=False,
# state=RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0))
print(throttle.limit("key", 1))
# Check state -> RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0)
print(throttle.peek("key"))

# Deduct 60 requests (limited) -> RateLimitResult(limited=True,
# state=RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=60))
print(throttle.limit("key", 60))
```

#### Decorator

```python
from throttled import Throttled, rate_limter, exceptions

@Throttled(key="/ping", quota=rate_limter.per_min(1))
def ping() -> str:
    return "ping"

ping()

try:
    ping()  # Raises LimitedError
except exceptions.LimitedError as exc:
    print(exc)  # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60
```

#### Context Manager

You can use the context manager to limit the code block. When access is allowed, return [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult).

If the limit is exceeded or the retry timeout is exceeded, it will raise [**LimitedError**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#limitederror).

```python
from throttled import Throttled, exceptions, rate_limter

def call_api():
    print("doing something...")

throttle: Throttled = Throttled(key="/api/v1/users/", quota=rate_limter.per_min(1))
with throttle as rate_limit_result:
    print(f"limited: {rate_limit_result.limited}")
    call_api()

try:
    with throttle:
        call_api()
except exceptions.LimitedError as exc:
    print(exc)  # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60
```

#### Wait & Retry

By default, rate limiting returns [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult) immediately.

You can specify a **`timeout`** to enable wait-and-retry behavior. The rate limiter will wait according to the `retry_after` value in [**RateLimitState**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#2-ratelimitstate) and retry automatically.

Returns the final [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult) when the request is allowed or timeout reached.

```python
from throttled import RateLimiterType, Throttled, rate_limter, utils

throttle = Throttled(
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limter.per_sec(1_000, burst=1_000),
    # ⏳ Set timeout=1 to enable wait-and-retry (max wait 1 second)
    timeout=1,
)

def call_api() -> bool:
    # ⬆️⏳ Function-level timeout overrides global timeout
    result = throttle.limit("/ping", cost=1, timeout=1)
    return result.limited

if __name__ == "__main__":
    # 👇 The actual QPS is close to the preset quota (1_000 req/s):
    # ✅ Total: 10000, 🕒 Latency: 14.7883 ms/op, 🚀Throughput: 1078 req/s (--)
    # ❌ Denied: 54 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.concurrent(call_api, 10_000, workers=16))
    print(f"❌ Denied: {denied_num} requests")
```

### 2) Storage Backends

#### Redis

```python
from throttled import RateLimiterType, Throttled, rate_limter, store

@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limter.per_min(1),
    store=store.RedisStore(server="redis://127.0.0.1:6379/0", options={"PASSWORD": ""}),
)
def products() -> list:
    return [{"name": "iPhone"}, {"name": "MacBook"}]

products()  # Success
products()  # Raises LimitedError
```

#### In-Memory

If you want to throttle the same Key at different locations in your program, make sure that Throttled receives the same MemoryStore and uses a consistent [`Quota`](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#3-quota).

The following example uses memory as the storage backend and throttles the same Key on ping and pong:

```python
from throttled import Throttled, rate_limter, store

mem_store = store.MemoryStore()

@Throttled(key="ping-pong", quota=rate_limter.per_min(1), store=mem_store)
def ping() -> str: return "ping"

@Throttled(key="ping-pong", quota=rate_limter.per_min(1), store=mem_store)
def pong() -> str: return "pong"

ping()  # Success
pong()  # Raises LimitedError
```

### 3) Algorithms

The rate limiting algorithm is specified by the **`using`** parameter. The supported algorithms are as follows:

* [Fixed window](https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8): `RateLimiterType.FIXED_WINDOW.value`
* [Sliding window](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3): `RateLimiterType.SLIDING_WINDOW.value`
* [Token Bucket](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6): `RateLimiterType.TOKEN_BUCKET.value`
* [Leaky Bucket](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6): `RateLimiterType.LEAKING_BUCKET.value`
* [Generic Cell Rate Algorithm, GCRA)](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra): `RateLimiterType.GCRA.value`

```python
from throttled import RateLimiterType, Throttled, rate_limter, store

throttle = Throttled(
    # 🌟Specifying a current limiting algorithm
    using=RateLimiterType.FIXED_WINDOW.value, 
    quota=rate_limter.per_min(1),
    store=store.MemoryStore()
)
assert throttle.limit("key", 2).limited is True
```

### 4) Quota Configuration

#### Quick Setup

```python
from throttled import rate_limter

rate_limter.per_sec(60)   # 60 / sec
rate_limter.per_min(60)   # 60 / min
rate_limter.per_hour(60)  # 60 / hour
rate_limter.per_day(60)   # 60 / day
```

#### Burst Capacity

The **`burst`** parameter can be used to adjust the ability of the throttling object to handle burst traffic. This is valid for the following algorithms:

* `TOKEN_BUCKET`
* `LEAKING_BUCKET`
* `GCRA`

```python
from throttled import rate_limter

# Allow 120 burst requests.
# When burst is not specified, the default setting is the limit passed in.
rate_limter.per_min(60, burst=120)
```

#### Custom Quota

```python
from datetime import timedelta
from throttled.rate_limter import Quota, Rate

# A total of 120 requests are allowed in two minutes, and a burst of 150 requests is allowed.
Quota(Rate(period=timedelta(minutes=2), limit=120), burst=150)
```


## 📊 Benchmarks

### 1) Test Environment
- **Python Version**: 3.13.1 (CPython implementation)
- **Operating System**: macOS Darwin 23.6.0 (ARM64 architecture)
- **Redis Version**: 7.x (local connection)

### 2) Performance Metrics (Throughput in req/s, Latency in ms/op)

| Algorithm Type     | In-Memory (Single-thread) | In-Memory (16 threads)     | Redis (Single-thread) | Redis (16 threads)  |
|--------------------|---------------------------|----------------------------|-----------------------|---------------------|
| **Baseline** *[1]* | **1,692,307 / 0.0002**    | **135,018 / 0.0004** *[2]* | **17,324 / 0.0571**   | **16,803 / 0.9478** |
| Fixed Window       | 369,635 / 0.0023          | 57,275 / 0.2533            | 16,233 / 0.0610       | 15,835 / 1.0070     |
| Sliding Window     | 265,215 / 0.0034          | 49,721 / 0.2996            | 12,605 / 0.0786       | 13,371 / 1.1923     |
| Token Bucket       | 365,678 / 0.0023          | 54,597 / 0.2821            | 13,643 / 0.0727       | 13,219 / 1.2057     |
| Leaky Bucket       | 364,296 / 0.0023          | 54,136 / 0.2887            | 13,628 / 0.0727       | 12,579 / 1.2667     |
| GCRA               | 373,906 / 0.0023          | 53,994 / 0.2895            | 12,901 / 0.0769       | 12,861 / 1.2391     |

* *[1] Baseline: In-Memory - `dict[key] += 1`, Redis - `INCRBY key increment`*.
* *[2] In-Memory concurrent baseline uses `threading.RLock` for thread safety.*
* *[3] Performance: In-Memory - ~2.5-4.5x `dict[key] += 1` operations, Redis - ~1.06-1.37x `INCRBY key increment` operations.*
* *[4] Benchmark code: [tests/benchmarks/test_throttled.py](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/tests/benchmarks/test_throttled.py).*


## ⚙️ Data Models & Configuration

### 1) RateLimitResult

RateLimitState represents the result after executing the RateLimiter for the given key.

| Field     | Type           | Description                                                                             |
|-----------|----------------|-----------------------------------------------------------------------------------------|
| `limited` | bool           | Limited represents whether this request is allowed to pass.                             |
| `state`   | RateLimitState | RateLimitState represents the result after executing the RateLimiter for the given key. |

### 2) RateLimitState

RateLimitState represents the current state of the rate limiter for the given key.

| Field         | Type  | Description                                                                                                                          |
|---------------|-------|--------------------------------------------------------------------------------------------------------------------------------------|
| `limit`       | int   | Limit represents the maximum number of requests allowed to pass in the initial state.                                                |
| `remaining`   | int   | Remaining represents the maximum number of requests allowed to pass for the given key in the current state.                          |
| `reset_after` | float | ResetAfter represents the time in seconds for the RateLimiter to return to its initial state. In the initial state, Limit=Remaining. |
| `retry_after` | float | RetryAfter represents the time in seconds for the request to be retried, 0 if the request is allowed.                                |

### 3) Quota

Quota represents the quota limit configuration.

| Field   | Type | Description                                                                                                    |
|---------|------|----------------------------------------------------------------------------------------------------------------|
| `burst` | int  | Optional burst capacity that allows exceeding the rate limit momentarily(supports Token / Leaky Bucket, GCRA). |
| `rate`  | Rate | The base rate limit configuration.                                                                             |

### 4) Rate

Rate represents the rate limit configuration.

| Field    | Type               | Description                                                         |
|----------|--------------------|---------------------------------------------------------------------|
| `period` | datetime.timedelta | The time period for which the rate limit applies.                   |
| `limit`  | int                | The maximum number of requests allowed within the specified period. |

### 5) Store Configuration

#### Common Parameters

| Param     | Description                     | Default                      |
|-----------|---------------------------------|------------------------------|
| `server`  | Redis connection URL            | `"redis://localhost:6379/0"` |
| `options` | Storage-specific configurations | `{}`                         |

#### RedisStore Options

RedisStore is developed based on the Redis API provided by [redis-py](https://github.com/redis/redis-py).

In terms of Redis connection configuration management, the configuration naming of [django-redis](https://github.com/jazzband/django-redis) is basically used to reduce the learning cost.

| Parameter                  | Description                                                                                                                                                    | Default                               |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| `CONNECTION_FACTORY_CLASS` | ConnectionFactory is used to create and maintain [ConnectionPool](https://redis-py.readthedocs.io/en/stable/connections.html#redis.connection.ConnectionPool). | `"throttled.store.ConnectionFactory"` |
| `CONNECTION_POOL_CLASS`    | ConnectionPool import path.                                                                                                                                    | `"redis.connection.ConnectionPool"`   |
| `CONNECTION_POOL_KWARGS`   | [ConnectionPool construction parameters](https://redis-py.readthedocs.io/en/stable/connections.html#connectionpool).                                           | `{}`                                  |
| `REDIS_CLIENT_CLASS`       | RedisClient import path, uses [redis.client.Redis](https://redis-py.readthedocs.io/en/stable/connections.html#redis.Redis) by default.                         | `"redis.client.Redis"`                |
| `REDIS_CLIENT_KWARGS`      | [RedisClient construction parameters](https://redis-py.readthedocs.io/en/stable/connections.html#redis.Redis).                                                 | `{}`                                  |
| `PASSWORD`                 | Password.                                                                                                                                                      | `null`                                |
| `SOCKET_TIMEOUT`           | ConnectionPool parameters.                                                                                                                                     | `null`                                |
| `SOCKET_CONNECT_TIMEOUT`   | ConnectionPool parameters.                                                                                                                                     | `null`                                |
| `SENTINELS`                | `(host, port)` tuple list, for sentinel mode, please use `SentinelConnectionFactory` and provide this configuration.                                           | `[]`                                  |
| `SENTINEL_KWARGS`          | [Sentinel construction parameters](https://redis-py.readthedocs.io/en/stable/connections.html#id1).                                                            | `{}`                                  |

#### MemoryStore Options

MemoryStore is essentially a [LRU Cache](https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU) based on memory with expiration time.

| Parameter  | Description                                                                                                                          | Default |
|------------|--------------------------------------------------------------------------------------------------------------------------------------|---------|
| `MAX_SIZE` | Maximum capacity. When the number of stored key-value pairs exceeds `MAX_SIZE`, they will be eliminated according to the LRU policy. | `1024`  |

### 6) Exception

All exceptions inherit from `throttled.exceptions.BaseThrottledError`.

#### LimitedError

When a request is throttled, an exception is thrown, such as: `Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.`.

| Field               | Type              | Description                                                   |
|---------------------|-------------------|---------------------------------------------------------------|
| `rate_limit_result` | `RateLimitResult` | The result after executing the RateLimiter for the given key. |

#### DataError

Thrown when the parameter is invalid, such as: `Invalid key: None, must be a non-empty key.`.


## 🍃 Inspiration

* [Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting), by [Brandur Leach](https://github.com/brandur)


## 📚 Version History

[See CHANGELOG_EN.md](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md)


## 📄 License

[The MIT License](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/LICENSE)
