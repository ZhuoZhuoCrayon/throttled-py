=================
Function Call
=================

Using ``Throttled`` to check if a request is allowed is very simple.

You just need to call the ``limit`` method and pass in the specified ``key``, which will return a ``RateLimitResult``.

**It is important to note that** ``limit`` **does not raise any exceptions**, you can determine whether the request is
allowed by checking the ``RateLimitResult.limited`` attribute.

You can also get a snapshot of the Throttled state after calling ``limit`` through the ``RateLimitResult.state``
attribute.

If you just want to check the latest state of ``Throttled`` without deducting requests, you can use the ``peek``
method, which will also return a ``RateLimitState``.

The following example will guide you through the basic usage of ``Throttled``:

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/function_call_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/function_call_example.py
       :language: python
