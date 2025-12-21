=================
Function Call
=================

Using :class:`Throttled <throttled.Throttled>` to check if a request is allowed is very simple.

You just need to call the :py:meth:`Throttled.limit <throttled.Throttled.limit>` method and pass in the specified ``key``,
which will return a :class:`RateLimitResult <throttled.RateLimitResult>` object.

**It is important to note that** :py:meth:`Throttled.limit <throttled.Throttled.limit>`
**does not raise any exceptions**, you can determine whether the request is allowed by checking the
:py:attr:`RateLimitResult.limited <throttled.RateLimitResult.limited>` attribute.

You can also get a snapshot of the Throttled state after calling :py:meth:`Throttled.limit <throttled.Throttled.limit>`
through the :py:attr:`RateLimitResult.state <throttled.RateLimitResult.state>` attribute.

If you just want to check the latest state of :class:`Throttled <throttled.Throttled>` without deducting requests,
you can use the :py:meth:`Throttled.peek <throttled.Throttled.peek>` method,
which will also return a :class:`RateLimitState <throttled.RateLimitState>` object.

The following example will guide you through the basic usage of :class:`Throttled <throttled.Throttled>`:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/function_call_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/function_call_example.py
           :language: python
