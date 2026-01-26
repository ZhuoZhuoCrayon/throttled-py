=============
OpenTelemetry
=============

``OTelHook`` provides OpenTelemetry metrics integration for monitoring rate limiting events.

Installation
============

Install throttled-py with OpenTelemetry support:

.. code-block:: bash

   pip install 'throttled-py[otel]'

This installs ``opentelemetry-api`` only. throttled-py emits metrics in OpenTelemetry format - how you collect and export them is up to your application.


Quick Start
===========

.. code-block:: python

   from opentelemetry import metrics

   from throttled import Throttled, per_sec
   from throttled.contrib.otel import OTelHook

   # Get meter from your application's OpenTelemetry setup
   meter = metrics.get_meter("my-app")

   # Create hook and use with Throttled
   hook = OTelHook(meter)
   throttle = Throttled(
       key="/api/users",
       quota=per_sec(100),
       hooks=[hook],
   )

   # Rate limiting - metrics are automatically recorded
   result = throttle.limit()


Metrics
=======

``OTelHook`` records the following metrics:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Metric Name
     - Type
     - Description
   * - ``throttled.requests``
     - Counter
     - Number of rate limit checks (with ``result`` dimension)
   * - ``throttled.duration``
     - Histogram
     - Duration of rate limit checks in seconds

All metrics include these attributes:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Attribute
     - Description
   * - ``key``
     - The rate limit key (e.g., "/api/users", "user:123")
   * - ``algorithm``
     - Algorithm used (e.g., "token_bucket", "fixed_window")
   * - ``store_type``
     - Storage backend (e.g., "memory", "redis")
   * - ``result``
     - Result of rate limit check: "allowed" or "denied"


Configuration
=============

``OTelHook`` requires a ``Meter`` instance:

.. code-block:: python

   from opentelemetry import metrics
   from throttled.contrib.otel import OTelHook

   meter = metrics.get_meter("my-service", "1.0.0")
   hook = OTelHook(meter)

This follows the dependency injection pattern - you control the meter configuration.


Architecture
============

throttled-py depends only on ``opentelemetry-api``, not the SDK:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────────────┐
   │                    throttled-py                                     │
   │   Dependency: opentelemetry-api (interface only)                    │
   │   Output: counter.add(), histogram.record()                         │
   └──────────────────────────────┬──────────────────────────────────────┘
                                  │
                                  v
   ┌─────────────────────────────────────────────────────────────────────┐
   │                 Your Application                                    │
   │   You decide how to collect and export metrics:                     │
   │   - Console, OTLP, Prometheus, Datadog, etc.                        │
   └─────────────────────────────────────────────────────────────────────┘

This keeps the library lightweight. You have full control over how metrics are exported.


Exporter Examples
=================

Below are examples of how you might configure exporters in your application.
These are just examples - use whatever setup fits your infrastructure.

Console (for debugging)
-----------------------

.. code-block:: python

   from opentelemetry import metrics
   from opentelemetry.sdk.metrics import MeterProvider
   from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

   reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
   provider = MeterProvider(metric_readers=[reader])
   metrics.set_meter_provider(provider)

   # Now get_meter() will use this provider
   meter = metrics.get_meter("my-app")

OTLP
----

.. code-block:: python

   from opentelemetry import metrics
   from opentelemetry.sdk.metrics import MeterProvider
   from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
   from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

   reader = PeriodicExportingMetricReader(
       OTLPMetricExporter(endpoint="http://collector:4317")
   )
   provider = MeterProvider(metric_readers=[reader])
   metrics.set_meter_provider(provider)

Prometheus
----------

.. code-block:: python

   from opentelemetry import metrics
   from opentelemetry.sdk.metrics import MeterProvider
   from opentelemetry.exporter.prometheus import PrometheusMetricReader
   from prometheus_client import start_http_server

   start_http_server(port=8000)
   reader = PrometheusMetricReader()
   provider = MeterProvider(metric_readers=[reader])
   metrics.set_meter_provider(provider)

   # Metrics available at http://localhost:8000/metrics


Grafana Dashboard Example
=========================

Example PromQL queries for Grafana:

.. code-block:: promql

   # Request rate by key
   sum(rate(throttled_requests_total[5m])) by (key)

   # Denial rate
   sum(rate(throttled_requests_total{result="denied"}[5m]))
   /
   sum(rate(throttled_requests_total[5m]))

   # Allowed vs Denied comparison
   sum(rate(throttled_requests_total{result="allowed"}[5m]))
   sum(rate(throttled_requests_total{result="denied"}[5m]))

   # P95 duration by algorithm
   histogram_quantile(0.95, rate(throttled_duration_bucket[5m])) by (algorithm)