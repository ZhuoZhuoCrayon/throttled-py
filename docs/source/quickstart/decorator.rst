=================
Decorator
=================

You can use :class:`Throttled <throttled.Throttled>` as a decorator, and
the :py:meth:`limit <throttled.Throttled.limit>` method will check if
the request is allowed before the wrapped function call.

If the request is not allowed, it will raise :class:`LimitedError <throttled.exceptions.LimitedError>`.

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/decorator_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/decorator_example.py
           :language: python
