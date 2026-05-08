=======
FastAPI
=======

Async decorator-based rate limiter for FastAPI. Apply per-route rate limiting with
automatic ``RateLimit-*`` header injection on responses from rate-limit-checked
routes and IETF-compliant HTTP 429 responses on quota exhaustion.


Installation
============

.. code-block:: bash

   pip install 'throttled-py[fastapi]'

This installs ``fastapi`` as a dependency. You also need an ASGI server
(e.g., ``uvicorn``) to run the application.

.. note::

   This integration is **async-only**. All decorated route functions must be
   ``async def``. There is no synchronous variant. The module lives under
   ``throttled.asyncio.contrib.fastapi`` and requires an async ASGI server.


1) Quick Start
==============

Application
-----------

A minimal FastAPI app with rate limiting on a single route:

.. literalinclude:: ../../../examples/contrib/fastapi/basic_example.py
   :language: python

Three components are required:

1. **Limiter**: Decorator that checks rate limits and raises on quota exhaustion.
2. **RateLimitMiddleware**: Injects ``RateLimit-*`` headers on responses from
   routes that passed the rate-limit check.
3. **rate_limit_exceeded_handler**: Renders HTTP 429 with ``Retry-After`` header.

.. note::

   Keep the FastAPI route decorator (for example, ``@app.get(...)`` or
   ``@router.get(...)``) above ``@limiter.limit()``. Reversing them silently
   disables rate limiting; see :ref:`fastapi-decorator-order` for the failure
   mode and stacking with other decorators.

.. warning::

   **All three components are required.** Skipping
   ``app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)``
   is the most common pitfall: quota exhaustion then surfaces as ``HTTP 500
   Internal Server Error`` (not ``429``), because Starlette has no handler for
   ``RateLimitExceededError`` and falls back to the default 500 path.

.. note::

   Every decorated route **must** declare a ``Request`` parameter (any name is fine).
   The decorator finds it by type, not by name.

Run
---

If you are using throttled-py from your own project, save the snippet as
``basic_example.py`` and start the server with
`uvicorn <https://www.uvicorn.dev/>`_:

.. code-block:: bash

   pip install 'throttled-py[fastapi]' uvicorn
   uvicorn basic_example:app

If you are running the checked-in example from the repository, use the full
module path from the repo root:

.. code-block:: bash

   uvicorn examples.contrib.fastapi.basic_example:app

Test
----

The default quota is ``2/m`` (two requests per minute). Send three requests in
quick succession to observe each phase of the rate limit:

.. code-block:: bash

   $ curl -is http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-limit: 2
   ratelimit-remaining: 1
   ratelimit-reset: 30
   content-type: application/json

   {"items":["apple","banana"]}

   $ curl -is http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-limit: 2
   ratelimit-remaining: 0
   ratelimit-reset: 60
   content-type: application/json

   {"items":["apple","banana"]}

   $ curl -is http://localhost:8000/items
   HTTP/1.1 429 Too Many Requests
   ratelimit-limit: 2
   ratelimit-remaining: 0
   ratelimit-reset: 60
   retry-after: 30
   content-type: application/json

   {"detail":"Rate limit exceeded"}

.. note::

   HTTP/1.1 header names are case-insensitive. The library writes them in the
   IETF-recommended ``RateLimit-Limit`` form, but Starlette lowercases all
   response header names before handing them to the ASGI server (the ASGI spec
   requires lowercase header names on the wire). The bytes sent to clients are
   therefore ``ratelimit-limit``, ``ratelimit-remaining``, etc.

2) Custom Key Function
======================

By default, rate limiting uses the client IP address (``get_remote_address``).
You can supply a custom ``key_func`` to identify clients by API key, user ID,
or any other request attribute.

Application
-----------

.. literalinclude:: ../../../examples/contrib/fastapi/custom_key_func_example.py
   :language: python

``key_func`` accepts both sync and async callables:

.. code-block:: python

   # Sync: simple header extraction.
   def get_api_key(request: Request) -> str:
       return request.headers.get("X-API-Key", "anonymous")

   # Async: database or Redis lookup.
   async def get_user_id(request: Request) -> str:
       token = request.headers.get("Authorization", "")
       user = await verify_token(token)
       return user.id

Run
---

From your own project, save the snippet as ``custom_key_func_example.py`` and run:

.. code-block:: bash

   uvicorn custom_key_func_example:app

From the repository root:

