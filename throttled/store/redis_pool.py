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
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from urllib.parse import ParseResult, ParseResultBytes, parse_qs, urlparse

from redis import ConnectionPool, Redis, Sentinel
from redis.connection import DefaultParser, to_bool

from throttled.exceptions import SetUpError
from throttled.utils import import_string


class BaseConnectionFactory(abc.ABC):
    """Base connection factory."""

    _pools: Dict[str, ConnectionPool] = {}

    def __init__(self, options: Dict[str, Any]):
        pool_cls_path: str = options.get(
            "CONNECTION_POOL_CLASS", "redis.connection.ConnectionPool"
        )
        self.pool_cls: Type[ConnectionPool] = import_string(pool_cls_path)
        self.pool_cls_kwargs: Dict[str, Any] = options.get("CONNECTION_POOL_KWARGS", {})

        redis_client_cls_path: str = options.get(
            "REDIS_CLIENT_CLASS", "redis.client.Redis"
        )
        self.redis_client_cls: Type[Redis] = import_string(redis_client_cls_path)
        self.redis_client_cls_kwargs: Dict[str, Any] = options.get(
            "REDIS_CLIENT_KWARGS", {}
        )

        self.options: Dict[str, Any] = options

    @abc.abstractmethod
    def make_connection_params(self, url: str = None) -> Dict[str, Any]:
        """Given a main connection parameters, build a complete dict of
        connection parameters.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def connect(self, url: Optional[str] = None) -> Redis:
        """Given a basic connection parameters, return a new connection."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_connection(self, params: Dict[str, Any]) -> Redis:
        """Given a now preformatted params, return a new connection.
        The default implementation uses a cached pools for create new connection.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_create_connection_pool(self, params: Dict[str, Any]) -> ConnectionPool:
        """
        Given a connection parameters and return a new
        or cached connection pool for them.

        Implement this method if you want distinct
        connection pool instance caching behavior.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_connection_pool(self, params: Dict[str, Any]) -> ConnectionPool:
        """
        Given a connection parameters, return a new connection pool for them.
        Implement this method if you want a custom behavior on creating connection pool.
        """
        raise NotImplementedError


class ConnectionFactory(BaseConnectionFactory):
    """Store connection pool by backend options.
    _pools is a process-global, as otherwise _pools is cleared every time.
    """

    DEFAULT_URL: str = "redis://localhost:6379/0"

    def make_connection_params(self, url: Optional[str] = None) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "url": url or self.DEFAULT_URL,
            "parser_class": self.get_parser_cls(),
        }
        password: Optional[str] = self.options.get("PASSWORD", None)
        if password:
            kwargs["password"] = password

        socket_timeout: Any = self.options.get("SOCKET_TIMEOUT", None)
        if socket_timeout:
            if not isinstance(socket_timeout, (int, float)):
                raise SetUpError("Socket timeout should be float or integer")
            kwargs["socket_timeout"] = socket_timeout

        socket_connect_timeout: Any = self.options.get("SOCKET_CONNECT_TIMEOUT", None)
        if socket_connect_timeout:
            if not isinstance(socket_connect_timeout, (int, float)):
                raise SetUpError("Socket connect timeout should be float or integer")
            kwargs["socket_connect_timeout"] = socket_connect_timeout

        return kwargs

    def connect(self, url: Optional[str] = None) -> Redis:
        params: Dict[str, Any] = self.make_connection_params(url)
        return self.get_connection(params)

    def get_connection(self, params) -> Redis:
        pool: ConnectionPool = self.get_or_create_connection_pool(params)
        return self.redis_client_cls(
            connection_pool=pool, **self.redis_client_cls_kwargs
        )

    def get_parser_cls(self) -> Type[DefaultParser]:
        parser_cls_path: Optional[str] = self.options.get("PARSER_CLASS", None)
        if parser_cls_path is None:
            return DefaultParser
        return import_string(parser_cls_path)

    def get_or_create_connection_pool(self, params: Dict[str, Any]) -> ConnectionPool:
        key: str = params["url"]
        if key not in self._pools:
            self._pools[key] = self.get_connection_pool(params)
        return self._pools[key]

    def get_connection_pool(self, params: Dict[str, Any]) -> ConnectionPool:
        cp_params: Dict[str, Any] = dict(params)
        cp_params.update(self.pool_cls_kwargs)
        pool: ConnectionPool = self.pool_cls.from_url(**cp_params)

        if pool.connection_kwargs.get("password", None) is None:
            pool.connection_kwargs["password"] = params.get("password", None)
            pool.reset()

        return pool


class SentinelConnectionFactory(ConnectionFactory):
    def __init__(self, options):
        # allow overriding the default SentinelConnectionPool class
        options.setdefault(
            "CONNECTION_POOL_CLASS", "redis.sentinel.SentinelConnectionPool"
        )
        super().__init__(options)

        sentinels: List[Tuple[str, Union[str, int]]] = options.get("SENTINELS")
        if not sentinels:
            raise SetUpError("SENTINELS must be provided as a list of (host, port).")

        # provide the connection pool kwargs to the sentinel in case it
        # needs to use the socket options for the sentinels themselves
        connection_kwargs = self.make_connection_params(None)
        connection_kwargs.pop("url")
        connection_kwargs.update(self.pool_cls_kwargs)
        self._sentinel: Sentinel = Sentinel(
            sentinels,
            sentinel_kwargs=options.get("SENTINEL_KWARGS"),
            **connection_kwargs,
        )

    def get_connection_pool(self, params: Dict[str, Any]) -> ConnectionPool:
        """Given a connection parameters, return a new sentinel connection
        pool for them."""
        url: Union[ParseResult, ParseResultBytes] = urlparse(params["url"])

        # explicitly set service_name and sentinel_manager for the
        # SentinelConnectionPool constructor since will be called by from_url.
        cp_params: Dict[str, Any] = dict(params)
        cp_params.update(service_name=url.hostname, sentinel_manager=self._sentinel)
        pool: ConnectionPool = super().get_connection_pool(cp_params)

        # convert "is_master" to a boolean if set on the URL, otherwise if not
        # provided it defaults to True.
        is_master: Optional[str] = parse_qs(url.query).get("is_master")
        if is_master:
            pool.is_master = to_bool(is_master[0])

        return pool


def get_connection_factory(
    path: Optional[str] = None, options: Optional[Dict[str, Any]] = None
) -> BaseConnectionFactory:
    """Given a ConnectionFactory class path and options,
    return a ConnectionFactory instance."""
    # TODO read from env.
    default_path: str = "throttled.store.ConnectionFactory"
    cls: Type[BaseConnectionFactory] = import_string(path or default_path)
    return cls(options or {})
