<h1 align="center">throttled-py</h1>
<p align="center">
    <em>🔧 支持多种算法（固定窗口，滑动窗口，令牌桶，漏桶 & GCRA）及存储（Redis、内存）的高性能 Python 限流库。</em>
</p>

<p align="center">
    <a href="https://github.com/ZhuoZhuoCrayon/throttled-py">
        <img src="https://badgen.net/badge/python/%3E=3.8/green?icon=github" alt="Python">
    </a>
     <a href="https://github.com/ZhuoZhuoCrayon/throttled-py">
        <img src="https://codecov.io/gh/ZhuoZhuoCrayon/throttled-py/graph/badge.svg" alt="Coverage Status">
    </a>
</p>

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_EN.md) | 简体中文


## 🚀 功能

### 1）存储

| Redis | 内存（线程安全） |
|-------|----------|
| ✅     | ✅        |

### 2）限流算法

| [固定窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8) | [滑动窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3) | [令牌桶](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6) | [漏桶](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6) | [通用信元速率算法（Generic Cell Rate Algorithm, GCRA）](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra) |
|------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| ✅                                                                                                                                              | ✅                                                                                                                             | ✅                                                                                                                   | ✅                                                                                                         | ✅                                                                                                                                    |

我们提供以上限流算法的原理分析，你可以点击具体的限流算法跳转到相应的介绍。


## 🔰 安装

```shell
$ pip install throttled-py
```


## 📝 使用

### 1）基础

#### 通用 API

