=================
API Reference
=================

.. module:: throttled


Main Interface
=================

.. autoclass:: throttled.Throttled
    :inherited-members:
    :members:
    :special-members: __init__, __call__, __enter__
    :exclude-members: limiter


Store
=================

.. autoclass:: throttled.store.BaseStore
    :members:


Rate Limiting
=================

.. autoclass:: throttled.rate_limiter.Rate
    :members:
    :undoc-members:

.. autoclass:: throttled.rate_limiter.Quota
    :members:
    :undoc-members:
    :exclude-members: period_sec, emission_interval, fill_rate, get_period_sec, get_limit

.. autofunction:: throttled.rate_limiter.per_sec

.. autofunction:: throttled.rate_limiter.per_min

.. autofunction:: throttled.rate_limiter.per_hour

.. autofunction:: throttled.rate_limiter.per_day

.. autofunction:: throttled.rate_limiter.per_week

.. autofunction:: throttled.rate_limiter.per_duration


Exceptions
====================

All exceptions inherit from :class:`throttled.exceptions.BaseThrottledError`.

.. autoexception:: throttled.exceptions.BaseThrottledError
.. autoexception:: throttled.exceptions.SetUpError
.. autoexception:: throttled.exceptions.DataError
.. autoexception:: throttled.exceptions.StoreUnavailableError
.. autoexception:: throttled.exceptions.LimitedError


Lower-Level Classes
====================

.. autoclass:: throttled.RateLimiterType
    :members:
    :undoc-members:
    :exclude-members: choice

.. autoclass:: throttled.RateLimitResult
    :members:
    :undoc-members:

.. autoclass:: throttled.RateLimitState
    :members:
    :undoc-members:
