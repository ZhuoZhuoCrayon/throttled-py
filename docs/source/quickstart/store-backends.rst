=================
Store Backends
=================

.. _store-backends-in-memory:

1) In-Memory
=================

:class:`MemoryStore <throttled.store.MemoryStore>` is essentially a memory-based
`LRU Cache <https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU>`_ with expiration time, it is thread-safe and
can be used for rate limiting in a single process.

By default, :class:`Throttled <throttled.Throttled>` will initialize a global
:class:`MemoryStore <throttled.store.MemoryStore>` instance with maximum capacity of 1024,
so **you don't usually need to create it manually.**

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/global_memory_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/global_memory_example.py
       :language: python


Also note that ``throttled.store.MemoryStore`` and ``throttled.asyncio.store.MemoryStore`` are implemented based on
``threading.RLock`` and ``asyncio.Lock`` respectively, so the global instance is also independent
for synchronous and asynchronous usage.

Different instances mean different storage spaces, if you want to limit the same key in different places
in your program, **make sure that** :class:`Throttled <throttled.Throttled>` **receives the same**
:class:`MemoryStore <throttled.store.MemoryStore>` **instance** and uses the same
:class:`Quota <throttled.rate_limiter.Quota>` configuration.

The following example uses :class:`MemoryStore <throttled.store.MemoryStore>` as the storage backend and
throttles the same Key on ping and pong:

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/memory_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/memory_example.py
       :language: python


.. _store-backends-redis:

2) Redis
=================

:class:`RedisStore <throttled.store.RedisStore>` is implemented based on `redis-py <https://github.com/redis/redis-py>`_,
you can use it for rate limiting in a distributed environment.

It supports the following arguments:

* ``server``: `Standard Redis URL`.

* ``options``: Redis connection configuration, supports all configuration items
  of `redis-py <https://github.com/redis/redis-py>`_, see :ref:`RedisStore Options <store-configuration-redis-store-options>`.

The following examples demonstrate how to use :class:`RedisStore <throttled.store.RedisStore>` with different Redis deployment types.

.. _store-backend-redis-standalone:

2.1) Standalone
-----------------------------

Three ``server`` formats are supported for standalone Redis:

- ``redis://`` creates a TCP socket connection. See more at: `Redis URI Schemes <https://www.iana.org/assignments/uri-schemes/prov/redis>`_.
- ``rediss://`` creates a SSL wrapped TCP socket connection. See more at: `Redis SSL URI Schemes <https://www.iana.org/assignments/uri-schemes/prov/rediss>`_.
- ``unix://`` creates a Unix Domain Socket connection.


For example:

.. code-block::

    redis://[[username]:[password]@]localhost:6379/0
    rediss://[[username]:[password]@]localhost:6379/0
    unix://[username@]/path/to/socket.sock?db=0[&password=password]

.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/redis_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/redis_example.py
       :language: python

2.2) Sentinel
-----------------------------

It is also easy to use :class:`RedisStore <throttled.store.RedisStore>` with Redis Sentinel.

``server`` format for Redis Sentinel is as follows:

.. code-block::

    redis+sentinel://[[username]:[password]@]host1[:port1][,hostN][:portN][/service_name]

* username: ``[Optional]`` Authentication username
* password: ``[Optional]`` Authentication password
* host: ``[Required]`` Sentinel node hostname or IP address.
* port: ``[Optional]`` Sentinel node port, default is 26379.
* service_name: ``[Optional]`` Name of the master service monitored by Sentinel, default is ``mymaster``.


.. tab:: Sync

    .. literalinclude:: ../../../examples/quickstart/redis_sentinel_example.py
       :language: python


.. tab:: Async

    .. literalinclude:: ../../../examples/quickstart/async/redis_sentinel_example.py
       :language: python


3) References
=================

- `redis-py Connecting to Redis <https://redis.readthedocs.io/en/stable/connections.html#connecting-to-redis>`_
