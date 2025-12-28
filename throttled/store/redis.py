import copy
import urllib.parse
from typing import TYPE_CHECKING, Any

from ..constants import StoreType
from ..exceptions import DataError
from ..types import AtomicActionP, KeyT, StoreDictValueT, StoreValueT
from ..utils import format_kv, format_value
from .base import BaseStore, BaseStoreBackend
from .redis_pool import BaseConnectionFactory, get_connection_factory

if TYPE_CHECKING:
    import redis
    import redis.asyncio as aioredis

    Redis = redis.Redis | aioredis.Redis


class RedisStoreBackend(BaseStoreBackend):
    """Backend for Redis store."""

    @classmethod
    def _parse_auth(cls, parsed: urllib.parse.ParseResult) -> dict[str, str]:
        auth_info: dict[str, str] = {}
        if parsed.username:
            auth_info["username"] = parsed.username
        if parsed.password:
            auth_info["password"] = parsed.password
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
    def _set_options(cls, options: dict[str, Any]):
        pass

    @classmethod
    def _set_sentinel_options(cls, options: dict[str, Any]):
        options.setdefault(
            "CONNECTION_FACTORY_CLASS", "throttled.store.SentinelConnectionFactory"
        )

    @classmethod
    def _set_cluster_options(cls, options: dict[str, Any]):
        options.setdefault(
            "CONNECTION_FACTORY_CLASS",
            "throttled.store.ClusterConnectionFactory",
        )

    @classmethod
    def _set_standalone_options(cls, options: dict[str, Any]):
        pass

    @classmethod
    def _parse(
        cls, server: str | None = None, options: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        options: dict[str, Any] = copy.deepcopy(options or {})
        if not server:
            cls._set_options(options)
            cls._set_standalone_options(options)
            return server, options

        if server.startswith("redis+sentinel://"):
            parsed: urllib.parse.ParseResult = urllib.parse.urlparse(server)

            # If SENTINEL_KWARGS is not explicitly passed,
            # use the authentication information from the URL, SENTINEL_KWARGS
            # has a higher priority than the authentication information.
            auth_info: dict[str, str] = cls._parse_auth(parsed)
            options["SENTINEL_KWARGS"] = {
                **auth_info,
                **(options.get("SENTINEL_KWARGS") or {}),
            }
            options.update({k.upper(): v for k, v in auth_info.items()})

            options.setdefault("SENTINELS", []).extend(
                cls._parse_nodes(parsed, default_port=26379)
            )
            cls._set_sentinel_options(options)

            service_name: str = parsed.path.lstrip("/") if parsed.path else "mymaster"
            server = f"redis://{service_name}/0"

        elif server.startswith("redis+cluster://"):
            parsed: urllib.parse.ParseResult = urllib.parse.urlparse(server)
            auth_info: dict[str, str] = cls._parse_auth(parsed)
            options.update({k.upper(): v for k, v in auth_info.items()})
            options.setdefault("CLUSTER_NODES", []).extend(cls._parse_nodes(parsed))
            cls._set_cluster_options(options)
        else:
            cls._set_standalone_options(options)

        cls._set_options(options)
        return server, options

    def __init__(self, server: str | None = None, options: dict[str, Any] | None = None):
        super().__init__(*self._parse(server, options))

        self._client: Redis | None = None

        connection_factory_cls_path: str | None = self.options.get(
            "CONNECTION_FACTORY_CLASS"
        )
        self._connection_factory: BaseConnectionFactory = get_connection_factory(
            connection_factory_cls_path, self.options
        )

    def get_client(self) -> "Redis":
        if self._client is None:
            self._client = self._connection_factory.connect(self.server)
        return self._client


class RedisStore(BaseStore):
    """Concrete implementation of BaseStore using Redis as backend.

    :class:`throttled.store.RedisStore` is implemented based on
    `redis-py <https://github.com/redis/redis-py>`_, you can use it for
    rate limiting in a distributed environment.
    """

    TYPE: str = StoreType.REDIS.value

    _BACKEND_CLASS: type[RedisStoreBackend] = RedisStoreBackend

    def __init__(self, server: str | None = None, options: dict[str, Any] | None = None):
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

    def exists(self, key: KeyT) -> bool:
        return bool(self._backend.get_client().exists(key))

    def ttl(self, key: KeyT) -> int:
        return int(self._backend.get_client().ttl(key))

    def expire(self, key: KeyT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().expire(key, timeout)

    def set(self, key: KeyT, value: StoreValueT, timeout: int) -> None:
        self._validate_timeout(timeout)
        self._backend.get_client().set(key, value, ex=timeout)

    def get(self, key: KeyT) -> StoreValueT | None:
        value: StoreValueT | None = self._backend.get_client().get(key)
        if value is None:
            return None

        return format_value(value)

    def hset(
        self,
        name: KeyT,
        key: KeyT | None = None,
        value: StoreValueT | None = None,
        mapping: StoreDictValueT | None = None,
    ) -> None:
        if key is None and not mapping:
            raise DataError("hset must with key value pairs")
        self._backend.get_client().hset(name, key, value, mapping)

    def hgetall(self, name: KeyT) -> StoreDictValueT:
        return format_kv(self._backend.get_client().hgetall(name))

    def make_atomic(self, action_cls: type[AtomicActionP]) -> AtomicActionP:
        return action_cls(backend=self._backend)
