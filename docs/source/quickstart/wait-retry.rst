=================
Wait & Retry
=================

By default, ``Throttled`` returns
`RateLimitResult <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult>`_ immediately.

To enable wait-and-retry behavior, you can use the ``timeout`` parameter.

``Throttled`` will wait according to the ``RateLimitState.retry_after`` in
`RateLimitState <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#2-ratelimitstate>`_
and retry automatically.

In the :doc:`Function Call </quickstart/function-call>` mode will return the last retried ``RateLimitResult``:

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/wait_retry_function_call_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/wait_retry_function_call_example.py
       :language: python



In the :doc:`Decorator </quickstart/decorator>` and :doc:`Context Manager </quickstart/context-manager>` modes,
``LimitedError`` will be raised if the request is not allowed after the timeout:

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/wait_retry_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/wait_retry_example.py
       :language: python

In the above example, ``per_sec(2, burst=2)`` means allows 2 requests per second, and allows
2 burst requests (Bucket's capacity). In other words, ``Throttled`` will consume the burst after 2 requests.
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

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/wait_retry_concurrent_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/wait_retry_concurrent_example.py
       :language: python
