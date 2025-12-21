=================
Quick Start
=================

1) Core API
=================

* :py:meth:`Throttled.limit <throttled.Throttled.limit>`: Deduct requests and return :class:`RateLimitResult <throttled.RateLimitResult>` object.

* :py:meth:`Throttled.peek <throttled.Throttled.peek>`: Check current rate limit state for a key and return :class:`RateLimitState <throttled.RateLimitState>` object.


2) Async Support
=================

The core API is the same for synchronous and asynchronous code.
Just replace ``from throttled import ...`` with ``from throttled.asyncio import ...`` in your code.


3) Example
=================

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/quickstart_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/quickstart_example.py
           :language: python


4) Contents
=================

.. toctree::
   :maxdepth: 2

   function-call
   decorator
   context-manager
   wait-retry
   store-backends
   specifying-algorithms
   quota-configuration
