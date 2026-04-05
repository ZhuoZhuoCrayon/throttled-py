======================
Quota Configuration
======================

:class:`Quota <throttled.rate_limiter.Quota>` represents the rules for rate limiting.


1) Quick Setup
=======================

``throttled-py`` provides quick functions to configure common time-based :class:`Quota <throttled.rate_limiter.Quota>`.

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python

            from throttled import rate_limiter

            rate_limiter.per_sec(60)    # 60 req/sec
            rate_limiter.per_min(60)    # 60 req/min
            rate_limiter.per_hour(60)   # 60 req/hour
            rate_limiter.per_day(60)    # 60 req/day
            rate_limiter.per_week(60)   # 60 req/week


    .. tab-item:: Async
        :sync: async

        .. code-block:: python

            from throttled.asyncio import rate_limiter

            rate_limiter.per_sec(60)    # 60 req/sec
            rate_limiter.per_min(60)    # 60 req/min
            rate_limiter.per_hour(60)   # 60 req/hour
            rate_limiter.per_day(60)    # 60 req/day
            rate_limiter.per_week(60)   # 60 req/week


2) Quota DSL
===================

You can also configure quota directly with a readable DSL string when creating
:class:`Throttled <throttled.Throttled>`.

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python

            from throttled import Throttled

            # limit only
            Throttled(quota="100/s")
            # limit + burst
            Throttled(quota="100 per second burst 200")


    .. tab-item:: Async
        :sync: async

        .. code-block:: python

            from throttled.asyncio import Throttled

            # limit only
            Throttled(quota="100/s")
            # limit + burst
            Throttled(quota="100 per second burst 200")

The object-based :class:`Quota <throttled.rate_limiter.Quota>` API remains
fully supported and is still the recommended option for complex programmatic
construction.


3) Custom Quota
===================

If the quick configuration does not meet your needs, you can customize the :class:`Quota <throttled.rate_limiter.Quota>`
through the :py:meth:`per_duration <throttled.rate_limiter.per_duration>` method:

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python

            from datetime import timedelta
            from throttled import rate_limiter

            # A total of 120 requests are allowed in two minutes, and a burst of 150 requests is allowed.
            rate_limiter.per_duration(timedelta(minutes=2), limit=120, burst=150)


    .. tab-item:: Async
        :sync: async

        .. code-block:: python

            from datetime import timedelta
            from throttled.asyncio import rate_limiter

            # A total of 120 requests are allowed in two minutes, and a burst of 150 requests is allowed.
            rate_limiter.per_duration(timedelta(minutes=2), limit=120, burst=150)


4) Burst Capacity
===================

The :py:attr:`burst <throttled.rate_limiter.Quota.burst>` argument can be used to adjust the ability of
the throttling object to handle burst traffic.

This is valid for the following algorithms:

* ``TOKEN_BUCKET``
* ``LEAKING_BUCKET``
* ``GCRA``

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. code-block:: python

            from throttled import rate_limiter

            # Allow 120 burst requests.
            # When burst is not specified, the default setting is the limit passed in.
            rate_limiter.per_min(60, burst=120)


    .. tab-item:: Async
        :sync: async

        .. code-block:: python

            from throttled.asyncio import rate_limiter

            # Allow 120 burst requests.
            # When burst is not specified, the default setting is the limit passed in.
            rate_limiter.per_min(60, burst=120)
