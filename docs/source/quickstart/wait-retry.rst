=================
Wait & Retry
=================

By default, :class:`Throttled <throttled.Throttled>` returns :class:`RateLimitResult <throttled.RateLimitResult>` immediately.

To enable wait-and-retry behavior, you can use the ``timeout`` parameter.

:class:`Throttled <throttled.Throttled>` will wait according to the
:py:attr:`RateLimitState.retry_after <throttled.RateLimitState.retry_after>` and retry automatically.

In the :doc:`Function Call </quickstart/function-call>` mode will return
the last retried :class:`RateLimitResult <throttled.RateLimitResult>`:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/wait_retry_function_call_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/wait_retry_function_call_example.py
           :language: python



In the :doc:`Decorator </quickstart/decorator>` and :doc:`Context Manager </quickstart/context-manager>` modes,
:class:`LimitedError <throttled.exceptions.LimitedError>` will be raised if the request is not allowed after the timeout:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/wait_retry_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/wait_retry_example.py
           :language: python

In the above example, ``per_sec(2, burst=2)`` means allows 2 requests per second, and allows
2 burst requests (Bucket's capacity). In other words, :class:`Throttled <throttled.Throttled>` will consume the burst after 2 requests.
If timeout>=0.5 is set, the above example will complete all requests in 1.5 seconds (the burst is consumed
immediately, and the 3 requests will be filled in the subsequent 1.5s):

.. code-block::

    ------------- Burst---------------------
    Request 1 completed at 0.00s
    Request 2 completed at 0.00s
    ----------------------------------------
    -- Refill: 0.5 tokens per second -------
    Request 3 completed at 0.50s
    Request 4 completed at 1.00s
    Request 5 completed at 1.50s
    -----------------------------------------
    Total time for 5 requests at 2/sec: 1.50s


``Wait & Retry`` is most effective for smoothing out request rates, and you can feel its effect
through the following example:


.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/wait_retry_concurrent_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/wait_retry_concurrent_example.py
           :language: python
