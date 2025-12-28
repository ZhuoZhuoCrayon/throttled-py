# Copyright (c) 2011-2016 Andrey Antukh <niwi@niwi.nz>
# Copyright (c) 2011 Sean Bleier
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS`` AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import abc
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult, ParseResultBytes, parse_qs, urlparse

from ..exceptions import SetUpError
from ..utils import import_string, to_bool

if TYPE_CHECKING:
    import redis
    import redis.asyncio as aioredis
    from redis.asyncio.cluster import ClusterNode as AsyncClusterNode
    from redis.asyncio.connection import DefaultParser as AsyncDefaultParser
    from redis.cluster import ClusterNode as SyncClusterNode
    from redis.connection import DefaultParser as SyncDefaultParser

    ConnectionPool = redis.ConnectionPool | aioredis.ConnectionPool
    Redis = redis.Redis | aioredis.Redis
    Sentinel = redis.Sentinel | aioredis.Sentinel
    ClusterNode = SyncClusterNode | AsyncClusterNode
    DefaultParser = SyncDefaultParser | AsyncDefaultParser


class BaseConnectionFactory(abc.ABC):
    """Base connection factory."""

    _pools: dict[str, "ConnectionPool"] = {}

    def __init__(self, options: dict[str, Any]):
        pool_cls_path: str = options.get("CONNECTION_POOL_CLASS", "redis.ConnectionPool")
        try:
            self.pool_cls: type[ConnectionPool] = import_string(pool_cls_path)
        except ImportError:
            raise ImportError(
                f"Could not import connection pool class '{pool_cls_path}', "
                f"possible reasons are: \n- The module does not exist.\n"
                f"- Redis storage backend requires extra dependencies, "
                f'please install with `pip install "throttled-py[redis]"`.'
            ) from None

        self.pool_cls_kwargs: dict[str, Any] = options.get("CONNECTION_POOL_KWARGS", {})

        self.redis_client_cls_path: str = options.get(
            "REDIS_CLIENT_CLASS", "redis.Redis"
        )
        self.redis_client_cls: type[Redis] = import_string(self.redis_client_cls_path)
        self.redis_client_cls_kwargs: dict[str, Any] = options.get(
            "REDIS_CLIENT_KWARGS", {}
        )

        parser_cls_path: str = options.get(
            "PARSER_CLASS", "redis.connection.DefaultParser"
        )
        self.parser_cls: type[DefaultParser] = import_string(parser_cls_path)

        self.options: dict[str, Any] = options

    @abc.abstractmethod
    def make_connection_params(self, url: str = None) -> dict[str, Any]:
        """Build a complete dict of connection parameters."""
        raise NotImplementedError

    @abc.abstractmethod
    def connect(self, url: str | None = None) -> "Redis":
        """Given a basic connection parameters, return a new connection."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_connection(self, params: dict[str, Any]) -> "Redis":
        """Given a now preformatted params, return a new connection.

        The default implementation uses a cached pools for create new connection.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_create_connection_pool(self, params: dict[str, Any]) -> "ConnectionPool":
        """Return a new or cached connection pool for the given parameters.

        Implement this method if you want distinct
        connection pool instance caching behavior.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_connection_pool(self, params: dict[str, Any]) -> "ConnectionPool":
        """Given a connection parameters, return a new connection pool for them.

        Implement this method if you want a custom behavior on creating connection pool.
        """
        raise NotImplementedError


class ConnectionFactory(BaseConnectionFactory):
    """Store connection pool by backend options.

    _pools is a process-global, as otherwise _pools is cleared every time.
    """

    DEFAULT_URL: str = "redis://localhost:6379/0"

    def make_connection_params(self, url: str | None = None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "url": url or self.DEFAULT_URL,
            "parser_class": self.parser_cls,
        }
        password: str | None = self.options.get("PASSWORD", None)
        if password:
            kwargs["password"] = password

        socket_timeout: Any = self.options.get("SOCKET_TIMEOUT", None)
        if socket_timeout:
            if not isinstance(socket_timeout, int | float):
                raise SetUpError("Socket timeout should be float or integer")
            kwargs["socket_timeout"] = socket_timeout

        socket_connect_timeout: Any = self.options.get("SOCKET_CONNECT_TIMEOUT", None)
        if socket_connect_timeout:
            if not isinstance(socket_connect_timeout, int | float):
                raise SetUpError("Socket connect timeout should be float or integer")
            kwargs["socket_connect_timeout"] = socket_connect_timeout

        return kwargs

    def connect(self, url: str | None = None) -> "Redis":
        params: dict[str, Any] = self.make_connection_params(url)
        return self.get_connection(params)

    def get_connection(self, params) -> "Redis":
        pool: ConnectionPool = self.get_or_create_connection_pool(params)
        return self.redis_client_cls(
            connection_pool=pool, **self.redis_client_cls_kwargs
        )

    def _get_pool_key(self, params: dict[str, Any]) -> str:
        """Generate a unique key for the connection pool based on parameters."""
        # Use redis client class path as part of the key, to avoid collisions
        # between different connection pool classes, e.g. Redis vs asyncio.Redis.
        return f"{self.redis_client_cls_path}:{params['url']}"

    def get_or_create_connection_pool(self, params: dict[str, Any]) -> "ConnectionPool":
        """Return a new or cached connection pool for the given parameters."""
        key: str = self._get_pool_key(params)

        # REUSE_CONNECTION: solve the problem of "redis attached to a different loop",
        # due to the fact that the connection pool is created in a different loop.
        if not self.options.get("REUSE_CONNECTION", True) or key not in self._pools:
            self._pools[key] = self.get_connection_pool(params)
        return self._pools[key]

    def get_connection_pool(self, params: dict[str, Any]) -> "ConnectionPool":
        cp_params: dict[str, Any] = dict(params)
        cp_params.update(self.pool_cls_kwargs)
        pool: ConnectionPool = self.pool_cls.from_url(**cp_params)

        if pool.connection_kwargs.get("password", None) is None:
            pool.connection_kwargs["password"] = params.get("password")
            pool.reset()

        return pool


class SentinelConnectionFactory(ConnectionFactory):
    """Connection factory for Redis Sentinel."""

    def __init__(self, options):
        # allow overriding the default SentinelConnectionPool class
        options.setdefault("CONNECTION_POOL_CLASS", "redis.SentinelConnectionPool")
        super().__init__(options)

        sentinels: list[tuple[str, str | int]] = options.get("SENTINELS")
        if not sentinels:
            raise SetUpError("SENTINELS must be provided as a list of (host, port).")

        self._sentinels_str: str = ",".join(f"{host}:{port}" for host, port in sentinels)

        # provide the connection pool kwargs to the sentinel in case it
        # needs to use the socket options for the sentinels themselves
        connection_kwargs = self.make_connection_params(None)
        connection_kwargs.pop("url")
        connection_kwargs.update(self.pool_cls_kwargs)

        sentinel_cls_path: str = options.get("SENTINEL_CLASS", "redis.Sentinel")
        sentinel_cls: type[Sentinel] = import_string(sentinel_cls_path)
        self._sentinel: Sentinel = sentinel_cls(
            sentinels,
            sentinel_kwargs=options.get("SENTINEL_KWARGS"),
            **connection_kwargs,
        )

    def _get_pool_key(self, params: dict[str, Any]) -> str:
        return f"{self.redis_client_cls_path}:{self._sentinels_str}:{params['url']}"

    def get_connection_pool(self, params: dict[str, Any]) -> "ConnectionPool":
        """Return a new sentinel connection pool for the given parameters."""
        url: ParseResult | ParseResultBytes = urlparse(params["url"])

        # explicitly set service_name and sentinel_manager for the
        # SentinelConnectionPool constructor since will be called by from_url.
        cp_params: dict[str, Any] = dict(params)
        cp_params.update(service_name=url.hostname, sentinel_manager=self._sentinel)
        pool: ConnectionPool = super().get_connection_pool(cp_params)

        # convert "is_master" to a boolean if set on the URL, otherwise if not
        # provided it defaults to True.
        is_master: str | None = parse_qs(url.query).get("is_master")
        if is_master:
            pool.is_master = to_bool(is_master[0])

        return pool


class ClusterConnectionFactory(ConnectionFactory):
    """Connection factory for Redis Cluster."""

    def __init__(self, options):
        options.setdefault("REDIS_CLIENT_CLASS", "redis.cluster.RedisCluster")
        options.setdefault("REDIS_CLUSTER_NODE_CLASS", "redis.cluster.ClusterNode")
        super().__init__(options)

        cluster_node_cls_path: str = options["REDIS_CLUSTER_NODE_CLASS"]
        cluster_node_cls: type[ClusterNode] = import_string(cluster_node_cls_path)

        self._startup_nodes: list[ClusterNode] = []
        for node in options.get("CLUSTER_NODES", []):
            self._startup_nodes.append(cluster_node_cls(*node))

    def get_connection(self, params) -> "Redis":
        params.pop("url", None)
        params.pop("parser_class", None)
        return self.redis_client_cls(
            startup_nodes=self._startup_nodes, **params, **self.redis_client_cls_kwargs
        )


def get_connection_factory(
    path: str | None = None, options: dict[str, Any] | None = None
) -> BaseConnectionFactory:
    """Return a ConnectionFactory instance given a class path and options."""
    # TODO read from env.
    default_path: str = "throttled.store.ConnectionFactory"
    cls: type[BaseConnectionFactory] = import_string(path or default_path)
    return cls(options or {})
