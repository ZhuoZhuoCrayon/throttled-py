<h1 align="center">throttled-py</h1>
<p align="center">
    <em>🔧 支持多种算法（固定窗口，滑动窗口，令牌桶，漏桶 & GCRA）及存储（Redis、内存）的高性能 Python 限流库。</em>
</p>

<p align="center">
    <a href="https://github.com/ZhuoZhuoCrayon/throttled-py">
        <img src="https://img.shields.io/badge/python-%3E%3D3.8-green?logo=python" alt="Python">
    </a>
     <a href="https://github.com/ZhuoZhuoCrayon/throttled-py">
        <img src="https://codecov.io/gh/ZhuoZhuoCrayon/throttled-py/graph/badge.svg" alt="Coverage Status">
    </a>
     <a href="https://pypi.org/project/throttled-py/">
        <img src="https://img.shields.io/pypi/v/throttled-py.svg" alt="Pypi Package">
    </a>
     <a href="https://pepy.tech/projects/throttled-py">
        <img src="https://static.pepy.tech/personalized-badge/throttled-py?period=total&units=INTERNATIONAL_SYSTEM&left_color=GRAY&right_color=GREEN&left_text=downloads" alt="Downloads">
    </a>
    <a href="https://github.com/ZhuoZhuoCrayon/throttled-py/issues">
        <img src="https://img.shields.io/badge/issue-welcome-blue.svg?logo=github" alt="Welcome Issue">
    </a>
    <a href="https://hellogithub.com/repository/fb094234bf744e108f4ce7d3326a5cb1" target="_blank">
        <img src="https://api.hellogithub.com/v1/widgets/recommend.svg?rid=fb094234bf744e108f4ce7d3326a5cb1&claim_uid=RzCXpndJ3LrMbUH&theme=small" alt="Featured｜HelloGitHub" />
    </a>
</p>

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py) | 简体中文