* `limit`：消耗请求，返回 [**RateLimitResult**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1ratelimitresult)。
* `peek`：获取指定 Key 的限流器状态，返回 [**RateLimitState**](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#2ratelimitstate)。

```python
from throttled import Throttled

# 参数全部缺省时，默认初始化一个基于「内存」、每分钟允许通过 60 个请求、使用「令牌桶算法」的限流器。
throttle = Throttled()

# 消耗 1 次请求，输出：RateLimitResult(limited=False,
# state=RateLimitState(limit=60, remaining=59, reset_after=1))
print(throttle.limit("key", 1))
# 获取限流器状态，输出：RateLimitState(limit=60, remaining=59, reset_after=1)
print(throttle.peek("key"))

# 消耗 60 次请求，触发限流，输出：RateLimitResult(limited=True,
# state=RateLimitState(limit=60, remaining=59, reset_after=1))
print(throttle.limit("key", 60))
```

#### 作为装饰器

```python
from throttled import Throttled, rate_limter, exceptions

# 创建一个每秒允许通过 1 次的限流器。
@Throttled(key="/ping", quota=rate_limter.per_min(1))
def ping() -> str:
    return "ping"

ping()

try:
    # 当触发限流时，抛出 LimitedError。
    ping()
except exceptions.LimitedError as exc:
    # Rate limit exceeded: remaining=0, reset_after=60
    print(exc)
    # 在异常中获取限流结果：RateLimitResult(limited=True, 
    # state=RateLimitState(limit=1, remaining=0, reset_after=60))
    print(exc.rate_limit_result)
```

### 2）指定存储后端

#### Redis

```python
from throttled import RateLimiterType, Throttled, rate_limter, store

@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limter.per_min(1),
    # 🌟 使用 Redis 作为存储后端
    store=store.RedisStore(server="redis://127.0.0.1:6379/0", options={"PASSWORD": ""}),
)
def products() -> list:
    return [{"name": "iPhone"}, {"name": "MacBook"}]

products()
# raise LimitedError: Rate limit exceeded: remaining=0, reset_after=60
products()
```

#### Memory

如果你希望在程序的不同位置，对同一个 Key 进行限流，请确保 `Throttled` 接收到的是同一个 `MemoryStore`，并使用一致的 [`Quota`](https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#3quota)。

下方样例使用内存作为存储后端，并在 `ping`、`pong` 上对同一个 Key 进行限流：

```python
from throttled import Throttled, rate_limter, store

# 🌟 使用 Memory 作为存储后端
mem_store = store.MemoryStore()

@Throttled(key="ping-pong", quota=rate_limter.per_min(1), store=mem_store)
def ping() -> str:
    return "ping"

@Throttled(key="ping-pong", quota=rate_limter.per_min(1), store=mem_store)
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
from throttled import RateLimiterType, Throttled, rate_limter, store

throttle = Throttled(
    # 🌟指定限流算法
    using=RateLimiterType.FIXED_WINDOW.value,
    quota=rate_limter.per_min(1),
    store=store.MemoryStore()
)
assert throttle.limit("key", 2).limited is True
```

### 4）指定容量

#### 快捷创建方式

```python
from throttled import rate_limter

rate_limter.per_sec(60)   # 60 / sec
rate_limter.per_min(60)   # 60 / min
rate_limter.per_hour(60)  # 60 / hour
rate_limter.per_day(60)   # 60 / day
```

#### 调整突发限制

通过 **`burst`** 参数，可以调节限流对象处理突发流量的能力 ，对以下算法有效：

* `TOKEN_BUCKET`
* `LEAKING_BUCKET`
* `GCRA`

```python
from throttled import rate_limter

# 允许突发处理 120 个请求
# 未指定 burst 时，默认设置为 limit 传入值
rate_limter.per_min(60, burst=120)
```

#### 自定义配额

```python
from datetime import timedelta
from throttled.rate_limter import Quota, Rate

# 两分钟一共允许 120 个请求，允许突发处理 150 个请求
Quota(Rate(period=timedelta(minutes=2), limit=120), burst=150)
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

| 参数        | 描述                                                                                                  | 默认值                          |
|-----------|-----------------------------------------------------------------------------------------------------|------------------------------|
| `server`  | 标准的 [Redis URL](https://github.com/redis/lettuce/wiki/Redis-URI-and-connection-details#uri-syntax)。 | `"redis://localhost:6379/0"` |
| `options` | 存储相关配置项，见下文。                                                                                        | `{}`                         |

#### RedisStore Options

RedisStore 基于 [redis-py](https://github.com/redis/redis-py) 提供的 Redis API 进行开发。

在 Redis 连接配置管理上，基本沿用 [django-redis](https://github.com/jazzband/django-redis) 的配置命名，减少学习成本。

| 参数                         | 描述                                                                                                                                      | 默认值                                   |
|----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| `CONNECTION_FACTORY_CLASS` | ConnectionFactory 用于创建并维护 [ConnectionPool](https://redis-py.readthedocs.io/en/stable/connections.html#redis.connection.ConnectionPool)。 | `"throttled.store.ConnectionFactory"` |
| `CONNECTION_POOL_CLASS`    | ConnectionPool 导入路径。                                                                                                                    | `"redis.connection.ConnectionPool"`   |
| `CONNECTION_POOL_KWARGS`   | [ConnectionPool 构造参数](https://redis-py.readthedocs.io/en/stable/connections.html#connectionpool)。                                       | `{}`                                  |
| `REDIS_CLIENT_CLASS`       | RedisClient 导入路径，默认使用 [redis.client.Redis](https://redis-py.readthedocs.io/en/stable/connections.html#redis.Redis)。                     | `"redis.client.Redis"`                |
| `REDIS_CLIENT_KWARGS`      | [RedisClient 构造参数](https://redis-py.readthedocs.io/en/stable/connections.html#redis.Redis)。                                             | `{}`                                  |
| `PASSWORD`                 | 密码。                                                                                                                                     | `null`                                |
| `SOCKET_TIMEOUT`           | ConnectionPool 参数。                                                                                                                      | `null`                                |
| `SOCKET_CONNECT_TIMEOUT`   | ConnectionPool 参数。                                                                                                                      | `null`                                |
| `SENTINELS`                | `(host, port)` 元组列表，哨兵模式请使用 `SentinelConnectionFactory` 并提供该配置。                                                                         | `[]`                                  |
| `SENTINEL_KWARGS`          | [Sentinel 构造参数](https://redis-py.readthedocs.io/en/stable/connections.html#id1)。                                                        | `{}`                                  |

#### MemoryStore Options

MemoryStore 本质是一个基于内存实现的，带过期时间的 [LRU Cache](https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU) 。

| 参数         | 描述                                        | 默认值    |
|------------|-------------------------------------------|--------|
| `MAX_SIZE` | 最大容量，存储的键值对数量超过 `MAX_SIZE` 时，将按 LRU 策略淘汰。 | `1024` |


## 📚 Version History

[See CHANGELOG.md](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md)

## 📄 License

[The MIT License](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/LICENSE)
