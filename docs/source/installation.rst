=================
Installation
=================

Install the package with pip:

.. code-block::

    $ pip install throttled-py


1) Optional Dependencies
=========================

Starting from `v2.0.0 <https://github.com/ZhuoZhuoCrayon/throttled-py/releases/tag/v2.0.0>`_,
only core dependencies(``in-memory``) are installed by default.

To enable additional features, install optional dependencies as follows (multiple extras can
be comma-separated):

.. code-block:: shell

    $ pip install "throttled-py[redis]"
    $ pip install "throttled-py[redis,in-memory]"


2) Extras
==========

+--------------+--------------------------------------+
| Extra        | Description                          |
+==============+======================================+
| ``all``      | Install all extras.                  |
+--------------+--------------------------------------+
| ``in-memory``| Use In-Memory as storage backend.    |
+--------------+--------------------------------------+
| ``redis``    | Use Redis as storage backend.        |
+--------------+--------------------------------------+
| ``otel``     | OpenTelemetry metrics integration.   |
+--------------+--------------------------------------+

