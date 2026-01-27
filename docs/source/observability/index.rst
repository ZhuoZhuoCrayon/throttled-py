=============
Observability
=============

throttled-py provides observability through a flexible :doc:`Hook system </advance_usage/hooks>`.
Hooks allow you to monitor rate limiting events and integrate with external monitoring systems.

Overview
========

Observability features enable:

- **Monitoring**: Track allowed/denied requests, current state
- **Metrics**: Record rate limiting metrics with OpenTelemetry
- **Alerting**: Trigger alerts when thresholds are exceeded
- **Analytics**: Analyze rate limiting patterns for optimization


Built-in Hooks
==============

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Hook
     - Description
   * - :doc:`OTelHook <opentelemetry>`
     - OpenTelemetry metrics integration for monitoring rate limiting events.

.. seealso::

   For information on creating custom hooks, see :doc:`/advance_usage/hooks`.


Contents
========

.. toctree::
   :maxdepth: 2

   opentelemetry