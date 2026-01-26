=====
Hooks
=====

The Hook system provides a flexible middleware pattern for extending rate limiting behavior.
Hooks can be used for:

- **Observability**: Monitor rate limiting events, record metrics
- **Timing**: Measure duration of rate limit checks
- **Exception handling**: Gracefully handle errors in the rate limiting flow
- **Custom logic**: Add pre/post processing around rate limit checks


1) Basic Usage
==============

.. code-block:: python

   from collections.abc import Callable

   from throttled import Throttled, per_sec, Hook, HookContext, RateLimitResult

   class LoggingHook(Hook):
       def on_limit(
           self,
           call_next: Callable[[], RateLimitResult],
           context: HookContext,
       ) -> RateLimitResult:
           # Before rate limit check
           print(f"Checking rate limit for {context.key}")

           # Execute rate limit check
           result = call_next()

           # After rate limit check
           status = "denied" if result.limited else "allowed"
           print(f"[{context.key}] {status} - remaining: {result.state.remaining}")

           return result

   hook = LoggingHook()
   throttle = Throttled(
       key="/api/users",
       quota=per_sec(10),
       hooks=[hook],
   )

   result = throttle.limit()
   # Output:
   # Checking rate limit for /api/users
   # [/api/users] allowed - remaining: 9


2) Middleware Pattern
=====================

Hooks follow the middleware pattern (Chain of Responsibility). When you register multiple hooks,
they are executed in order, wrapping the rate limit operation:

.. code-block:: text

   hooks = [A, B]

   Execution order:
   A.on_limit (before) → B.on_limit (before) → rate_limit → B.on_limit (after) → A.on_limit (after)

This allows each hook to:

1. Execute logic **before** the rate limit check
2. Call ``call_next()`` to continue the chain
3. Execute logic **after** the rate limit check
4. Inspect or modify the result


3) HookContext
==============

The ``HookContext`` is an immutable dataclass containing information about the rate limit request:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Attribute
     - Type
     - Description
   * - ``key``
     - ``str``
     - The identifier being rate-limited (e.g., user_id, IP address)
   * - ``cost``
     - ``int``
     - The cost of the current request
   * - ``algorithm``
     - ``str``
     - The algorithm used (e.g., "token_bucket", "fixed_window")
   * - ``store_type``
     - ``str``
     - The storage backend type (e.g., "memory", "redis")

.. note::

   ``HookContext`` does not include the result. The result is obtained by calling ``call_next()``.


4) Creating Custom Hooks
========================

To create a custom hook, inherit from ``Hook`` and implement the ``on_limit`` method:

.. code-block:: python

   import time
   from collections.abc import Callable

   from throttled import Hook, HookContext, RateLimitResult

   class TimingHook(Hook):
       def on_limit(
           self,
           call_next: Callable[[], RateLimitResult],
           context: HookContext,
       ) -> RateLimitResult:
           start = time.perf_counter()
           result = call_next()
           duration = time.perf_counter() - start

           print(f"Rate limit check took {duration:.4f}s")
           return result


Best Practices
--------------

1. **Always call call_next()**: The hook must call ``call_next()`` to continue the chain and return its result.

   .. code-block:: python

      class MyHook(Hook):
          def on_limit(self, call_next, context):
              # Must call call_next() and return its result
              result = call_next()
              return result

2. **Handle exceptions gracefully**: If your hook raises an exception, it will be caught and the hook is skipped entirely - the chain continues by calling the next hook directly. To ensure your hook doesn't get skipped, wrap risky operations in try/except:

   .. code-block:: python

      class SafeHook(Hook):
          def on_limit(self, call_next, context):
              # Pre-processing with error handling
              try:
                  self.validate_request(context)
              except Exception as e:
                  logging.warning(f"Pre-processing failed: {e}")

              # call_next() outside try/except - always executes
              result = call_next()

              # Post-processing with error handling
              try:
                  self.send_metrics(result, context)
              except Exception as e:
                  logging.warning(f"Post-processing failed: {e}")

              return result

3. **Keep hooks fast**: The ``on_limit`` method runs synchronously. For slow operations (HTTP calls, database writes), use a queue or background task.

   .. code-block:: python

      class AsyncMetricsHook(Hook):
          def __init__(self, queue):
              self.queue = queue

          def on_limit(self, call_next, context):
              result = call_next()
              # Non-blocking: add to queue for async processing
              self.queue.put_nowait({
                  "key": context.key,
                  "limited": result.limited,
                  "timestamp": time.time(),
              })
              return result

4. **Use multiple hooks**: You can register multiple hooks for different purposes.

   .. code-block:: python

      throttle = Throttled(
          key="/api",
          quota=per_sec(100),
          hooks=[
              TimingHook(),
              LoggingHook(),
              MetricsHook(statsd_client),
          ],
      )


5) Built-in Hooks
=================

throttled-py provides the following built-in hooks:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Hook
     - Description
   * - :doc:`OTelHook </observability/opentelemetry>`
     - OpenTelemetry metrics integration for monitoring rate limiting events.