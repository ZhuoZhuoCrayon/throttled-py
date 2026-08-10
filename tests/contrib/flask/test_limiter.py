"""End-to-end tests driving a real Flask app through the test client."""

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from flask import Blueprint, Flask, request
from throttled.contrib.flask import Limiter, get_remote_address
from throttled.store import MemoryStore

from .conftest import ALGORITHMS

if TYPE_CHECKING:
    from collections.abc import Callable


def _register_items_endpoint(app: Flask, limiter: Limiter) -> None:
    """Register a rate-limited ``GET /items`` view on ``app`` for tests."""

    @app.get("/items")
    @limiter.limit()
    def list_items() -> dict[str, str]:
        return {"ok": "yes"}


class TestLimiterInit:
    @classmethod
    def test_init__quota_is_none__raises_type_error(cls) -> None:
        """A missing quota must fail loudly."""
        with pytest.raises(TypeError, match=r"requires an explicit quota"):
            Limiter(None)  # type: ignore[arg-type]

    @classmethod
    def test_init__app_kwarg__wires_eagerly(cls) -> None:
        """``Limiter(quota, app=app)`` must behave like ``init_app``
        (Flask extension eager-init convention)."""
        app = Flask(__name__)
        limiter = Limiter("2/s", app=app, store=MemoryStore())

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        response = app.test_client().get("/x")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["RateLimit-Limit"] == "2"

    @classmethod
    def test_init_app__called_twice__headers_not_duplicated(cls) -> None:
        """Repeated ``init_app`` with the same limiter must be a no-op:
        the after_request hook may only run once per response."""
        app = Flask(__name__)
        limiter = Limiter("2/s", store=MemoryStore())
        limiter.init_app(app)
        limiter.init_app(app)

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        response = app.test_client().get("/x")
        assert response.headers.getlist("RateLimit-Limit") == ["2"]

    @classmethod
    def test_init_app__two_limiters_one_app__single_header_hook(cls) -> None:
        """Multiple limiters on one app share a single after_request
        hook; headers must not be emitted twice."""
        app = Flask(__name__)
        limiter_a = Limiter("2/s", store=MemoryStore())
        limiter_b = Limiter("5/s", store=MemoryStore())
        limiter_a.init_app(app)
        limiter_b.init_app(app)

        @app.get("/a")
        @limiter_a.limit()
        def route_a() -> dict[str, bool]:
            return {"ok": True}

        response = app.test_client().get("/a")
        assert response.headers.getlist("RateLimit-Limit") == ["2"]


class TestDefaultKeyFunc:
    @classmethod
    def test_limit__default_key_func__shares_bucket_across_clients(cls) -> None:
        """The omitted key_func is a shared route bucket, not client IP."""
        limiter = Limiter("1/m", store=MemoryStore())
        app = Flask(__name__)
        limiter.init_app(app)

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        assert (
            client.get(
                "/x", environ_overrides={"REMOTE_ADDR": "198.51.100.1"}
            ).status_code
            == HTTPStatus.OK
        )
        assert (
            client.get(
                "/x", environ_overrides={"REMOTE_ADDR": "198.51.100.2"}
            ).status_code
            == HTTPStatus.TOO_MANY_REQUESTS
        )

    @classmethod
    def test_limit__remote_address_key_func__separates_clients(cls) -> None:
        """IP-based limiting remains available as an explicit opt-in."""
        limiter = Limiter("1/m", store=MemoryStore(), key_func=get_remote_address)
        app = Flask(__name__)
        limiter.init_app(app)

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        addr_a = {"REMOTE_ADDR": "198.51.100.1"}
        addr_b = {"REMOTE_ADDR": "198.51.100.2"}
        assert client.get("/x", environ_overrides=addr_a).status_code == HTTPStatus.OK
        assert client.get("/x", environ_overrides=addr_b).status_code == HTTPStatus.OK
        assert (
            client.get("/x", environ_overrides=addr_a).status_code
            == HTTPStatus.TOO_MANY_REQUESTS
        )


