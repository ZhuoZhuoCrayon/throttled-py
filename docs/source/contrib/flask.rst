=====
Flask
=====

Decorator-based rate limiting for Flask. Apply per-view quotas with automatic
``RateLimit-*`` headers on checked responses and HTTP 429 responses on quota
exhaustion.


Installation
============

.. code-block:: bash

   pip install 'throttled-py[flask]'

This installs Flask as an optional dependency.


.. _flask-examples:

Examples
========

The examples below are runnable Flask applications covering common quota,
initialization, storage namespace, and error-handling choices.

.. tab-set::
    :sync-group: flask-example

    .. tab-item:: Basic usage
        :sync: basic
        :selected:

        .. literalinclude:: ../../../examples/contrib/flask/basic_example.py
           :language: python

    .. tab-item:: Application factory
        :sync: application-factory

        .. literalinclude:: ../../../examples/contrib/flask/multi_route_example.py
           :language: python

    .. tab-item:: API key quota
        :sync: api-key

        .. literalinclude:: ../../../examples/contrib/flask/custom_key_func_example.py
           :language: python

    .. tab-item:: Client IP quota
        :sync: client-ip

        .. literalinclude:: ../../../examples/contrib/flask/remote_address_example.py
           :language: python

    .. tab-item:: Key prefix
        :sync: key-prefix

        .. literalinclude:: ../../../examples/contrib/flask/key_prefix_example.py
           :language: python

    .. tab-item:: Error handling
        :sync: error-handling

        .. literalinclude:: ../../../examples/contrib/flask/error_handling_example.py
           :language: python

The setup has three parts:

1. **Limiter**: Checks decorated views against a quota.
2. **Application initialization**: Passing ``app`` or calling ``init_app``
   registers the response-header hook.
3. **RateLimitExceededError**: Lets Werkzeug render quota exhaustion as HTTP
   429 without an application error handler.

.. note::

   Keep the Flask route decorator (for example, ``@app.get(...)`` or
   ``@blueprint.get(...)``) above ``@limiter.limit()``. Reversing them silently
   disables rate limiting; see :ref:`flask-decorator-order` for the failure
   mode.

The following sections explain when to use each example. Return to
:ref:`flask-examples` to see the runnable app code.

Run an example with the Flask development server:

.. code-block:: bash

   flask --app examples.contrib.flask.basic_example run


1) Basic Usage
==============

Pass an application to ``Limiter`` for eager initialization. By default,
requests with the same HTTP method and route share one quota bucket. See the
`Basic usage example <?flask-example=basic#flask-examples>`_.

Example
-------

Send three requests within one minute to observe the allowed and rejected
responses:

.. code-block:: bash

   $ curl -is http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Limit: 2
   RateLimit-Remaining: 1
   ...

   $ curl -is http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Limit: 2
   RateLimit-Remaining: 0
   ...

   $ curl -is http://localhost:5000/items
   HTTP/1.1 429 TOO MANY REQUESTS
   RateLimit-Limit: 2
   RateLimit-Remaining: 0
   Retry-After: 30
   ...


2) Application Factories
========================

Create the limiter without an application and call ``init_app`` inside each
application factory. This follows the standard Flask extension pattern.

Repeated calls to ``init_app`` with the same limiter and application are
idempotent. Multiple limiter instances on one application share a single
``after_request`` header hook.

See the
`Application factory example
<?flask-example=application-factory#flask-examples>`_
for a runnable application with a per-route quota override.

Example
-------

Run the application-factory example with the Flask development server:

.. code-block:: bash

   $ flask --app examples.contrib.flask.multi_route_example run


3) Choosing a Key Function
==========================

Provide ``key_func`` when a quota should be tied to a caller identity. Flask
key functions take no arguments and read from the active request context.

API key quota
-------------

Use an application principal such as a user ID, tenant ID, or API key when the
application already authenticates its callers:

.. code-block:: python

   from flask import request

   def get_api_key() -> str:
       return request.headers.get("X-API-Key", "anonymous")

   limiter = Limiter("2/m", app=app, key_func=get_api_key)

Each API key then receives an independent bucket for the same method and route.
Without ``key_func``, all callers share that route's bucket.

Example
~~~~~~~

Run the
`API key quota example <?flask-example=api-key#flask-examples>`_
and send requests for two principals. Exhausting ``user-a`` does not consume
``user-b``'s bucket:

.. code-block:: bash

   $ flask --app examples.contrib.flask.custom_key_func_example run

   $ curl -is -H "X-API-Key: user-a" http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Remaining: 1
   ...

   $ curl -is -H "X-API-Key: user-a" http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Remaining: 0
   ...

   $ curl -is -H "X-API-Key: user-a" http://localhost:5000/items
   HTTP/1.1 429 TOO MANY REQUESTS
   ...

   $ curl -is -H "X-API-Key: user-b" http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Remaining: 1
   ...

Client IP quota
---------------

For direct client-address limiting, pass ``get_remote_address`` explicitly:

.. code-block:: python

   from throttled.contrib.flask import get_remote_address

   limiter = Limiter("100/m", app=app, key_func=get_remote_address)

``get_remote_address`` reads ``request.remote_addr``. When the application is
behind a reverse proxy, configure trusted proxy handling before treating that
value as a client identity.

Example
~~~~~~~

Run the
`Client IP quota example <?flask-example=client-ip#flask-examples>`_
with the Flask development server:

.. code-block:: bash

   $ flask --app examples.contrib.flask.remote_address_example run

To observe separate buckets, send requests from different network source
addresses. Forwarded headers alone do not change the direct client address
used by ``get_remote_address``.


