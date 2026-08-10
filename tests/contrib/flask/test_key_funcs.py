"""Tests for the zero-arg key extraction helpers."""

import logging

import pytest
from flask import Flask
from throttled.contrib.flask import get_remote_address
from throttled.contrib.flask import key_funcs as key_funcs_module


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


class TestGetRemoteAddress:
    @classmethod
    def test_get_remote_address__returns_remote_addr(cls, app: Flask) -> None:
        """Reads ``flask.request.remote_addr`` from the active request
        context — no request argument needed (Flask convention)."""
        with app.test_request_context(
            "/", environ_overrides={"REMOTE_ADDR": "203.0.113.7"}
        ):
            assert get_remote_address() == "203.0.113.7"

    @classmethod
    def test_get_remote_address__missing_addr__falls_back_with_warning(
        cls,
        app: Flask,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No REMOTE_ADDR in the WSGI environ: fall back to the sentinel
        and warn once so operators can spot misconfigured proxies."""
        with (
            caplog.at_level(logging.WARNING, logger=key_funcs_module.__name__),
            app.test_request_context("/", environ_overrides={"REMOTE_ADDR": ""}),
        ):
            assert get_remote_address() == key_funcs_module._UNKNOWN_CLIENT

        records = [r for r in caplog.records if r.name == key_funcs_module.__name__]
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING
