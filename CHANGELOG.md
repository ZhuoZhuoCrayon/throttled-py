# Version History

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md) | 简体中文


## v2.1.0 - 2025-05-26

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v210---2025-05-26) | 简体中文

### ✨ 优化

- refactor: 简化限流器与存储后端实现 @ZhuoZhuoCrayon (#68)

### 🚀 New Features

- feat: 新增 Throttled 的异步支持 (issue #36) @ZhuoZhuoCrayon (#73)
- feat: 实现具有异步支持的「GCRA」限流器 (issue #36) @ZhuoZhuoCrayon (#72)
- feat: 实现具有异步支持的「令牌桶」限流器 (issue #36) @ZhuoZhuoCrayon (#71)
- feat: 实现具有异步支持的「滑动窗口」限流器 (issue #36) @ZhuoZhuoCrayon (#70)
- feat: 实现具有异步支持的「漏桶」限流器 (issue #36) @ZhuoZhuoCrayon (#69)
- feat: 实现具有异步支持的「固定窗口」限流器 (issue #36) @ZhuoZhuoCrayon (#67)
- feat: 新增 RedisStore 的异步实现 (issue #36) @ZhuoZhuoCrayon (#66)
- feat: 新增 MemoryStore 的异步实现 (issue #36) @ZhuoZhuoCrayon (#65)

### 📝 文档

- docs: 新增异步示例 @ZhuoZhuoCrayon (#74)
- docs: 更新 README_ZH.md 中的英文链接 @ZhuoZhuoCrayon (#64)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.2...v2.1.0

---


## v2.0.2 - 2025-05-03

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v202---2025-05-03) | 简体中文

### 📝 文档

- docs: 优化 README 导航 @ZhuoZhuoCrayon (#61)
- docs: 优化低配置服务器的快速入门示例 @ZhuoZhuoCrayon (#60)

### 📦 依赖项更新

- build: 更新包元数据 & README 导航链接 @ZhuoZhuoCrayon (#62)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.1...v2.0.2

---


## v2.0.1 - 2025-05-02

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v201---2025-05-02) | 简体中文

### ✨ 优化

- perf: 优化限速算法性能 @ZhuoZhuoCrayon (#55)

### 📝 文档

- docs: 更新 readme pypi 链接 @ZhuoZhuoCrayon (#57)
- docs: 修复 README 中的拼写错误 @ZhuoZhuoCrayon (#53)

### 📦 依赖项更新

- build: 更新包元数据 @ZhuoZhuoCrayon (#56)

### 🧪 测试

- test: 重写计时器实现并添加回调支持 @ZhuoZhuoCrayon (#54)

### 🍃 维护工作

- ci: 更新 ci/skip-changelog 的正则表达式 @ZhuoZhuoCrayon (#58)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.0...v2.0.1

---


## v2.0.0 - 2025-04-22

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v200---2025-04-22) | 简体中文

### 🔥 破坏性变更

- build: 通过 extras 使存储依赖项可选 (#45) @ZhuoZhuoCrayon (#50)
    - 更多详情请参考 [额外依赖](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#1%E9%A2%9D%E5%A4%96%E4%BE%9D%E8%B5%96) 部分。

- fix: 移除已弃用的拼写错误别名 "rate_limter" (#38) @ZhuoZhuoCrayon (#51)

### 🐛 Bug 修复

- fix: 移除已弃用的拼写错误别名 "rate_limter" (#38) @ZhuoZhuoCrayon (#51)

### 📦 依赖项更新

- build: 通过 extras 使存储依赖项变为可选 (#45) @ZhuoZhuoCrayon (#50)

### 🍃 维护工作

- ci: 实现自动化发布草稿工作流 @ZhuoZhuoCrayon (#47)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.1...v2.0.0

---


## v1.1.1 - 2025-04-19

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v111---2025-04-19) | 简体中文

### 更新内容
* refactor: 用 `time.monotonic()` 替换 `time.time()`，以减少系统时钟更新的影响 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/41
* feat: 增加 `per_duration` 和 `per_week` 的 Quota 快捷创建方式 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/43
* fix: 修复 `per_day` 时间跨度计算不准确的问题 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/42

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.0...v1.1.1

---


## v1.1.0 - 2025-04-17

[English Documents Available](https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.md#v110---2025-04-17) | 简体中文

### 更新内容
* feat: 新增「retry_after」到 LimitedError 的异常信息 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/34
* feat: 新增上下文管理器支持 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/35
* fix: 修正「rate_limter」拼写为「rate_limiter」 (fixed #38) by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/39

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.3...v1.1.0

---


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
