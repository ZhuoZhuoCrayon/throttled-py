======================
Quota Configuration
======================

1) Quick Setup
=======================

You can pass a readable quota string directly to :class:`Throttled <throttled.Throttled>`.

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/quota_dsl_example.py
            :language: python


    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/quota_dsl_example.py
            :language: python

Supported patterns:

- ``n / unit``
- ``n / unit burst <burst>``
- ``n per unit``
- ``n per unit burst <burst>``

Where ``burst`` means extra bucket capacity for short spikes. It is effective for:

- ``TOKEN_BUCKET``
- ``LEAKING_BUCKET``
- ``GCRA``

If ``burst`` is omitted in quota string mode, it defaults to ``n`` in the same
rule. For example, ``1/s`` is equivalent to ``1/s burst 1``.

Supported units and compatibility forms:

.. list-table::
    :header-rows: 1
    :widths: 20 16 44 20

    * - Canonical unit
      - Short form
      - Compatible forms
      - Example
    * - ``second``
      - ``s``
      - ``s``, ``sec``, ``secs``, ``second``, ``seconds``
      - ``100/s`` / ``100 per sec``
    * - ``minute``
      - ``m``
      - ``m``, ``min``, ``mins``, ``minute``, ``minutes``
      - ``60/m`` / ``60 per min``
    * - ``hour``
      - ``h``
      - ``h``, ``hr``, ``hrs``, ``hour``, ``hours``
      - ``10/h`` / ``10 per hour``
    * - ``day``
      - ``d``
      - ``d``, ``day``, ``days``
      - ``5/d`` / ``5 per day``
    * - ``week``
      - ``w``
      - ``w``, ``wk``, ``wks``, ``week``, ``weeks``
      - ``1/w`` / ``1 per week``


2) Custom Quota
=======================

If quota string patterns are not enough for your scenario, you can still build
``Quota`` objects programmatically:

.. literalinclude:: ../../../examples/quickstart/quota_example.py
    :language: python
