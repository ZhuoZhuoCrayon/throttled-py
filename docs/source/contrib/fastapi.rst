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


.. _fastapi-examples:

Examples
========

The examples below use the same FastAPI integration pieces with different
quota choices.

.. tab-set::

    .. tab-item:: Shared route quota

        .. literalinclude:: ../../../examples/contrib/fastapi/basic_example.py
           :language: python

    .. tab-item:: API key quota

        .. literalinclude:: ../../../examples/contrib/fastapi/custom_key_func_example.py
           :language: python

    .. tab-item:: Client IP quota

        .. literalinclude:: ../../../examples/contrib/fastapi/remote_address_example.py
           :language: python

    .. tab-item:: Per-route quotas

        .. literalinclude:: ../../../examples/contrib/fastapi/multi_route_example.py
           :language: python

The setup has three parts:

1. **Limiter**: Checks decorated routes against a quota.
2. **RateLimitMiddleware**: Adds ``RateLimit-*`` headers to checked responses.
3. **rate_limit_exceeded_handler**: Renders quota exhaustion as HTTP 429 with
   ``Retry-After``.

.. note::

   Keep the FastAPI route decorator (for example, ``@app.get(...)`` or
   ``@router.get(...)``) above ``@limiter.limit()``. Reversing them silently
   disables rate limiting; see :ref:`fastapi-decorator-order` for the failure
   mode and stacking with other decorators.

The following sections explain when to use each example. Return to
:ref:`fastapi-examples` to see the runnable app code.


1) Basic Usage
==============

By default, calls to the same method and route share one quota bucket. See the
``Shared route quota`` example in :ref:`fastapi-examples`.

Test
----

The default quota is ``2/m`` (two requests per minute). Run the matching
example with an ASGI server, then send three requests in quick succession to
observe each phase of the rate limit:

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

2) Choosing a Key Function
==========================

Use an explicit ``key_func`` when the quota should be tied to a caller or
application identity. For the default shared-route behavior, see the
``Shared route quota`` tab in :ref:`fastapi-examples`.

For direct client-IP limiting, pass ``get_remote_address`` explicitly. See the
``Client IP quota`` tab in :ref:`fastapi-examples` for a runnable app.
``get_remote_address`` reads ``request.client.host`` from the ASGI scope. In
reverse-proxy or load-balancer deployments, make sure that value is the client
address you intend to trust before using it as a rate-limit principal.

For authenticated APIs, prefer an application principal such as user ID, tenant
ID, or API key. See the ``API key quota`` tab in :ref:`fastapi-examples`
for a runnable app.

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

Each ``.limit()`` call creates an independent ``Throttled`` instance. Routes share
a counter only when they share the same ``store`` object **and** the same composed
storage key (method + route template + principal).

See the ``Per-route quotas`` tab in :ref:`fastapi-examples` for a
runnable app with a stricter ``/admin`` quota.

Test
----

Run the per-route example with an ASGI server. ``/items`` allows 10
requests/minute, ``/admin`` only 1/minute. Each route has its own counter:

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


5) Constraints and Known Limitations
=====================================

Async-only
----------

All decorated route functions must be ``async def``. Applying ``@limiter.limit()``
to a sync function raises ``TypeError`` at decoration time.

Request parameter
-----------------

Every decorated route must declare a ``Request`` parameter. The decorator finds
it by type, not by name, and raises ``TypeError`` if none is available.

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
