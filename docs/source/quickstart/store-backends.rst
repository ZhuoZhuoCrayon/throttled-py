=================
Store Backends
=================

1) In-Memory
=================

``MemoryStore`` is essentially a memory-based
`LRU Cache <https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU>`_ with expiration time, it is thread-safe and
can be used for rate limiting in a single process.

By default, ``Throttled`` will initialize a global ``MemoryStore`` instance with maximum capacity of 1024,
so **you don't usually need to create it manually.**

Also note that ``throttled.store.MemoryStore`` and ``throttled.asyncio.MemoryStore`` are implemented based on
``threading.RLock`` and ``asyncio.Lock`` respectively, so the global instance is also independent
for synchronous and asynchronous usage.

Different instances mean different storage spaces, if you want to limit the same key in different places
in your program, **make sure that** ``Throttled`` **receives the same** ``MemoryStore`` **instance** and
uses the same ``Quota`` configuration.

The following example uses ``MemoryStore`` as the storage backend and throttles the same Key on ping and pong:

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/memory_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/memory_example.py
       :language: python


2) Redis
=================

``RedisStore`` is implemented based on `redis-py <https://github.com/redis/redis-py>`_, you can use it for
rate limiting in a distributed environment.

It supports the following arguments:

* ``server``: Standard `Redis URL <https://github.com/redis/lettuce/wiki/Redis-URI-and-connection-details#uri-syntax>`_.

* ``options``: Redis connection configuration, supports all configuration items of `redis-py <https://github.com/redis/redis-py>`_.

The following example uses ``RedisStore`` as the storage backend:

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/redis_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/redis_example.py
       :language: python
