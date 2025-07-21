=================
Context Manager
=================

You can use the context manager to limit the code block.
When access is allowed, return :class:`RateLimitResult <throttled.RateLimitResult>`.

If the limit is exceeded or the retry timeout is exceeded,
it will raise :class:`LimitedError <throttled.exceptions.LimitedError>`.

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/context_manager_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/context_manager_example.py
       :language: python
