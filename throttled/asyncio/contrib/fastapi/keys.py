"""Storage key composition utilities."""

from __future__ import annotations

from typing import NamedTuple
from urllib.parse import quote

_FIELD_SEPARATOR = "|"


class KeyParts(NamedTuple):
    """Structured parts that compose a storage key.

    :param method: HTTP method (``"GET"``, ``"POST"``...).
    :param route: The matched route template (``"/users/{id}"``). Falls
        back to the concrete URL path when the router has not populated
        it yet.
    :param principal: Result of the user-provided ``key_func``.
    """

    method: str
    route: str
    principal: str


def compose_key(parts: KeyParts) -> str:
    """Join :class:`KeyParts` into a collision-safe storage key.

    Fields are percent-encoded with ``quote(safe="")`` and joined by
    :data:`_FIELD_SEPARATOR`.

    Each field is percent-encoded with an empty ``safe`` set so every
    character outside the RFC 3986 unreserved range (``A-Z``, ``a-z``,
    ``0-9``, ``-``, ``.``, ``_``, ``~``) is escaped.
    """
    return _FIELD_SEPARATOR.join(
        (
            quote(parts.method, safe=""),
            quote(parts.route, safe=""),
            quote(parts.principal, safe=""),
        )
    )
