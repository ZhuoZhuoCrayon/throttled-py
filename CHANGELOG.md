# Version History

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md) | 简体中文


## v1.0.3 - 2025-04-10

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v103---2025-04-10) | 简体中文

### 更新内容
* feat: 新增「retry_after」到 RateLimitState by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/28
* feat: 新增「等待-重试」模式，并支持超时配置 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/29
* fix: 修复因 MemoryStore 过期时间精度不准确导致的「GCRA」限流器双倍流量问题 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/30
* test: 新增基准测试用例并在文档中增加 Benchmarks 说明 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/26

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.2...v1.0.3

---


## v1.0.2 - 2025-03-29

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v102---2025-03-29) | 简体中文

### 更新内容
* refactor: 标准化限流器 Key 格式为 "throttled:v1:{RateLimiterType}:{UserKey}" by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/24
* perf: 优化「令牌桶」Redis 限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/18
* perf: 优化「固定窗口」Redis 限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/19
* docs: 修复文档格式问题 by @JasperLinnn in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15
* test: 新增性能测试 Benchmark 类 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/16
* ci: 添加 GitHub Actions 工作流用于提交校验 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/22

### 新贡献者
* @JasperLinnn 在 https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15 完成首次贡献

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.1...v1.0.2

---


## v1.0.1 - 2025-03-15

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v101---2025-03-15) | 简体中文

### 更新内容
* feat: 支持 Redis、内存（线程安全）作为存储后端 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1
* feat: 实现「滑动窗口」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/2
* feat: 实现「令牌桶」｜限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/3
* feat: 实现「漏桶」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/8
* feat: 实现「GCRA」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/9

### 新贡献者
* @ZhuoZhuoCrayon 在 https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1 完成首次贡献

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/commits/v1.0.1
