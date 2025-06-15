=================
Decorator
=================

You can use ``Throttled`` as a decorator, and the ``limit`` method will check if the request is allowed
before the wrapped function call.

If the request is not allowed, it will raise a ``LimitedError``.

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/decorator_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/decorator_example.py
       :language: python
