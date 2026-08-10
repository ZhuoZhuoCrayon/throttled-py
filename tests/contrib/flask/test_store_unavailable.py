"""StoreUnavailableError → HTTP 503 mapping (mirrors FastAPI #168)."""

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from flask import Blueprint, Flask, jsonify
from throttled.contrib.flask import Limiter
from throttled.contrib.flask import limiter as limiter_module
from throttled.exceptions import BaseThrottledError, StoreUnavailableError
from werkzeug.exceptions import ServiceUnavailable

from ...store.unavailable import OperationUnavailableStore

if TYPE_CHECKING:
    from werkzeug.test import TestResponse

_LIMITER_LOGGER_NAME = "throttled.contrib.flask.limiter"


class _CustomStoreUnavailableError(StoreUnavailableError):
    """A downstream store's finer-grained outage exception."""


def build_unavailable_app() -> Flask:
    """Build a Flask app whose only route is rate-limited by a store
    that always raises ``StoreUnavailableError``.
    """
    limiter = Limiter("5/s", store=OperationUnavailableStore())
    app = Flask(__name__)
    limiter.init_app(app)

    @app.get("/")
    @limiter.limit()
    def endpoint() -> dict[str, bool]:
        return {"ok": True}

    return app


def call_route(app: Flask, caplog: pytest.LogCaptureFixture) -> "TestResponse":
    """Call the app's rate-limited route with the limiter logger
    captured at ERROR level."""
    with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
        return app.test_client().get("/")


def _store_unavailable_records(
    caplog: pytest.LogCaptureFixture,
) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == _LIMITER_LOGGER_NAME]


def assert_store_unavailable_logged_once(caplog: pytest.LogCaptureFixture) -> None:
    records = _store_unavailable_records(caplog)
    assert len(records) == 1
    record = records[0]
    assert record.getMessage() == limiter_module._STORE_UNAVAILABLE_LOG_MSG
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.exc_info[0] is StoreUnavailableError


def assert_no_store_unavailable_log(caplog: pytest.LogCaptureFixture) -> None:
    assert _store_unavailable_records(caplog) == []


