<h1 align="center">throttled-py</h1>
<p align="center">
    <em>🔧支持多种算法及存储的限流 Python 库，同时提供对 Django、Django REST Framework（DRF）、Flask 等框架友好的限流中间件，以便快速集成。</em>
</p>

[English Documents Available](./README.md) | 简体中文


## 🚀 功能

### 1）存储

- [x] Redis
- [x] 内存

### 2）限流算法

- [x] [固定窗口](https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8)
- [x] [滑动窗口]()
- [ ] 令牌桶
- [ ] 漏桶
- [ ] 通用信元速率算法（Generic Cell Rate Algorithm, GCRA）

### 3）周边生态

- [ ] Django
- [ ] Django REST Framework（DRF）
- [ ] Flask


## 🔰 安装

```shell
$ pip install throttled-py
```


## 📝 使用

## 📈 进阶

### 1）Store

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

