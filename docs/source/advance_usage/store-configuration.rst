===================
Store Configuration
===================


1) RedisStore
======================

``RedisStore`` is developed based on the Redis API provided by `redis-py <https://github.com/redis/redis-py>`_.

In terms of Redis connection configuration management, the configuration naming of
`django-redis <https://github.com/jazzband/django-redis>`_ is basically used to reduce the learning cost.


.. tab:: Sync

    .. code-block:: python

        from throttled import store

        store.RedisStore(server="redis://127.0.0.1:6379/0", options={})


.. tab:: Async

    .. code-block:: python

        from throttled.asyncio import store

        store.RedisStore(server="redis://127.0.0.1:6379/0", options={})

.. _store-configuration-redis-store-arguments:

Arguments
-----------

.. list-table::
   :widths: 30 50 20
   :header-rows: 1

   * - Parameter
     - Description
     - Default
   * - ``server``
     - Standard Redis URL, you can use it to connect to Redis in any deployment mode, see :ref:`Store Backends <store-backend-redis-standalone>`.
     - ``"redis://localhost:6379/0"``
   * - ``options``
     - <Options>
     - ``{}``

.. _store-configuration-redis-store-options:

Options
-----------

.. list-table::
   :widths: 30 50 20
   :header-rows: 1

   * - Parameter
     - Description
     - Default
   * - ``SOCKET_TIMEOUT``
     - ConnectionPool parameters.
     - ``null``
   * - ``SOCKET_CONNECT_TIMEOUT``
     - ConnectionPool parameters.
     - ``null``
   * - ``CONNECTION_POOL_KWARGS``
     - `ConnectionPool construction parameters <https://redis.readthedocs.io/en/stable/connections.html#connectionpool>`_.
     - ``{}``
   * - ``REDIS_CLIENT_KWARGS``
     - `RedisClient construction parameters <https://redis.readthedocs.io/en/stable/connections.html#redis.Redis>`_.
     - ``{}``
   * - ``SENTINEL_KWARGS``
     - `Sentinel construction parameters <https://redis.readthedocs.io/en/stable/connections.html#id1>`_.
     - ``{}``
   * - ``CONNECTION_FACTORY_CLASS``
     - ConnectionFactory is used to create and maintain `ConnectionPool <https://redis.readthedocs.io/en/stable/connections.html#redis.connection.ConnectionPool>`_.
     - Automatically select via the ``server`` scheme by default.

       Standalone: ``"throttled.store.ConnectionFactory"``
       Sentinel: ``"throttled.store.SentinelConnectionFactory"``
   * - ``REDIS_CLIENT_CLASS``
     - RedisClient import path.
     - Automatically select sync/async mode by default.

       Sync: ``"redis.client.Redis"``

       Async: ``"redis.asyncio.client.Redis"``
   * - ``CONNECTION_POOL_CLASS``
     - ConnectionPool import path.
     - Automatically select via the ``server`` scheme and sync/async mode by default.

       Sync(Standalone): ``"redis.connection.ConnectionPool"``

       Async(Standalone): ``"redis.asyncio.connection.ConnectionPool"``

       Sync(Sentinel): ``"redis.sentinel.SentinelConnectionPool"``

       Async(Sentinel): ``"redis.asyncio.sentinel.SentinelConnectionPool"``
   * - ``SENTINEL_CLASS``
     - Sentinel import path.
     - Automatically select sync/async mode by default.

       Sync: ``"redis.Sentinel"``

       Async: ``"redis.asyncio.Sentinel"``


2) MemoryStore
======================

``MemoryStore`` is essentially a memory-based
`LRU Cache <https://en.wikipedia.org/wiki/Cache_replacement_policies#LRU>`_ with expiration time.


.. tab:: Sync

    .. code-block:: python

        from throttled import store

        store.MemoryStore(options={"MAX_SIZE": 10240})

.. tab:: Async

    .. code-block:: python

        from throttled.asyncio import store

        store.MemoryStore(options={"MAX_SIZE": 10240})

.. _store-configuration-memory-store-arguments:

Arguments
-----------

+------------------------------+-----------------------------------------------------------------------------------------------------------+--------------------------------+
| ``options``                  | <Options>                                                                                                 | ``{}``                         |
+------------------------------+-----------------------------------------------------------------------------------------------------------+--------------------------------+

.. _store-configuration-memory-store-options:

Options
-----------

+--------------+--------------------------------------------------------------------------------------------------------------------------------------------------+----------+
| Parameter    | Description                                                                                                                                      | Default  |
+==============+==================================================================================================================================================+==========+
| ``MAX_SIZE`` | Maximum capacity. When the number of stored key-value pairs exceeds ``MAX_SIZE``, they will be eliminated according to the LRU policy.           | ``1024`` |
+--------------+--------------------------------------------------------------------------------------------------------------------------------------------------+----------+
