import copy
import urllib.parse
from typing import Any, Generic, cast

from .. import types
from ..constants import StoreType
from ..exceptions import DataError
from ..utils import format_kv, format_value
from .base import BaseStore, BaseStoreBackend
from .redis_pool import BaseConnectionFactory, get_connection_factory


class BaseRedisStoreBackend(
    BaseStoreBackend[types.RedisClientT], Generic[types.RedisClientT]
):
    """Base backend for Redis store."""

    @classmethod
    def _parse_auth(cls, parsed: urllib.parse.ParseResult) -> dict[str, str]:
        auth_info: dict[str, str] = {}
        if parsed.username:
            auth_info["username"] = str(parsed.username)
        if parsed.password:
            auth_info["password"] = str(parsed.password)
        return auth_info

    @classmethod
    def _parse_nodes(
        cls, parsed: urllib.parse.ParseResult, default_port: int = 6379
    ) -> list[tuple[str, int]]:
        nodes: list[tuple[str, int]] = []
        idx: int = parsed.netloc.find("@") + 1
        for node in parsed.netloc[idx:].split(","):
            node_tuple: list[str] = node.rsplit(":", 1)
            host: str = node_tuple[0]
            port: int = default_port if len(node_tuple) == 1 else int(node_tuple[1])
            nodes.append((host, port))
        return nodes

    @classmethod
    def _set_options(cls, options: dict[str, Any]) -> None:
        pass

    @classmethod
    def _set_sentinel_options(cls, options: dict[str, Any]) -> None:
        options.setdefault(
            "CONNECTION_FACTORY_CLASS", "throttled.store.SentinelConnectionFactory"
        )

    @classmethod
    def _set_cluster_options(cls, options: dict[str, Any]) -> None:
        options.setdefault(
            "CONNECTION_FACTORY_CLASS",
            "throttled.store.ClusterConnectionFactory",
        )

    @classmethod
    def _set_standalone_options(cls, options: dict[str, Any]) -> None:
        pass

    @classmethod
    def _parse(
        cls, server: str | None = None, options: dict[str, Any] | None = None
    ) -> tuple[str | None, dict[str, Any]]:
        parsed_options: dict[str, Any] = copy.deepcopy(options or {})
        parsed_server: str | None = server
        if not server:
            cls._set_options(parsed_options)
            cls._set_standalone_options(parsed_options)
            return parsed_server, parsed_options

        if server.startswith("redis+sentinel://"):
            sentinel_parsed: urllib.parse.ParseResult = urllib.parse.urlparse(server)

            # If SENTINEL_KWARGS is not explicitly passed,
            # use the authentication information from the URL, SENTINEL_KWARGS
            # has a higher priority than the authentication information.
            sentinel_auth: dict[str, str] = cls._parse_auth(sentinel_parsed)
            parsed_options["SENTINEL_KWARGS"] = {
                **sentinel_auth,
                **(parsed_options.get("SENTINEL_KWARGS") or {}),
            }
            parsed_options.update({k.upper(): v for k, v in sentinel_auth.items()})

            parsed_options.setdefault("SENTINELS", []).extend(
                cls._parse_nodes(sentinel_parsed, default_port=26379)
            )
            cls._set_sentinel_options(parsed_options)

            service_name: str = (
                sentinel_parsed.path.lstrip("/") if sentinel_parsed.path else "mymaster"
            )
            parsed_server = f"redis://{service_name}/0"

        elif server.startswith("redis+cluster://"):
            cluster_parsed: urllib.parse.ParseResult = urllib.parse.urlparse(server)
            cluster_auth: dict[str, str] = cls._parse_auth(cluster_parsed)
            parsed_options.update({k.upper(): v for k, v in cluster_auth.items()})
            parsed_options.setdefault("CLUSTER_NODES", []).extend(
                cls._parse_nodes(cluster_parsed)
            )
            cls._set_cluster_options(parsed_options)
        else:
            cls._set_standalone_options(parsed_options)

        cls._set_options(parsed_options)
        return parsed_server, parsed_options

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().__init__(*self._parse(server, options))

        self._client: types.RedisClientT | None = None

        connection_factory_cls_path: str | None = self.options.get(
            "CONNECTION_FACTORY_CLASS"
        )
        self._connection_factory: BaseConnectionFactory = get_connection_factory(
            connection_factory_cls_path, self.options
        )

    def get_client(self) -> types.RedisClientT:
        if self._client is not None:
            return self._client

        # Cast once at the redis-py boundary: ``connect`` returns the untyped
        # ``RedisP`` union, narrow to the declared client protocol.
        client: types.RedisClientT = cast(
            "types.RedisClientT", self._connection_factory.connect(self.server)
        )
        self._client = client
        return client


class RedisStoreBackend(BaseRedisStoreBackend[types.SyncRedisClientP]):
    """Backend for sync Redis store."""


class RedisStore(BaseStore[RedisStoreBackend]):
    """Concrete implementation of BaseStore using Redis as backend.

    :class:`throttled.store.RedisStore` is implemented based on
    `redis-py <https://github.com/redis/redis-py>`_, you can use it for
    rate limiting in a distributed environment.
    """

    TYPE: str = StoreType.REDIS.value

    _BACKEND_CLASS: type[RedisStoreBackend] = RedisStoreBackend

    def __init__(
        self, server: str | None = None, options: dict[str, Any] | None = None
    ) -> None:
        """Initialize RedisStore.

        :param server: Redis Standard Redis URL, you can use it
            to connect to Redis in any deployment mode,
            see :ref:`Store Backends <store-backend-redis-standalone>`.
        :param options: Redis connection configuration, supports all
            configuration item of `redis-py <https://github.com/redis/redis-py>`_,
            see :ref:`RedisStore Options <store-configuration-redis-store-options>`.
        """
        super().__init__(server, options)
        self._backend: RedisStoreBackend = self._BACKEND_CLASS(server, options)

    def exists(self, key: types.KeyT) -> bool:
        return bool(self._backend.get_client().exists(key))

    def ttl(self, key: types.KeyT) -> int:
        return int(self._backend.get_client().ttl(key))

    def expire(self, key: types.KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().expire(key, timeout)

    def set(self, key: types.KeyT, value: types.StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().set(key, value, ex=timeout)

    def get(self, key: types.KeyT) -> types.StoreValueT | None:
        value: types.StoreValueT | None = self._backend.get_client().get(key)
        if value is None:
            return None
        return format_value(value)

    def hset(
        self,
        name: types.KeyT,
        key: types.KeyT | None = None,
        value: types.StoreValueT | None = None,
        mapping: types.StoreDictValueT | None = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")
        self._backend.get_client().hset(name, key, value, mapping)

    def hgetall(self, name: types.KeyT) -> types.StoreDictValueT:
        return format_kv(self._backend.get_client().hgetall(name))
