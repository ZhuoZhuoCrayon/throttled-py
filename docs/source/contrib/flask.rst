=====
Flask
=====

Decorator-based rate limiting for Flask applications. The integration checks
quotas before a decorated view runs, adds ``RateLimit-*`` headers to checked
responses, and renders quota exhaustion as HTTP 429.


Installation
============

.. code-block:: bash

   pip install 'throttled-py[flask]'

This installs Flask as an optional dependency. Async Flask views require
Flask's additional async dependencies:

.. code-block:: bash

   pip install 'flask[async]'


.. _flask-examples:

Examples
========

The examples below are runnable Flask applications covering the common quota
and initialization choices.

.. tab-set::

    .. tab-item:: Shared route quota

        .. literalinclude:: ../../../examples/contrib/flask/basic_example.py
           :language: python

    .. tab-item:: API key quota

        .. literalinclude:: ../../../examples/contrib/flask/custom_key_func_example.py
           :language: python

    .. tab-item:: Client IP quota

        .. literalinclude:: ../../../examples/contrib/flask/remote_address_example.py
           :language: python

    .. tab-item:: Application factory

        .. literalinclude:: ../../../examples/contrib/flask/multi_route_example.py
           :language: python

Run an example with the Flask development server:

.. code-block:: bash

   flask --app examples.contrib.flask.basic_example run


1) Basic Usage
==============

Pass an application to ``Limiter`` for eager initialization. By default,
requests with the same HTTP method and route share one quota bucket.

.. code-block:: python

   from flask import Flask
   from throttled.contrib.flask import Limiter

   app = Flask(__name__)
   limiter = Limiter("2/m", app=app)

   @app.get("/items")
   @limiter.limit()
   def list_items():
       return {"items": ["apple", "banana"]}

Test
----

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

.. code-block:: python

   from flask import Flask
   from throttled.contrib.flask import Limiter

   limiter = Limiter("10/m")

   def create_app() -> Flask:
       app = Flask(__name__)
       limiter.init_app(app)

       @app.get("/items")
       @limiter.limit()
       def list_items():
           return {"items": ["apple", "banana"]}

       return app

Repeated calls to ``init_app`` with the same limiter and application are
idempotent. Multiple limiter instances on one application share a single
``after_request`` header hook.

See the ``Application factory`` tab in :ref:`flask-examples` for a runnable
application with a per-route quota override.

Test
----

Run the application-factory example, then call both routes. ``/items`` uses the
default ``10/m`` quota while ``/admin`` overrides it with ``1/m``:

.. code-block:: bash

   $ flask --app examples.contrib.flask.multi_route_example run

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


3) Choosing a Key Function
==========================

Provide ``key_func`` when a quota should be tied to a caller identity. Flask
key functions take no arguments and read from the active request context.

.. code-block:: python

   from flask import request

   def get_api_key() -> str:
       return request.headers.get("X-API-Key", "anonymous")

   limiter = Limiter("2/m", app=app, key_func=get_api_key)

Each API key then receives an independent bucket for the same method and route.
Without ``key_func``, all callers share that route's bucket.

For direct client-address limiting, pass ``get_remote_address`` explicitly:

.. code-block:: python

   from throttled.contrib.flask import get_remote_address

   limiter = Limiter("100/m", app=app, key_func=get_remote_address)

``get_remote_address`` reads ``request.remote_addr``. When the application is
behind a reverse proxy, configure trusted proxy handling before treating that
value as a client identity.

Test
----

Run the API-key example and send requests for two principals. Exhausting
``user-a`` does not consume ``user-b``'s bucket:

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


4) Response Headers
===================

Checked responses carry three rate-limit headers:

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
     - Seconds until the quota resets, rounded up.

HTTP 429 responses also include ``Retry-After``, the number of seconds clients
should wait before retrying. Existing response headers take precedence when the
``after_request`` hook applies missing rate-limit headers.

When limiters are stacked, successful responses report the innermost limiter's
state. A 429 response preserves the headers rendered by the limiter that
rejected the request.


5) Error Handling
=================

No error handler registration is required. ``RateLimitExceededError`` is a
Werkzeug HTTP exception, so Flask renders a default 429 response with
``RateLimit-*`` and ``Retry-After`` headers.

Register an error handler to customize the body. If the handler constructs a
new response, carry forward the exception headers so the response retains the
rejecting limiter's metadata:

.. code-block:: python

   from flask import jsonify
   from throttled.contrib.flask import RateLimitExceededError

   @app.errorhandler(RateLimitExceededError)
   def handle_rate_limit(exc: RateLimitExceededError):
       headers = {
           name: value
           for name, value in exc.get_headers()
           if name.lower() != "content-type"
       }
       return jsonify(detail=exc.description), exc.code, headers

The exception also exposes ``rate_limit_context`` and inherits from the core
``LimitedError`` class for applications with shared error-handling code.


6) Constraints and Known Limitations
====================================

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

This is Flask's WSGI async-view support, not the asynchronous throttled API.
Each request still occupies one worker, and the rate-limit check and store
remain synchronous. Install ``flask[async]`` to use async views. Use
``throttled.asyncio.contrib.fastapi`` for an ASGI-native async integration.


Stacked limiter evaluation and headers
--------------------------------------

Stacked limiters execute from the outermost decorator to the innermost and stop
at the first rejection. Consequently, a limiter that rejects a request prevents
inner limiters from checking or consuming their buckets.

On successful requests, the innermost limiter supplies the response headers. On
HTTP 429 responses, headers from the rejecting exception are preserved. The
integration does not expose every stacked limiter's state in one response.
