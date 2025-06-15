=================
Context Manager
=================

You can use the context manager to limit the code block.
When access is allowed, return `RateLimitResult <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-ratelimitresult>`_.

If the limit is exceeded or the retry timeout is exceeded,
it will raise `LimitedError <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#limitederror>`_.

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/context_manager_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/context_manager_example.py
       :language: python