.. code-block:: bash

   uvicorn examples.contrib.fastapi.custom_key_func_example:app

Test
----

Each API key gets its own quota. ``user-a`` and ``user-b`` are tracked separately:

.. code-block:: bash

   $ curl -is -H "X-API-Key: user-a" http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-remaining: 1
   ...

   $ curl -is -H "X-API-Key: user-a" http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-remaining: 0
   ...

   $ curl -is -H "X-API-Key: user-a" http://localhost:8000/items
   HTTP/1.1 429 Too Many Requests
   retry-after: 30
   ...
   {"detail":"Rate limit exceeded"}

   $ curl -is -H "X-API-Key: user-b" http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-remaining: 1
   ...
   {"items":["apple","banana"]}


3) Per-Route Quota Override
===========================

The ``Limiter`` constructor sets a default quota for all decorated routes.
Individual routes can override it via ``.limit(quota)``.

Application
-----------

.. literalinclude:: ../../../examples/contrib/fastapi/multi_route_example.py
   :language: python

Each ``.limit()`` call creates an independent ``Throttled`` instance. Routes share
a counter only when they share the same ``store`` object **and** the same composed
storage key (method + route template + principal).

Run
---

From your own project, save the snippet as ``multi_route_example.py`` and run:

.. code-block:: bash

   uvicorn multi_route_example:app

From the repository root:

.. code-block:: bash

   uvicorn examples.contrib.fastapi.multi_route_example:app

Test
----

``/items`` allows 10 requests/minute, ``/admin`` only 1/minute. Each route has
its own counter:

.. code-block:: bash

   $ curl -is http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-limit: 10
   ratelimit-remaining: 9
   ...

   $ curl -is http://localhost:8000/admin
   HTTP/1.1 200 OK
   ratelimit-limit: 1
   ratelimit-remaining: 0
   ...
   {"status":"ok"}

   $ curl -is http://localhost:8000/admin
   HTTP/1.1 429 Too Many Requests
   ratelimit-limit: 1
   retry-after: 60
   ...
   {"detail":"Rate limit exceeded"}

   $ curl -is http://localhost:8000/items
   HTTP/1.1 200 OK
   ratelimit-limit: 10
   ratelimit-remaining: 8
   ...


4) Response Headers
===================

Allowed responses (any non-429)
-------------------------------

Whenever the rate-limit check passes, the middleware attaches three headers
following
`draft-ietf-httpapi-ratelimit-headers <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>`_:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Header
     - Description
   * - ``RateLimit-Limit``
     - Total quota in the current window.
   * - ``RateLimit-Remaining``
     - Remaining requests in the current window.
   * - ``RateLimit-Reset``
     - Seconds until the quota resets (integer, rounded up).

.. note::

   Header injection is gated on whether the rate-limit check passed, **not** on
   the endpoint's status code. A decorated endpoint that returns ``400`` or
   ``500`` after the rate-limit check passed will still carry the
   ``RateLimit-*`` headers. This matches the IETF draft, which describes the
   rate-limit state, not the response outcome. The 429 path is rendered by the
   exception handler instead and is not affected by this middleware.

Rate-limited responses (429)
----------------------------

429 responses carry the same three ``RateLimit-*`` headers as allowed
responses, plus one additional header per
`RFC 9110 §10.2.3 <https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3>`_:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Header
     - Description
   * - ``Retry-After``
     - Seconds the client should wait before retrying (integer, rounded up).

The body matches FastAPI's ``HTTPException`` shape:

.. code-block:: json

   {"detail": "Rate limit exceeded"}


5) API Reference
================

Limiter
-------

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Parameter
     - Type
     - Description
   * - ``quota`` *(required)*
     - ``Quota | str``
     - Default quota for all decorated routes. Accepts a ``Quota`` instance or
       a DSL string such as ``"100/m"`` or ``"10/s burst 20"``.
   * - ``store``
     - ``AsyncStoreP | None``
     - Storage backend. Defaults to ``MemoryStore`` when ``None``.
   * - ``using``
     - ``str``
     - Rate-limit algorithm. Defaults to ``"token_bucket"`` to match
       :class:`~throttled.asyncio.throttled.Throttled`.
   * - ``key_func``
     - ``KeyFunc``
     - Sync or async callable ``(Request) -> str``. Defaults to
       ``get_remote_address`` (client IP).
   * - ``hooks``
     - ``Sequence[Hook] | None``
     - Optional async hooks forwarded to the internal ``Throttled`` instances.

