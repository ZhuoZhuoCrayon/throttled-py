"""Unit tests for ``get_remote_address``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from starlette.requests import Request
from throttled.asyncio.contrib.fastapi import get_remote_address

if TYPE_CHECKING:
    import pytest

_UNKNOWN_CLIENT = "unknown"


def _mock_request(host: str | None = "10.0.0.1") -> MagicMock:
    """Build a minimal mocked Starlette ``Request`` for unit testing."""
    request: MagicMock = MagicMock(spec=Request)
    if host is None:
        request.client = None
    else:
        request.client = MagicMock()
        request.client.host = host
    return request


class TestGetRemoteAddress:
    @classmethod
    def test_get_remote_address__client_present__returns_host(cls) -> None:
        """Return the ASGI client host verbatim when available."""
        assert get_remote_address(_mock_request("192.168.1.1")) == "192.168.1.1"

    @classmethod
    def test_get_remote_address__ipv6_host__preserved_verbatim(cls) -> None:
        """IPv6 addresses must not be mangled by the helper."""
        assert get_remote_address(_mock_request("2001:db8::1")) == "2001:db8::1"

    @classmethod
    def test_get_remote_address__client_none__warns_and_returns_unknown(
        cls, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Emit a warning and fall back to :data:`_UNKNOWN_CLIENT` so
        operators can notice the key-collapse risk."""
        with caplog.at_level(
            logging.WARNING,
            logger="throttled.asyncio.contrib.fastapi.key_funcs",
        ):
            result: str = get_remote_address(_mock_request(None))
        assert result == _UNKNOWN_CLIENT
        assert any(
            "request.client is unavailable" in record.message
            for record in caplog.records
        )

    @classmethod
    def test_get_remote_address__empty_host__returns_unknown(cls) -> None:
        """An empty string host is treated as missing to avoid silent
        key collapse on one-empty-host."""
        assert get_remote_address(_mock_request("")) == _UNKNOWN_CLIENT