class TestLimiterLimit:
    @classmethod
    def test_limit__below_quota__allows_requests(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Requests under the quota pass through unchanged."""
        app, limiter = build_app(quota="2/s")
        _register_items_endpoint(app, limiter)
        client = app.test_client()

        assert client.get("/items").status_code == HTTPStatus.OK
        assert client.get("/items").status_code == HTTPStatus.OK

    @classmethod
    def test_limit__quota_exhausted__returns_429(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Second request exceeds a ``1/m`` quota and must 429 without
        any errorhandler registration (werkzeug renders the exception)."""
        app, limiter = build_app(quota="1/m")
        _register_items_endpoint(app, limiter)
        client = app.test_client()

        assert client.get("/items").status_code == HTTPStatus.OK
        assert client.get("/items").status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_limit__429_response__carries_ietf_headers_and_description(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """429 carries draft-ietf-httpapi-ratelimit headers and the
        exception description in the default werkzeug body."""
        app, limiter = build_app(quota="1/m")
        _register_items_endpoint(app, limiter)
        client = app.test_client()

        client.get("/items")
        response = client.get("/items")
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert response.headers["RateLimit-Limit"] == "1"
        assert response.headers["RateLimit-Remaining"] == "0"
        assert "RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers
        assert "Rate limit exceeded" in response.get_data(as_text=True)

    @classmethod
    def test_limit__path_parameters__share_route_template_key(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """``/users/<int:user_id>`` must share one rate-limit key across
        concrete IDs."""
        app, limiter = build_app(quota="1/m")

        @app.get("/users/<int:user_id>")
        @limiter.limit()
        def get_user(user_id: int) -> dict[str, int]:
            return {"id": user_id}

        client = app.test_client()
        assert client.get("/users/1").status_code == HTTPStatus.OK
        assert client.get("/users/2").status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_limit__per_route_quota__overrides_default(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Per-route quota tighter than the instance default wins."""
        app, limiter = build_app(quota="1000/s")

        @app.get("/tight")
        @limiter.limit("1/m")
        def tight() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        assert client.get("/tight").status_code == HTTPStatus.OK
        assert client.get("/tight").status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_limit__per_route_key_func__overrides_default(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Per-route key_func swaps the principal extractor for that
        route only."""
        app, limiter = build_app(quota="1/m", key_func=lambda: "shared")

        @app.get("/per-user")
        @limiter.limit(key_func=lambda: request.headers["x-user"])
        def per_user() -> dict[str, bool]:
            return {"ok": True}

        @app.get("/shared")
        @limiter.limit()
        def shared() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        assert (
            client.get("/per-user", headers={"x-user": "alice"}).status_code
            == HTTPStatus.OK
        )
        assert (
            client.get("/per-user", headers={"x-user": "bob"}).status_code
            == HTTPStatus.OK
        )
        assert (
            client.get("/per-user", headers={"x-user": "alice"}).status_code
            == HTTPStatus.TOO_MANY_REQUESTS
        )
        assert client.get("/shared").status_code == HTTPStatus.OK
        assert client.get("/shared").status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    def test_limit__blueprint_mounts__do_not_share_key(cls) -> None:
        """Blueprints exposing the same child path under different
        url_prefixes must keep independent rate-limit keys
        (``request.url_rule.rule`` includes the prefix)."""
        limiter = Limiter("1/m", store=MemoryStore())
        app = Flask(__name__)
        limiter.init_app(app)

        def make_blueprint(name: str) -> Blueprint:
            blueprint = Blueprint(name, __name__)

            @blueprint.get("/users/<int:user_id>")
            @limiter.limit()
            def get_user(user_id: int) -> dict[str, int]:
                return {"id": user_id}

            return blueprint

        app.register_blueprint(make_blueprint("api"), url_prefix="/api")
        app.register_blueprint(make_blueprint("admin"), url_prefix="/admin")
        client = app.test_client()

        assert client.get("/api/users/1").status_code == HTTPStatus.OK
        assert client.get("/admin/users/1").status_code == HTTPStatus.OK
        assert client.get("/api/users/2").status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert client.get("/admin/users/2").status_code == HTTPStatus.TOO_MANY_REQUESTS


class TestSuccessHeaders:
    @classmethod
    def test_limit__success__dict_return__headers_present(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Dict return (no Response object) still gets ``RateLimit-*``
        headers via the after_request hook."""
        app, limiter = build_app(quota="10/s")

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        response = app.test_client().get("/x")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["RateLimit-Limit"] == "10"
        assert response.headers["RateLimit-Remaining"] == "9"
        assert "RateLimit-Reset" in response.headers
        assert "Retry-After" not in response.headers

    @classmethod
    def test_limit__success__remaining_decrements(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """RateLimit-Remaining decrements with each request."""
        app, limiter = build_app(quota="5/m")

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        first = client.get("/x")
        second = client.get("/x")
        assert first.headers["RateLimit-Remaining"] == "4"
        assert second.headers["RateLimit-Remaining"] == "3"

    @classmethod
    def test_limit__undecorated_route__no_rate_limit_headers(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Routes without ``@limiter.limit()`` must stay untouched."""
        app, _ = build_app()

        @app.get("/free")
        def free() -> dict[str, bool]:
            return {"ok": True}

        response = app.test_client().get("/free")
        assert response.status_code == HTTPStatus.OK
        assert "RateLimit-Limit" not in response.headers


class TestAsyncViews:
    """Flask-native ``async def`` view coverage.

    This is NOT async rate-limiting support: the check inside
    ``@limiter.limit()`` stays fully synchronous and
    ``throttled.asyncio`` remains the only async API. Flask itself
    runs ``async def`` views synchronously on WSGI (``flask[async]``),
    so the wrapper must delegate through ``current_app.ensure_sync``
    — as flask-limiter does — instead of silently leaking the
    coroutine out of the sync wrapper.
    """

    @classmethod
    def test_limit__async_view__enforced_and_awaited(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """An ``async def`` view under ``@limiter.limit()`` must behave
        exactly like a sync one: awaited on success, 429 on exhaustion.
        """
        app, limiter = build_app(quota="1/m")

        @app.get("/async")
        @limiter.limit()
        async def async_view() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        first = client.get("/async")
        assert first.status_code == HTTPStatus.OK
        assert first.get_json() == {"ok": True}
        assert first.headers["RateLimit-Limit"] == "1"
        assert client.get("/async").status_code == HTTPStatus.TOO_MANY_REQUESTS


class TestRequestContextLifetime:
    @classmethod
    def test_limit__held_open_app_context__no_header_leak_across_requests(
        cls,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """``flask.g`` is bound to the app context, not the request.
        When a caller keeps one app context open across several
        requests (common in tests), the after_request hook must
        consume the stored context so a later un-limited request
        cannot inherit the previous request's ``RateLimit-*`` headers.
        """
        app, limiter = build_app(quota="10/s")

        @app.get("/limited")
        @limiter.limit()
        def limited() -> dict[str, bool]:
            return {"ok": True}

        @app.get("/free")
        def free() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        with app.app_context():
            first = client.get("/limited")
            second = client.get("/free")

        assert first.headers["RateLimit-Limit"] == "10"
        assert "RateLimit-Limit" not in second.headers


class TestStackedLimiters:
    @classmethod
    def test_limit__stacked_limiters__both_quotas_enforced(cls) -> None:
        """Two Limiter instances stacked on one view both enforce their
        quotas. Success headers reflect the innermost limiter, while
        429 responses preserve the rejecting limiter's headers.
        """
        app = Flask(__name__)
        outer = Limiter("3/m", app=app, store=MemoryStore())
        inner = Limiter(
            "1/m",
            app=app,
            store=MemoryStore(),
            key_func=lambda: request.headers["x-user"],
        )

        @app.get("/stacked")
        @outer.limit()
        @inner.limit()
        def stacked() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()

        # Success headers come from the innermost (per-user) limiter.
        first = client.get("/stacked", headers={"x-user": "a"})
        assert first.status_code == HTTPStatus.OK
        assert first.headers["RateLimit-Limit"] == "1"

        # The inner per-user limiter rejects without its exception
        # headers being overwritten by the outer context on ``g``.
        second = client.get("/stacked", headers={"x-user": "a"})
        assert second.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert second.headers["RateLimit-Limit"] == "1"
        assert second.headers["RateLimit-Remaining"] == "0"
        assert "Retry-After" in second.headers

        # Fresh user passes both limiters (outer 3/3 used).
        third = client.get("/stacked", headers={"x-user": "b"})
        assert third.status_code == HTTPStatus.OK

        # The outer shared limiter rejects before the inner one runs.
        fourth = client.get("/stacked", headers={"x-user": "c"})
        assert fourth.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert fourth.headers["RateLimit-Limit"] == "3"
        assert fourth.headers["RateLimit-Remaining"] == "0"


class TestLimiterAlgorithm:
    @classmethod
    @pytest.mark.parametrize("algorithm", ALGORITHMS)
    def test_limit__each_algorithm__returns_429_after_exhaustion(
        cls,
        algorithm: str,
        build_app: "Callable[..., tuple[Flask, Limiter]]",
    ) -> None:
        """Every supported algorithm must return 429 when exhausted."""
        app, limiter = build_app(quota="1/m", using=algorithm)

        @app.get("/x")
        @limiter.limit()
        def x() -> dict[str, bool]:
            return {"ok": True}

        client = app.test_client()
        assert client.get("/x").status_code == HTTPStatus.OK
        client.get("/x")
        assert client.get("/x").status_code == HTTPStatus.TOO_MANY_REQUESTS