[🔰 安装](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-%E5%AE%89%E8%A3%85)｜[🎨 快速开始](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)｜[⚙️ 数据模型与配置](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#%EF%B8%8F-%E6%95%B0%E6%8D%AE%E6%A8%A1%E5%9E%8B%E4%B8%8E%E9%85%8D%E7%BD%AE)｜[📊 Benchmarks](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-benchmarks)｜[🍃 灵感](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-%E7%81%B5%E6%84%9F)｜[📚 Version History](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-version-history)｜[📄 License](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-license)


## ✨ 功能

* 支持同步和[异步](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#3%E5%BC%82%E6%AD%A5)（`async / await`）。
* 提供线程安全的存储后端：[Redis（单例/哨兵/集群）](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#redis)、[内存（支持 Key 过期淘汰）](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#memory)。
* 支持多种限流算法：[固定窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8)、[滑动窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3)、[令牌桶](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6)、[漏桶](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6) & [通用信元速率算法（Generic Cell Rate Algorithm, GCRA）](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra)。
* 支持[配置限流算法](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#3%E6%8C%87%E5%AE%9A%E9%99%90%E6%B5%81%E7%AE%97%E6%B3%95)，提供灵活的[配额设置](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#4%E6%8C%87%E5%AE%9A%E5%AE%B9%E9%87%8F)。
* 支持即刻返回及[等待重试](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#%E7%AD%89%E5%BE%85%E9%87%8D%E8%AF%95)，提供[函数调用](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#%E5%87%BD%E6%95%B0%E8%B0%83%E7%94%A8)、[装饰器](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#%E4%BD%9C%E4%B8%BA%E8%A3%85%E9%A5%B0%E5%99%A8)、[上下文管理器](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#%E4%B8%8A%E4%B8%8B%E6%96%87%E7%AE%A1%E7%90%86%E5%99%A8)。
* 支持集成到 [MCP](https://modelcontextprotocol.io/introduction) [Python SDK](https://github.com/modelcontextprotocol/python-sdk)，为模型对话流程提供限流支持。
* 良好的性能，单次限流 API 执行耗时换算如下（详见 [Benchmarks](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#-benchmarks)）：
  * 内存：约为 2.5 ~ 4.5 次 `dict[key] += 1` 操作。
  * Redis：约为 1.06 ~ 1.37 次 `INCRBY key increment` 操作。


## 🔰 安装

```shell
$ pip install throttled-py
```

> 说明：`v3.x` 要求 Python `>=3.10`。如果你使用的是 Python `3.8/3.9`，请安装 `throttled-py<3.0.0`。

### 1）额外依赖

自 [v2.0.0](https://github.com/ZhuoZhuoCrayon/throttled-py/releases/tag/v2.0.0) 版本起，默认安装仅包含核心功能依赖。

如需使用扩展功能，可通过以下方式安装可选依赖项（多个依赖项用逗号分隔）：

```shell
$ pip install "throttled-py[redis]"

$ pip install "throttled-py[otel]"

$ pip install "throttled-py[redis,otel]"
```

可选依赖项说明：

| 附加依赖项       | 描述               |
|-------------|------------------|
| `memory`    | 内存后端默认可用（`memory` extra 不会额外安装依赖）。 |
| `redis`     | 使用 Redis 作为存储后端。 |
| `otel`      | 启用 OpenTelemetry Hook 支持。 |


## 🎨 快速开始

### 1）通用 API

* `limit`：消耗请求，返回 [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#1ratelimitresult)。
* `peek`：获取指定 Key 的限流器状态，返回 [**RateLimitState**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#2ratelimitstate)。

### 2）样例

```python
from throttled import RateLimiterType, Throttled, rate_limiter, utils

throttle = Throttled(
    # 📈 使用令牌桶作为限流算法。
    using=RateLimiterType.TOKEN_BUCKET.value,
    # 🪣 设置配额：每秒填充 1,000 个 Token（limit），桶大小为 1,000（burst）。
    quota=rate_limiter.per_sec(1_000, burst=1_000),
    # 📁默认使用全局 MemoryStore 作为存储后端。
)


def call_api() -> bool:
    # 💧消耗 Key=/ping 的一个 Token。
    result = throttle.limit("/ping", cost=1)
    return result.limited


if __name__ == "__main__":
    # 💻 Python 3.12.10, Linux 5.4.119-1-tlinux4-0009.1, Arch: x86_64, Specs: 2C4G.
    # ✅ Total: 100000, 🕒 Latency: 0.0068 ms/op, 🚀 Throughput: 122513 req/s (--)
    # ❌ Denied: 98000 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.serial(call_api, 100_000))
    print(f"❌ Denied: {denied_num} requests")
```

### 3）异步

同步和异步拥有一致的功能和标准 API，只需将导入语句从 `from throttled import ...` 替换为 `from throttled.asyncio import ..` 即可。

例如将 `2）样例` 改写为异步：

```python
import asyncio
from throttled.asyncio import RateLimiterType, Throttled, rate_limiter, store, utils

throttle = Throttled(
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limiter.per_sec(1_000, burst=1_000),
)


async def call_api() -> bool:
    result = await throttle.limit("/ping", cost=1)
    return result.limited


async def main():
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(await benchmark.async_serial(call_api, 100_000))
    print(f"❌ Denied: {denied_num} requests")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📝 使用

### 1）基础

#### 函数调用

```python
from throttled import Throttled

# 参数全部缺省时，默认初始化一个基于「内存」、每分钟允许通过 60 个请求、使用「令牌桶算法」的限流器。
throttle = Throttled()

# 消耗 1 次请求，输出：RateLimitResult(limited=False,
# state=RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0))
print(throttle.limit("key", 1))
# 获取限流器状态，输出：RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0)
print(throttle.peek("key"))

# 消耗 60 次请求，触发限流，输出：RateLimitResult(limited=True,
# state=RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=60))
print(throttle.limit("key", 60))
```

#### 作为装饰器

```python
from throttled import Throttled, exceptions, rate_limiter

# 创建一个每分钟允许通过 1 次的限流器。
@Throttled(key="/ping", quota=rate_limiter.per_min(1))
def ping() -> str:
    return "ping"

ping()
try:
    ping()  # 当触发限流时，抛出 LimitedError。
except exceptions.LimitedError as exc:
    print(exc)  # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60
```

#### 上下文管理器

你可以使用「上下文管理器」对代码块进行限流，允许通过时，返回 [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#1ratelimitresult)。

触发限流或重试超时，抛出 [**LimitedError**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#limitederror)。

```python
from throttled import Throttled, exceptions, rate_limiter

def call_api():
    print("doing something...")

throttle: Throttled = Throttled(key="/api/v1/users/", quota=rate_limiter.per_min(1))
with throttle as rate_limit_result:
    print(f"limited: {rate_limit_result.limited}")
    call_api()

try:
    with throttle:
        call_api()
except exceptions.LimitedError as exc:
    print(exc)  # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60
```

#### 等待重试

默认情况下，限流判断将「即刻」返回 [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#1ratelimitresult)。

你可以通过  **`timeout`** 指定等待重试的超时时间，限流器将根据  [**RateLimitState**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#2ratelimitstate) 的 `retry_after` 进行若干次等待及重试。

一旦请求通过或超时，返回最后一次的  [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#1ratelimitresult)。

```python
from throttled import RateLimiterType, Throttled, rate_limiter, utils

throttle = Throttled(
    using=RateLimiterType.GCRA.value,
    quota=rate_limiter.per_sec(100, burst=100),
    # ⏳ 设置超时时间为 1 秒，表示允许等待重试，等待时间超过 1 秒返回最后一次限流结果。
    timeout=1,
)

def call_api() -> bool:
    # ⬆️⏳ 函数调用传入 timeout 将覆盖全局设置的 timeout。
    result = throttle.limit("/ping", cost=1, timeout=1)
    return result.limited


if __name__ == "__main__":
    # 👇 实际 QPS 接近预设容量（100 req/s）：
    # ✅ Total: 1000, 🕒 Latency: 35.8103 ms/op, 🚀 Throughput: 111 req/s (--)
    # ❌ Denied: 8 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.concurrent(call_api, 1_000, workers=4))
    print(f"❌ Denied: {denied_num} requests")
```

### 2）指定存储后端

#### Redis

仅需非常简单的配置，即可连接到 Redis 的单例模式、哨兵模式和集群模式。

下方样例使用 Redis 作为存储后端，`options` 支持 Redis 的所有配置项，详见 [RedisStore Options](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#redisstore-options)。

```python
from throttled import RateLimiterType, Throttled, rate_limiter, store

@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limiter.per_min(1),
    # 🌟 使用 Redis 作为存储后端
    store=store.RedisStore(
        # 单例模式
        server="redis://127.0.0.1:6379/0",
        # 哨兵模式
        # server="redis+sentinel://:yourpassword@host1:26379,host2:26379/mymaster"
        # 集群模式
        # server="redis+cluster://:yourpassword@host1:6379,host2:6379",
        options={}
    ),
)
def products() -> list:
    return [{"name": "iPhone"}, {"name": "MacBook"}]

products()
# raise LimitedError: Rate limit exceeded: remaining=0, reset_after=60
products()
```

#### Memory

当没有指定存储后端时，会默认使用最大容量为 1024 的全局 `MemoryStore` 实例作为存储后端，因此**通常不需要手动创建** `MemoryStore` 实例。

不同的 `MemoryStore` 实例意味着不同的存储空间，如果你希望在程序的不同位置，对同一个 Key 进行限流，请确保 `Throttled` 接收到的是同一个 `MemoryStore`，并使用一致的 [`Quota`](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#3quota)。

下方样例使用内存作为存储后端，并在 `ping`、`pong` 上对同一个 Key 进行限流：

```python
from throttled import Throttled, rate_limiter, store

# 🌟 使用 Memory 作为存储后端
mem_store = store.MemoryStore()

@Throttled(key="ping-pong", quota=rate_limiter.per_min(1), store=mem_store)
def ping() -> str:
    return "ping"

@Throttled(key="ping-pong", quota=rate_limiter.per_min(1), store=mem_store)
def pong() -> str:
    return "pong"
  
ping()
# raise LimitedError: Rate limit exceeded: remaining=0, reset_after=60
pong()
```

### 3）指定限流算法

通过 **`using`** 参数指定限流算法，支持算法如下：

* [固定窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8)：`RateLimiterType.FIXED_WINDOW.value`
* [滑动窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3)：`RateLimiterType.SLIDING_WINDOW.value`
* [令牌桶](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6)：`RateLimiterType.TOKEN_BUCKET.value`
* [漏桶](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6)：`RateLimiterType.LEAKING_BUCKET.value`
* [通用信元速率算法（Generic Cell Rate Algorithm, GCRA）](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra)：`RateLimiterType.GCRA.value`

```python
from throttled import RateLimiterType, Throttled, rate_limiter

throttle = Throttled(
    # 🌟指定限流算法
    using=RateLimiterType.FIXED_WINDOW.value,
    quota=rate_limiter.per_min(1)
)
assert throttle.limit("key", 2).limited is True
```

### 4）指定容量

#### 快捷创建方式

```python
from throttled import rate_limiter

rate_limiter.per_sec(60)    # 60 req/sec
rate_limiter.per_min(60)    # 60 req/min
rate_limiter.per_hour(60)   # 60 req/hour
rate_limiter.per_day(60)    # 60 req/day
rate_limiter.per_week(60)   # 60 req/week
```

#### 调整突发限制

通过 **`burst`** 参数，可以调节限流对象处理突发流量的能力 ，对以下算法有效：

* `TOKEN_BUCKET`
* `LEAKING_BUCKET`
* `GCRA`

```python
from throttled import rate_limiter

# 允许突发处理 120 个请求。
# 未指定 burst 时，默认设置为 limit 传入值。
rate_limiter.per_min(60, burst=120)
```

#### 自定义配额

```python
from datetime import timedelta
from throttled import rate_limiter

# 两分钟一共允许 120 个请求，允许突发处理 150 个请求。
rate_limiter.per_duration(timedelta(minutes=2), limit=120, burst=150)
```


## ⚙️ 数据模型与配置

### 1）RateLimitResult

RateLimitResult 表示对给定 Key 执行 `limit` 操作后返回的结果。

| 字段        | 类型             | 描述                 |
|-----------|----------------|--------------------|
| `limited` | bool           | 表示此次请求是否被允许通过。     |
| `state`   | RateLimitState | 表示给定 Key 的限流器当前状态。 |

### 2）RateLimitState

RateLimitState 表示给定 Key 的限流器当前状态。

| 字段            | 类型    | 描述                                                      |
|---------------|-------|---------------------------------------------------------|
| `limit`       | int   | 表示在初始状态下允许通过的最大请求数量。                                    |
| `remaining`   | int   | 表示在当前状态下，针对给定键允许通过的最大请求数量。                              |
| `reset_after` | float | 表示限流器恢复到初始状态所需的时间（以秒为单位）。在初始状态下，`limit` 等于 `remaining`。 |
| `retry_after` | float | 表示被拒绝请求的重试等待时间（以秒为单位），请求允许通过时，`retry_after` 为 0。        |

### 3）Quota

Quota 表示限流配额（基础速率 + 突发容量）。

| 字段      | 类型   | 描述                                                                                  |
|---------|------|-------------------------------------------------------------------------------------|
| `burst` | int  | 突发容量配置（可临时突破基础速率限制），仅对以下算法生效：<br />`TOEKN_BUCKET`<br />`LEAKING_BUCKET`<br />`GCRA` |
| `rate`  | Rate | 基础速率配置。                                                                             |

### 4）Rate

Rate 表示限流速率配置（(时间窗口内允许的请求量）。

| 字段       | 类型                 | 描述             |
|----------|--------------------|----------------|
| `period` | datetime.timedelta | 限流时间窗口。        |
| `limit`  | Rate               | 时间窗口内允许的最大请求数。 |

### 5）Store

#### 通用参数

| 参数        | 描述                                    | 默认值                          |
|-----------|---------------------------------------|------------------------------|
| `server`  | 标准的 Redis URL，你可以使用它连接到任何 Redis 部署模式。 | `"redis://localhost:6379/0"` |
| `options` | 存储相关配置项，见下文。                          | `{}`                         |

#### RedisStore Options

RedisStore 基于 [redis-py](https://github.com/redis/redis-py) 提供的 Redis API 进行开发。

在 Redis 连接配置管理上，基本沿用 [django-redis](https://github.com/jazzband/django-redis) 的配置命名，减少学习成本。


| 参数                         | 描述                                                                                                                                   | 默认值                                                                                                                                                                                                                                                                                                                                        |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `SOCKET_TIMEOUT`           | ConnectionPool 参数。                                                                                                                   | `null`                                                                                                                                                                                                                                                                                                                                     |
| `SOCKET_CONNECT_TIMEOUT`   | ConnectionPool 参数。                                                                                                                   |                                                                                                                                                                                                                                                                                                                                            |
| `CONNECTION_POOL_KWARGS`   | [ConnectionPool 构造参数](https://redis.readthedocs.io/en/stable/connections.html#connectionpool)。                                       | `{}`                                                                                                                                                                                                                                                                                                                                       |
| `REDIS_CLIENT_KWARGS`      | [RedisClient 构造参数](https://redis.readthedocs.io/en/stable/connections.html#redis.Redis)。                                             | `{}`                                                                                                                                                                                                                                                                                                                                       |
| `SENTINEL_KWARGS`          | [Sentinel 构造参数](https://redis.readthedocs.io/en/stable/connections.html#id1)。                                                        | `{}`                                                                                                                                                                                                                                                                                                                                       |
| `CONNECTION_FACTORY_CLASS` | ConnectionFactory 用于创建和维护 [ConnectionPool](https://redis.readthedocs.io/en/stable/connections.html#redis.connection.ConnectionPool)。 | 默认通过 `server` scheme 自动选择。<br />Standalone: `"throttled.store.ConnectionFactory"` <br />Sentinel:`"throttled.store.SentinelConnectionFactory"`<br />Cluster: `"throttled.store.ClusterConnectionFactory"`                                                                                                                                  |
| `REDIS_CLIENT_CLASS`       | RedisClient 导入路径。                                                                                                                    | 默认通过 sync/async 模式自动选择。<br />Sync(Standalone/Sentinel): `"redis.client.Redis"`<br />Async(Standalone/Sentinel): `"redis.asyncio.client.Redis"`<br />Sync(Cluster): ``"redis.cluster.RedisCluster"``<br />Async(Cluster): ``"redis.asyncio.cluster.RedisCluster"``                                                                          |
| `CONNECTION_POOL_CLASS`    | ConnectionPool 导入路径。                                                                                                                 | 默认通过 `server` scheme 和 sync/async 模式自动选择。<br />Sync(Standalone): `"redis.connection.ConnectionPool"`<br />Async(Standalone): `"redis.asyncio.connection.ConnectionPool"`<br />Sync(Sentinel): `"redis.sentinel.SentinelConnectionPool"`<br />Async(Sentinel): `"redis.asyncio.sentinel.SentinelConnectionPool"`<br />Cluster: `"Disabled"` |
| `SENTINEL_CLASS`           | Sentinel 导入路径。                                                                                                                       | 默认通过 sync/async 模式自动选择。<br />Sync: `"redis.Sentinel"`<br />Async: `"redis.asyncio.Sentinel"`                                                                                                                                                                                                                                               |


#### MemoryStore Options

MemoryStore 本质是一个基于内存实现的，带过期时间的 [LRU Cache](https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU) 。

| 参数         | 描述                                        | 默认值    |
|------------|-------------------------------------------|--------|
| `MAX_SIZE` | 最大容量，存储的键值对数量超过 `MAX_SIZE` 时，将按 LRU 策略淘汰。 | `1024` |


### 6）Exception

所有异常都继承自 `throttled.exceptions.BaseThrottledError`。

#### LimitedError

当请求被限流时抛出该异常，例如：`Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.`。

| 字段                  | 类型                | 描述                             |
|---------------------|-------------------|--------------------------------|
| `rate_limit_result` | `RateLimitResult` | 表示对给定 Key 执行 `limit` 操作后返回的结果。 |

#### DataError

参数错误时抛出该异常，例如：`Invalid key: None, must be a non-empty key.`。


## 📊 Benchmarks

### 1）环境

- **Python 版本：** Python 3.13.1 (CPython)
- **系统：** macOS Darwin 23.6.0 (arm64)
- **Redis 版本：** Redis 7.x（本地连接）

### 2）性能
> 单位：吞吐量 req/s，延迟 ms/op。

| 算法类型           | 内存（串行）                 | 内存（并发，16 线程）               | Redis（串行）           | Redis（并发，16 线程）     |
|----------------|------------------------|----------------------------|---------------------|---------------------|
| **对比基准** *[1]* | **1,692,307 / 0.0002** | **135,018 / 0.0004** *[2]* | **17,324 / 0.0571** | **16,803 / 0.9478** |
| 固定窗口           | 369,635 / 0.0023       | 57,275 / 0.2533            | 16,233 / 0.0610     | 15,835 / 1.0070     |
| 滑动窗口           | 265,215 / 0.0034       | 49,721 / 0.2996            | 12,605 / 0.0786     | 13,371 / 1.1923     |
| 令牌桶            | 365,678 / 0.0023       | 54,597 / 0.2821            | 13,643 / 0.0727     | 13,219 / 1.2057     |
| 漏桶             | 364,296 / 0.0023       | 54,136 / 0.2887            | 13,628 / 0.0727     | 12,579 / 1.2667     |
| GCRA           | 373,906 / 0.0023       | 53,994 / 0.2895            | 12,901 / 0.0769     | 12,861 / 1.2391     |

* *[1] 对比基准：内存 - `dict[key] += 1`，Redis - `INCRBY key increment`。*
* *[2] 在内存并发对比基准中，使用 `threading.RLock` 保证线程安全。*
* *[3] 性能：内存 - 约等于 2.5 ~ 4.5 次 `dict[key] += 1` 操作，Redis - 约等于 1.06 ~ 1.37 次 `INCRBY key increment` 操作。*
* *[4] Benchmarks 程序：[tests/benchmarks/test_throttled.py](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/tests/benchmarks/test_throttled.py)。*


## 🍃 灵感

[Rate Limiting, Cells, and GCRA](https://brandur.org/rate-limiting), by [Brandur Leach](https://github.com/brandur)


## 📚 Version History

[See CHANGELOG](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst)


## 📄 License

[The MIT License](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/LICENSE)
