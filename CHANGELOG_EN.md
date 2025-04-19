# Version History

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md) | English


## v1.1.1 - 2025-04-19

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md#v111---2025-04-19) | English

### What's Changed
* refactor: replace `time.time()` with `time.monotonic()` to reduce the impact of system clock updates by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/41
* feat: add `per_duration` and `per_week` to Quota definition by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/43
* fix: fixed the inaccurate calculation of `per_day` time span by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/42

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.0...v1.1.1

---


## v1.1.0 - 2025-04-17

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md#v110---2025-04-17) | English

### What's Changed
* feat: add retry_after to LimitedError message by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/34
* feat: implement context manager support for Throttled by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/35
* fix: correct the spelling of "rate_limter" to "rate_limiter" (fixed #38) by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/39

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.3...v1.1.0

---


## v1.0.3 - 2025-04-10

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md#v103---2025-04-10) | English

### What's Changed
* feat: add retry_after to RateLimitState by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/28
* feat: add wait-retry mode with timeout configuration by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/29
* fix: gcra double traffic issue from inaccurate MemoryStore expiration by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/30
* test: add benchmark tests and update README by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/26

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.2...v1.0.3

---


## v1.0.2 - 2025-03-29

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md#v102---2025-03-29) | English

### What's Changed
* refactor: standardize ratelimiter key format to "throttled:v1:{RateLimiterType}:{UserKey}" by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/24
* perf: optimize the implementation of "Token Bucket" Rate Limiter based on Redis by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/18
* perf: optimize the implementation of "Fixed Window" Rate Limiter based on Redis by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/19
* docs: resolve doc formatting issues by @JasperLinnn in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15
* test: add Benchmark class for performance testing by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/16
* ci: add GitHub actions workflow for commit linting by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/22

### New Contributors
* @JasperLinnn made their first contribution in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.1...v1.0.2

---


## v1.0.1 - 2025-03-15

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md#v101---2025-03-15) | English

### What's Changed
* feat: Implementing Redis and In-Memory(Thread-Safety) storage backends by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1
* feat: Implement "Sliding Window" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/2
* feat: Implement "Token Bucket" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/3
* feat: Implement "Leaking Bucket" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/8
* feat: Implement "GCRA" Rate Limiter by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/9

### New Contributors
* @ZhuoZhuoCrayon made their first contribution in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1

**Full Changelog**: https://github.com/ZhuoZhuoCrayon/throttled-py/commits/v1.0.1
