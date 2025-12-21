======================
Specifying Algorithms
======================


The rate limiting algorithm is specified by the ``using`` parameter in the :py:meth:`Throttled <throttled.Throttled.__init__>`.

The supported algorithms are as follows:

* `Fixed Window <https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8>`_ : ``RateLimiterType.FIXED_WINDOW.value``
* `Sliding Window <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3>`_: ``RateLimiterType.SLIDING_WINDOW.value``
* `Token Bucket <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6>`_: ``RateLimiterType.TOKEN_BUCKET.value``
* `Leaky Bucket <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6>`_: ``RateLimiterType.LEAKING_BUCKET.value``
* `Generic Cell Rate Algorithm, GCRA <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra>`_: ``RateLimiterType.GCRA.value``

.. tab-set::

    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: ../../../examples/quickstart/using_algorithm_example.py
           :language: python

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: ../../../examples/quickstart/async/using_algorithm_example.py
           :language: python
