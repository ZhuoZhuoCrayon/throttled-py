# Version History

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md) | English


## v1.0.2 - 2025-03-29

[简体中文](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG.md#v102---2025-03-29) | English

### What's Changed
* refactor: standardize ratelimiter key format to "throttled:v1:{RateLimiterType}:{UserKey}" by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/24
* perf: optimize the implementation of "Token Bucket" Rate Limiter based on Redis by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/18
* perf: optimize the implementation of "Fixed Window" Rate Limiter based on Redis by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/19
* docs: resolve doc formatting issues by @JasperLinnn in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15
* test: add Benchmark class for performance testing by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/16
* ci: add github actions workflow for commit linting by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/22

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