class TestStoreUnavailable:
    @classmethod
    def test_default__returns_503_without_rate_limit_headers(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No handler registered: default werkzeug 503 body, one ERROR
        log record, and no ``RateLimit-*`` / ``Retry-After`` headers."""
        app = build_unavailable_app()
        response = call_route(app, caplog)

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert "Rate limit store unavailable" in response.get_data(as_text=True)
        assert "RateLimit-Limit" not in response.headers
        assert "RateLimit-Remaining" not in response.headers
        assert "RateLimit-Reset" not in response.headers
        assert "Retry-After" not in response.headers

        assert_store_unavailable_logged_once(caplog)

    @classmethod
    @pytest.mark.parametrize(
        "handler_type",
        [
            pytest.param(StoreUnavailableError, id="exact-handler"),
            pytest.param(BaseThrottledError, id="base-class-handler"),
        ],
    )
    def test_handler__preempts_default_503(
        cls,
        handler_type: type[Exception],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A handler whose class is in the raised exception's MRO
        (exact ``StoreUnavailableError`` or a base such as
        ``BaseThrottledError``) preempts the default 503 and suppresses
        the library's store-unavailable log.
        """
        app = build_unavailable_app()

        @app.errorhandler(handler_type)
        def on_store_down(exc: Exception):
            return jsonify(detail="store down"), HTTPStatus.BAD_GATEWAY

        response = call_route(app, caplog)

        assert response.status_code == HTTPStatus.BAD_GATEWAY
        assert response.get_json() == {"detail": "store down"}
        assert_no_store_unavailable_log(caplog)

    @classmethod
    def test_handler_on_unrelated_blueprint__does_not_preempt_503(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A ``StoreUnavailableError`` handler on blueprint A must not
        affect an outage on blueprint B's route: Flask would never
        dispatch A's handler for B's request, so re-raising would turn
        the default 503 into an unhandled 500 (Codex review regression).
        """
        limiter = Limiter("5/s", store=OperationUnavailableStore())
        app = Flask(__name__)
        limiter.init_app(app)

        handling = Blueprint("handling", __name__)
        handling.errorhandler(StoreUnavailableError)(
            lambda exc: (jsonify(detail="handled by A"), HTTPStatus.BAD_GATEWAY)
        )
        serving = Blueprint("serving", __name__)

        @serving.get("/limited")
        @limiter.limit()
        def limited() -> dict[str, bool]:
            return {"ok": True}

        app.register_blueprint(handling, url_prefix="/a")
        app.register_blueprint(serving, url_prefix="/b")

        with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
            response = app.test_client().get("/b/limited")

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert "Rate limit store unavailable" in response.get_data(as_text=True)
        assert_store_unavailable_logged_once(caplog)

    @classmethod
    def test_handler_on_active_blueprint__preempts_503(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A handler on the blueprint that serves the failing route is
        user intent: the limiter re-raises and Flask dispatches it."""
        limiter = Limiter("5/s", store=OperationUnavailableStore())
        app = Flask(__name__)
        limiter.init_app(app)

        blueprint = Blueprint("api", __name__)
        blueprint.errorhandler(StoreUnavailableError)(
            lambda exc: (jsonify(detail="store down"), HTTPStatus.BAD_GATEWAY)
        )

        @blueprint.get("/limited")
        @limiter.limit()
        def limited() -> dict[str, bool]:
            return {"ok": True}

        app.register_blueprint(blueprint, url_prefix="/api")

        with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
            response = app.test_client().get("/api/limited")

        assert response.status_code == HTTPStatus.BAD_GATEWAY
        assert response.get_json() == {"detail": "store down"}
        assert_no_store_unavailable_log(caplog)

    @classmethod
    def test_generic_exception_handler__does_not_preempt_default_503(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A catch-all ``Exception`` handler is not an intentional
        opt-in for store outages: the limiter still converts to 503.
        Flask then dispatches the resulting ``ServiceUnavailable``
        through that handler via MRO — it must see the converted 503,
        never the raw ``StoreUnavailableError``.
        """
        app = build_unavailable_app()
        received: list[Exception] = []

        @app.errorhandler(Exception)
        def on_any(exc: Exception):
            received.append(exc)
            if isinstance(exc, ServiceUnavailable):
                return exc
            return jsonify(detail="unexpected"), HTTPStatus.INTERNAL_SERVER_ERROR

        response = call_route(app, caplog)

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert len(received) == 1
        assert isinstance(received[0], ServiceUnavailable)
        assert_store_unavailable_logged_once(caplog)


class TestHasErrorHandler:
    @classmethod
    @pytest.mark.parametrize(
        ("registered", "raised", "expected"),
        [
            pytest.param(
                StoreUnavailableError, StoreUnavailableError, True, id="exact-match"
            ),
            pytest.param(
                BaseThrottledError, StoreUnavailableError, True, id="base-via-mro"
            ),
            pytest.param(
                _CustomStoreUnavailableError,
                _CustomStoreUnavailableError,
                True,
                id="subclass-via-mro",
            ),
            pytest.param(
                Exception, StoreUnavailableError, False, id="exception-excluded"
            ),
            pytest.param(None, StoreUnavailableError, False, id="no-handler"),
        ],
    )
    def test_has_error_handler__matches_via_mro_excluding_exception(
        cls,
        registered: type[Exception] | None,
        raised: type[Exception],
        expected: bool,
    ) -> None:
        """``_has_error_handler`` walks app-level registrations so exact,
        base-class, and subclass handlers all match, while a catch-all
        ``Exception`` handler and the no-handler case do not. The lookup
        reads ``request.blueprints``, so it runs in a request context.
        """
        app = Flask(__name__)
        if registered is not None:
            app.errorhandler(registered)(lambda exc: ("", HTTPStatus.BAD_GATEWAY))

        with app.test_request_context("/"):
            assert limiter_module._has_error_handler(app, raised) is expected

    @classmethod
    def test_has_error_handler__active_blueprint_counts(cls) -> None:
        """A handler on the blueprint serving the request must count:
        Flask would dispatch it, so the limiter must re-raise."""
        app = Flask(__name__)
        blueprint = Blueprint("api", __name__)
        blueprint.errorhandler(StoreUnavailableError)(
            lambda exc: ("", HTTPStatus.BAD_GATEWAY)
        )

        @blueprint.get("/ping")
        def ping() -> str:
            return "pong"

        app.register_blueprint(blueprint, url_prefix="/api")

        with app.test_request_context("/api/ping"):
            assert limiter_module._has_error_handler(app, StoreUnavailableError) is True

    @classmethod
    def test_has_error_handler__unrelated_blueprint_does_not_count(cls) -> None:
        """A handler on a blueprint outside the active request's chain
        must NOT count: Flask would never dispatch it, so re-raising
        would surface an unhandled 500 instead of the default 503."""
        app = Flask(__name__)
        handling = Blueprint("handling", __name__)
        handling.errorhandler(StoreUnavailableError)(
            lambda exc: ("", HTTPStatus.BAD_GATEWAY)
        )
        serving = Blueprint("serving", __name__)

        @serving.get("/ping")
        def ping() -> str:
            return "pong"

        app.register_blueprint(handling, url_prefix="/handling")
        app.register_blueprint(serving, url_prefix="/serving")

        with app.test_request_context("/serving/ping"):
            assert limiter_module._has_error_handler(app, StoreUnavailableError) is False