4) Per-Route Quota Override
===========================

The ``Limiter`` constructor sets a default quota for every decorated view.
Individual views can override it via ``.limit(quota)``.

Each ``.limit()`` call builds an independent ``Throttled`` instance. Two views
share a counter only when they share the same ``store`` object **and** the same
composed storage key (method + route rule + principal).

``.limit()`` accepts ``key_func`` alongside ``quota``, so a view can override
the quota, the principal, or both. Anything left out falls back to the
instance default.

See the
`Application factory example
<?flask-example=application-factory#flask-examples>`_
for a runnable app with a stricter ``/admin`` quota.

Example
-------

With the application-factory example running, call both routes. ``/items``
allows 10 requests/minute, while ``/admin`` allows only 1/minute. Each view has
its own counter:

.. code-block:: bash

   $ curl -is http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Limit: 10
   RateLimit-Remaining: 9
   ...

   $ curl -is http://localhost:5000/admin
   HTTP/1.1 200 OK
   RateLimit-Limit: 1
   RateLimit-Remaining: 0
   ...

   $ curl -is http://localhost:5000/admin
   HTTP/1.1 429 TOO MANY REQUESTS
   RateLimit-Limit: 1
   Retry-After: 60
   ...

   $ curl -is http://localhost:5000/items
   HTTP/1.1 200 OK
   RateLimit-Limit: 10
   RateLimit-Remaining: 8
   ...


5) Key Prefix
=============

By default, rate-limit state lives under ``throttled:v1:<algorithm>:``. Pass
``key_prefix`` to replace the ``throttled`` namespace with your own. See the
`Key prefix example <?flask-example=key-prefix#flask-examples>`_ for a runnable
application configured with the ``storefront`` namespace.

Use a distinct prefix for each application that shares a backing store. Their
counters remain separate even when requests otherwise resolve to the same key.

``Limiter`` validates ``key_prefix`` during construction, so invalid
configuration fails at application setup. See
:ref:`Key Prefix <store-backends-key-prefix>` for the key format and validation
rules.

6) Error Handling
=================

The
`Error handling example <?flask-example=error-handling#flask-examples>`_
is a runnable application covering both cases below.

Quota exhaustion
----------------

No error handler registration is required. ``RateLimitExceededError`` is a
Werkzeug HTTP exception, so Flask renders a default 429 response with
``RateLimit-*`` and ``Retry-After`` headers.

Register an error handler to customize the body. If the handler constructs a
new response, carry forward the exception headers so the response retains the
rejecting limiter's metadata:

.. literalinclude:: ../../../examples/contrib/flask/error_handling_example.py
   :language: python
   :start-after: # Customize quota exhaustion responses.
   :end-at: return jsonify(detail=exc.description), exc.code, headers

The exception also exposes ``rate_limit_context`` and inherits from the core
``LimitedError`` class for applications with shared error-handling code.

Store outages
-------------

When the store backend raises ``StoreUnavailableError``, the limiter fails
closed: it logs the failure at ``ERROR`` and returns HTTP 503. The response
does not include ``RateLimit-*`` or ``Retry-After`` headers because no quota
was measured.

Register an error handler for ``StoreUnavailableError`` to customize the
response:

.. literalinclude:: ../../../examples/contrib/flask/error_handling_example.py
   :language: python
   :start-after: # Customize store outage responses.
   :end-at: return {"detail": "Rate limit service temporarily unavailable"}, 503

A handler registered for ``StoreUnavailableError`` or one of its base classes
takes over when it belongs to the application or the active blueprint. A
handler on another blueprint, or a catch-all ``Exception`` handler, does not
replace the default 503.


7) Response Headers
===================

Allowed responses (any non-429)
-------------------------------

Whenever the rate-limit check passes, the integration attaches three headers
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
   ``500`` after the check passed still carries the ``RateLimit-*`` headers.
   These headers describe rate-limit state, not the response outcome. HTTP 429
   responses follow the separate exception-handling path described above.

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


8) Constraints and Known Limitations
====================================

.. _flask-decorator-order:

Decorator ordering
------------------

Keep the Flask route decorator above ``@limiter.limit()``:

.. code-block:: python

   @app.get("/items")
   @limiter.limit()
   def list_items():
       return {"ok": True}

Reversing the decorators disables rate limiting because Flask registers the
callable when ``@app.get`` runs:

.. code-block:: python

   # Incorrect: Flask registers the unwrapped function.
   @limiter.limit()
   @app.get("/items")
   def list_items():
       return {"ok": True}


Async view execution
--------------------

The decorator supports Flask ``async def`` views through
``current_app.ensure_sync``:

.. code-block:: python

   @app.get("/async-items")
   @limiter.limit()
   async def list_items():
       items = await load_items()
       return {"items": items}

Install Flask's async dependencies to use async views:

.. code-block:: bash

   pip install 'flask[async]'

This is Flask's WSGI async-view support, not the asynchronous throttled API.
Each request still occupies one worker, and the rate-limit check and store
remain synchronous. Use ``throttled.asyncio.contrib.fastapi`` for an ASGI-native
async integration.


Stacked limiter evaluation and headers
--------------------------------------

Stacked limiters execute from the outermost decorator to the innermost and stop
at the first rejection. Consequently, a limiter that rejects a request prevents
inner limiters from checking or consuming their buckets.

On successful requests, the innermost limiter supplies the response headers. On
HTTP 429 responses, headers from the rejecting exception are preserved. The
integration does not expose every stacked limiter's state in one response.