Limiter.limit()
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Parameter
     - Type
     - Description
   * - ``quota``
     - ``Quota | str | None``
     - Per-route quota override. Falls back to the instance default when ``None``.
   * - ``key_func``
     - ``KeyFunc | None``
     - Per-route key function override. Falls back to the instance default when ``None``.

RateLimitMiddleware
-------------------

ASGI middleware (``BaseHTTPMiddleware`` subclass). No constructor parameters.
Register it on each ``FastAPI`` app that uses rate-limited routes:

.. code-block:: python

   app.add_middleware(RateLimitMiddleware)

The middleware reads the ``RateLimitContext`` that the decorator stored on
``request.state`` and applies the rendered headers to the final response.
If no context is found (e.g., undecorated routes), the response passes through
unchanged.

rate_limit_exceeded_handler
---------------------------

Async exception handler. Register it for ``RateLimitExceededError``:

.. code-block:: python

   app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)

Returns a 429 ``JSONResponse`` with ``RateLimit-*`` and ``Retry-After`` headers.

RateLimitExceededError
----------------------

Subclass of ``throttled.exceptions.LimitedError``. User code that catches
``LimitedError`` will also catch this exception:

.. code-block:: python

   from throttled.exceptions import LimitedError

   try:
       await throttle.limit()
   except LimitedError:
       # Catches both core LimitedError and RateLimitExceededError.
       ...


6) Constraints and Known Limitations
=====================================

Async-only
----------

All decorated route functions must be ``async def``. Applying ``@limiter.limit()``
to a sync function raises ``TypeError`` at decoration time.

Route metadata dependency
-------------------------

The storage key includes the matched route template from
``request.scope["route"].path_format``, which is set by FastAPI's
``APIRoute.matches()``. This is a FastAPI-specific attribute; using this
contrib with plain Starlette is not supported.

``root_path`` in the storage key
--------------------------------

The storage key is composed as ``root_path + path_format``, which prevents
collisions when the same sub-app is mounted at different paths. However,
changing a reverse-proxy prefix (``FastAPI(root_path=...)`` or ``--root-path``)
will rotate the counter namespace, effectively resetting all rate-limit counters.

Header injection requires middleware registration
--------------------------------------------------

``RateLimit-*`` headers on rate-limit-checked responses are injected by
``RateLimitMiddleware``. If the middleware is not registered, rate limiting
still works (429s are returned correctly), but allowed responses will not
include rate-limit headers.

.. _fastapi-decorator-order:

Decorator ordering
------------------

FastAPI route decorators such as ``@app.get(...)`` or ``@router.get(...)``
must stay above ``@limiter.limit()``:

.. code-block:: python

   @app.get("/items")
   @limiter.limit()
   async def items(request: Request) -> dict[str, str]:
       return {"ok": "true"}

Reversing the two decorators disables rate limiting for that route, because
FastAPI registers the endpoint callable when the route decorator runs:

.. code-block:: python

   @limiter.limit()
   @app.get("/items")  # Wrong order: limiter will not run for requests.
   async def items(request: Request) -> dict[str, str]:
       return {"ok": "true"}

In that wrong order, requests continue to reach the endpoint normally, so the
failure mode is silent: repeated requests keep returning ``200`` and no
``RateLimit-*`` headers appear.

Python applies decorators bottom-up, so the wrapper closest to the function
runs first. When stacking with other decorators, follow these rules:

- ``@app.{method}(...)`` (``@app.get``, ``@app.post``, ...) must be the
  **outermost** decorator, because it registers the final wrapped callable to
  the routing table.
- Function-internal injection decorators (``@inject`` from
  `dependency-injector <https://python-dependency-injector.ets-labs.org/>`_,
  ``@punq.inject``, etc.) belong **closest to the function**, so they see the
  original signature when binding arguments.
- Per-request wrappers like ``@limiter.limit()`` go **between** the two.

A common case is combining the rate limiter with a DI-style decorator. The
most popular one is ``@inject`` from ``dependency-injector``; when a route
uses both, stack them like this:

.. code-block:: python

   @app.get("/items")
   @limiter.limit()
   @inject
   async def list_items(
       request: Request,
       service: Service = Depends(Provide[Container.service]),
   ):
       ...

The same shape applies to other function-internal injection decorators
(``@punq.inject`` and similar): keep them closest to the function and put
``@limiter.limit()`` above.
