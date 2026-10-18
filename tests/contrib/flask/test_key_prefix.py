from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from flask import Flask
from throttled.contrib.flask import Limiter
from throttled.contrib.flask.keys import KeyParts, compose_key
from throttled.exceptions import DataError
from throttled.store import MemoryStore

from .conftest import ALGORITHMS

if TYPE_CHECKING:
    from collections.abc import Callable


_ROUTE = "/items"
_USER_ID = "user-1"

_SCHEMA_VERSION = "v1"
_DEFAULT_NAMESPACE = "throttled"


def _logical_key(
    method: str = "GET",
    route: str = _ROUTE,
) -> str:
    return compose_key(KeyParts(method=method, route=route, principal=_USER_ID))


def _physical_key(
    namespace: str,
    algorithm: str = "token_bucket",
) -> str:
    return f"{namespace}:{_SCHEMA_VERSION}:{algorithm}:{_logical_key()}"


def _stored_keys(store: MemoryStore) -> list[str]:
    return list(store._backend.get_client().keys())


def _get_user_id() -> str:
    return _USER_ID


def _register_items_endpoint(
    app: Flask,
    limiter: Limiter,
) -> None:
    @app.get(_ROUTE)
    @limiter.limit(key_func=_get_user_id)
    def list_items() -> dict[str, bool]:
        return {"ok": True}


def _build_limited_app(
    store: MemoryStore,
    *,
    key_prefix: str | None = None,
) -> Flask:
    limiter = Limiter(
        "1/m",
        store=store,
        using="fixed_window",
        key_prefix=key_prefix,
    )
    app = Flask(__name__)
    limiter.init_app(app)
    _register_items_endpoint(app, limiter)
    return app


class TestKeyPrefixStorageLayout:
    @classmethod
    def test_key_prefix__omitted__keeps_default_namespace(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        store = MemoryStore()
        app, limiter = build_app("2/s", store=store)
        _register_items_endpoint(app, limiter)

        assert app.test_client().get(_ROUTE).status_code == HTTPStatus.OK
        assert store.exists(_physical_key(_DEFAULT_NAMESPACE))

    @classmethod
    def test_key_prefix__set__replaces_only_the_namespace(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        store = MemoryStore()
        app, limiter = build_app("2/s", store=store, key_prefix="myapp")
        _register_items_endpoint(app, limiter)

        assert app.test_client().get(_ROUTE).status_code == HTTPStatus.OK
        assert store.exists(_physical_key("myapp"))
        assert not store.exists(_physical_key(_DEFAULT_NAMESPACE))

    @classmethod
    @pytest.mark.parametrize("algorithm", ALGORITHMS)
    def test_key_prefix__set__still_separates_algorithms(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
        algorithm: str,
    ) -> None:
        store = MemoryStore()
        app, limiter = build_app("2/s", store=store, key_prefix="myapp", using=algorithm)
        _register_items_endpoint(app, limiter)

        assert app.test_client().get(_ROUTE).status_code == HTTPStatus.OK
        keys: list[str] = _stored_keys(store)
        assert keys
        namespace: str = f"myapp:{_SCHEMA_VERSION}:{algorithm}:"
        assert all(key.startswith(namespace) for key in keys)
        assert any(_logical_key() in key for key in keys)


class TestKeyPrefixIsolation:
    @classmethod
    def test_distinct_prefixes__shared_store__independent_buckets(cls) -> None:
        store = MemoryStore()
        client_a = _build_limited_app(store, key_prefix="app-a").test_client()
        client_b = _build_limited_app(store, key_prefix="app-b").test_client()

        assert client_a.get(_ROUTE).status_code == HTTPStatus.OK
        assert client_b.get(_ROUTE).status_code == HTTPStatus.OK
        assert client_a.get(_ROUTE).status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert client_b.get(_ROUTE).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_same_prefix__shared_store__shares_one_bucket(cls) -> None:
        store = MemoryStore()
        client_a = _build_limited_app(store, key_prefix="shared").test_client()
        client_b = _build_limited_app(store, key_prefix="shared").test_client()

        assert client_a.get(_ROUTE).status_code == HTTPStatus.OK
        assert client_b.get(_ROUTE).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_same_prefix__separate_stores_same_backend__shares_one_bucket(cls) -> None:
        store_a = MemoryStore()
        store_b = MemoryStore()
        store_b._backend = store_a._backend
        client_a = _build_limited_app(
            store_a,
            key_prefix="shared",
        ).test_client()
        client_b = _build_limited_app(
            store_b,
            key_prefix="shared",
        ).test_client()

        assert client_a.get(_ROUTE).status_code == HTTPStatus.OK
        assert client_b.get(_ROUTE).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_default_namespace__shared_store__unchanged_collision(cls) -> None:
        store = MemoryStore()
        client_a = _build_limited_app(store).test_client()
        client_b = _build_limited_app(store).test_client()

        assert client_a.get(_ROUTE).status_code == HTTPStatus.OK
        assert client_b.get(_ROUTE).status_code == HTTPStatus.TOO_MANY_REQUESTS


class TestKeyPrefixValidation:
    @classmethod
    @pytest.mark.parametrize(
        "key_prefix",
        [
            pytest.param(":myapp", id="leading-colon"),
            pytest.param("myapp:", id="trailing-colon"),
            pytest.param("", id="empty"),
            pytest.param("   ", id="blank"),
        ],
    )
    def test_key_prefix__invalid__raises_at_construction(
        cls,
        key_prefix: str,
    ) -> None:
        with pytest.raises(DataError, match="key_prefix"):
            Limiter("2/s", store=MemoryStore(), key_prefix=key_prefix)

    @classmethod
    def test_key_prefix__not_a_string__raises(cls) -> None:
        with pytest.raises(DataError, match="key_prefix"):
            Limiter("2/s", store=MemoryStore(), key_prefix=42)  # type: ignore[arg-type]

    @classmethod
    def test_key_prefix__none__keeps_default_namespace(cls) -> None:
        store = MemoryStore()
        app = _build_limited_app(store, key_prefix=None)

        assert app.test_client().get(_ROUTE).status_code == HTTPStatus.OK
        keys: list[str] = _stored_keys(store)
        assert keys
        namespace: str = f"{_DEFAULT_NAMESPACE}:{_SCHEMA_VERSION}:fixed_window:"
        assert all(key.startswith(namespace) for key in keys)
