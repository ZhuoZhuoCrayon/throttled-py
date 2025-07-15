=================
*throttled-py*
=================

.. container:: badges

   .. image:: https://img.shields.io/badge/python-%3E%3D3.8-green?style=for-the-badge&logo=python
      :target: https://github.com/ZhuoZhuoCrayon/throttled-py
      :class: header-badge
   .. image:: https://img.shields.io/codecov/c/github/ZhuoZhuoCrayon/throttled-py?logo=codecov&style=for-the-badge
      :target: https://app.codecov.io/gh/ZhuoZhuoCrayon/throttled-py
      :class: header-badge
   .. image:: https://img.shields.io/pypi/v/throttled-py?&color=blue&style=for-the-badge&logo=python
      :target: https://pypi.org/project/throttled-py/
      :class: header-badge
   .. image:: https://img.shields.io/badge/issue-welcome-green?style=for-the-badge&logo=github
      :target: https://pypi.org/project/throttled-py/
      :class: header-badge


Introduction
=================

*throttled-py* is a high-performance Python rate limiting library with
multiple algorithms(Fixed Window, Sliding Window, Token Bucket, Leaky Bucket & GCRA)
and storage backends (Redis, In-Memory).


Features
=================

*   Supports both synchronous and `asynchronous <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#3-asynchronous>`_ (``async / await``).
*   Provides thread-safe storage backends: `Redis <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#redis>`_, `In-Memory (with support for key expiration and eviction) <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#in-memory>`_.
*   Supports multiple rate limiting algorithms: `Fixed Window <https://github.com/ZhuoZhuoCrayon/throttled-py/tree/main/docs/basic#21-%E5%9B%BA%E5%AE%9A%E7%AA%97%E5%8F%A3%E8%AE%A1%E6%95%B0%E5%99%A8>`_, `Sliding Window <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#22-%E6%BB%91%E5%8A%A8%E7%AA%97%E5%8F%A3>`_, `Token Bucket <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#23-%E4%BB%A4%E7%89%8C%E6%A1%B6>`_, `Leaky Bucket <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#24-%E6%BC%8F%E6%A1%B6>`_ & `Generic Cell Rate Algorithm (GCRA) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/docs/basic/readme.md#25-gcra>`_.
*   Supports `configuration of rate limiting algorithms <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#3-algorithms>`_ and provides flexible `quota configuration <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#4-quota-configuration>`_.
*   Supports immediate response and `wait-retry <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#wait--retry>`_ modes, and provides `function call <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#function-call>`_, `decorator <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#decorator>`_, and `context manager <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#context-manager>`_ modes.
*   Supports integration with the `MCP <https://modelcontextprotocol.io/introduction>`_ `Python SDK <https://github.com/modelcontextprotocol/python-sdk>`_ to provide rate limiting support for model dialog processes.
*   Excellent performance, The execution time for a single rate limiting API call is equivalent to (see `Benchmarks <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#-benchmarks>`_ for details):

    *   In-Memory: ~2.5-4.5x ``dict[key] += 1`` operations.
    *   Redis: ~1.06-1.37x ``INCRBY key increment`` operations.

Contents
=================

.. toctree::
   :maxdepth: 3
   :titlesonly:

   installation
   quickstart/index
   advance_usage/index
   changelog
   benchmarks
   api
