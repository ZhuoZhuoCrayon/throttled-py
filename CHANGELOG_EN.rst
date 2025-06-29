Version History
================


v2.2.1 - 2025-06-28
---------------------

`简体中文 (v2.2.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v221---2025-06-28>`_ | English

**✨ Improvements**

- perf: added support for cost=0 in Throttled @ZhuoZhuoCrayon (#85)

**🐛 Bug Fixes**

- fix: fixed the inaccurate retry_after issue for "Token Bucket" & "Leaking Bucket" @ZhuoZhuoCrayon (#87)

**📝 Documentation**

- docs: added throttled-py usage documentation, welcome to visit <https://throttled-py.readthedocs.io/en/latest/> @ZhuoZhuoCrayon (#84)

**🍃 Maintenance**

- ci: update changelog link format in release drafter config @ZhuoZhuoCrayon (#86)

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.2.0...v2.2.1


v2.2.0 - 2025-05-31
-------------------

`简体中文 (v2.2.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v220---2025-05-31>`_ | English

**🚀 New Features**

- feat: enhance Throttled decorator with cost parameter @River-Shi (#77)

**📝 Documentation**

- docs: add HelloGitHub recommendation badge to README @ZhuoZhuoCrayon (#76)

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.1.0...v2.2.0


v2.1.0 - 2025-05-26
-------------------

`简体中文 (v2.1.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v210---2025-05-26>`_ | English

**🚀 New Features**

- feat: add async support for Throttled (issue #36) @ZhuoZhuoCrayon (#73)
- feat: implement "GCRA" Rate Limiter with async support (issue #36) @ZhuoZhuoCrayon (#72)
- feat: implement "Token Bucket" Rate Limiter with async support (issue #36) @ZhuoZhuoCrayon (#71)
- feat: implement "Sliding Window" Rate Limiter with async support (issue #36) @ZhuoZhuoCrayon (#70)
- feat: implement "Leaking Bucket" Rate Limiter with async support (issue #36) @ZhuoZhuoCrayon (#69)
- feat: implement "Fixed Window" Rate Limiter with async support (issue #36) @ZhuoZhuoCrayon (#67)
- feat: add asyncio-based implementation for RedisStore (issue #36) @ZhuoZhuoCrayon (#66)
- feat: add asyncio-based implementation for MemoryStore (issue #36) @ZhuoZhuoCrayon (#65)

**📝 Documentation**

- docs: add asyncio example @ZhuoZhuoCrayon (#74)
- docs: update README_ZH.md with English link @ZhuoZhuoCrayon (#64)

**✨ Improvements**

- refactor: simplify rate limiter and store backend implementations @ZhuoZhuoCrayon (#68)

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.2...v2.1.0


v2.0.2 - 2025-05-03
-------------------

`简体中文 (v2.0.2) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v202---2025-05-03>`_ | English

**📝 Documentation**

- docs: optimize README navigation @ZhuoZhuoCrayon (#61)
- docs: optimize quick start examples for low-configuration servers @ZhuoZhuoCrayon (#60)

**📦 Dependencies**

- build: update package metadata & readme navigation links @ZhuoZhuoCrayon (#62)

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.1...v2.0.2


v2.0.1 - 2025-05-02
-------------------

`简体中文 (v2.0.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v201---2025-05-02>`_ | English

**✨ Improvements**

- perf: optimize rate limiting algorithm performance @ZhuoZhuoCrayon (#55)

**📝 Documentation**

- docs: update readme with pypi package link @ZhuoZhuoCrayon (#57)
- docs: fix typos in README @ZhuoZhuoCrayon (#53)

**📦 Dependencies**

- build: update package metadata @ZhuoZhuoCrayon (#56)

**🧪 Tests**

- test: rewrite timer implementation and add callback support @ZhuoZhuoCrayon (#54)

**🍃 Maintenance**

- ci: update regex pattern for ci/skip-changelog @ZhuoZhuoCrayon (#58)

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.0...v2.0.1


v2.0.0 - 2025-04-22
-------------------

`简体中文 (v2.0.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v200---2025-04-22>`_ | English

**🔥 Breaking Changes**

- build: make store dependencies optional via extras (#45) @ZhuoZhuoCrayon (#50)
    - For more details, please refer to the `Optional Dependencies <https://github.com/ZhuoZhuoCrayon/throttled-py?tab=readme-ov-file#1-optional-dependencies>`_ section.

- fix: remove deprecated "rate_limter" misspelled alias (#38) @ZhuoZhuoCrayon (#51)

**🐛 Bug Fixes**

- fix: remove deprecated "rate_limter" misspelled alias (#38) @ZhuoZhuoCrayon (#51)

**📦 Dependencies**

- build: make store dependencies optional via extras (#45) @ZhuoZhuoCrayon (#50)

**🍃 Maintenance**

- ci: implement automated release drafting workflow @ZhuoZhuoCrayon (#47)

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.1...v2.0.0


v1.1.1 - 2025-04-19
-------------------

`简体中文 (v1.1.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v111---2025-04-19>`_ | English

**What's Changed**

* refactor: replace ``time.time()`` with ``time.monotonic()`` to reduce the impact of system clock updates by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/41
* feat: add ``per_duration`` and ``per_week`` to Quota definition by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/43
* fix: fixed the inaccurate calculation of ``per_day`` time span by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/42

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.0...v1.1.1


v1.1.0 - 2025-04-17
-------------------

`简体中文 (v1.1.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v110---2025-04-17>`_ | English

**What's Changed**

* feat: add retry_after to LimitedError message by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/34
* feat: implement context manager support for Throttled by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/35
* fix: correct the spelling of "rate_limter" to "rate_limiter" (fixed #38) by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/39

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.3...v1.1.0


v1.0.3 - 2025-04-10
-------------------

`简体中文 (v1.0.3) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v103---2025-04-10>`_ | English

**What's Changed**

* feat: add retry_after to RateLimitState by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/28
* feat: add wait-retry mode with timeout configuration by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/29
* fix: gcra double traffic issue from inaccurate MemoryStore expiration by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/30
* test: add benchmark tests and update README by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/26

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.2...v1.0.3


v1.0.2 - 2025-03-29
-------------------

`简体中文 (v1.0.2) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v102---2025-03-29>`_ | English

**What's Changed**

* refactor: standardize ratelimiter key format to "throttled:v1:{RateLimiterType}:{UserKey}" by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/24
* perf: optimize the implementation of "Token Bucket" Rate Limiter based on Redis by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/18
* perf: optimize the implementation of "Fixed Window" Rate Limiter based on Redis by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/19
* docs: resolve doc formatting issues by @JasperLinnn in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15
* test: add Benchmark class for performance testing by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/16
* ci: add GitHub actions workflow for commit linting by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/22

**New Contributors**

* @JasperLinnn made their first contribution in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.1...v1.0.2


v1.0.1 - 2025-03-15
-------------------

`简体中文 (v1.0.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.rst#v101---2025-03-15>`_ | English

**What's Changed**

* feat: Implementing Redis and In-Memory(Thread-Safety) storage backends by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1
* feat: Implement "Sliding Window" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/2
* feat: Implement "Token Bucket" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/3
* feat: Implement "Leaking Bucket" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/8
* feat: Implement "GCRA" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/9

**New Contributors**

* @ZhuoZhuoCrayon made their first contribution in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/commits/v1.0.1
