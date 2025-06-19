=================
Quick Start
=================

1) Core API
=================

* ``limit``: Deduct requests and return `RateLimitResult <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult>`_.
* ``peek``: Check current rate limit state for a key and return `RateLimitState <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#2-ratelimitstate>`_.


2) Async Support
=================

The core API is the same for synchronous and asynchronous code.
Just replace ``from throttled import ...`` with ``from throttled.asyncio import ...`` in your code.


3) Example
=================

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/quickstart_example.py
       :language: python


.. tab:: Async

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
