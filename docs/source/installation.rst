=================
Installation
=================

Install the package with pip:

.. code-block::

    $ pip install throttled-py

.. note::

    ``v3.x`` requires Python ``>=3.10``.
    If you are using Python ``3.8/3.9``, install ``throttled-py<3.0.0``.


1) Optional Dependencies
=========================

Starting from `v2.0.0 <https://github.com/ZhuoZhuoCrayon/throttled-py/releases/tag/v2.0.0>`_,
only core dependencies are installed by default.

To enable additional features, install optional dependencies as follows (multiple extras can
be comma-separated):

.. code-block:: shell

    $ pip install "throttled-py[redis]"
    $ pip install "throttled-py[otel]"
    $ pip install "throttled-py[redis,otel]"


2) Extras
==========

+------------+--------------------------------------------------------------------------------------+
| Extra      | Description                                                                          |
+============+======================================================================================+
| ``memory`` | In-Memory backend is available by default (``memory`` extra installs no dependencies). |
+------------+--------------------------------------------------------------------------------------+
| ``redis``  | Use Redis as storage backend.                                                        |
+------------+--------------------------------------------------------------------------------------+
| ``otel``   | OpenTelemetry metrics integration.                                                   |
+------------+--------------------------------------------------------------------------------------+
