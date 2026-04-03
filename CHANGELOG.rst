Version History
=================

v3.2.0 - 2026-04-03
---------------------

`English Documents Available (v3.2.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v320---2026-04-03>`_ | 简体中文

**🚀 功能**

- feat(hook): 新增支持 OpenTelemetry 的异步 Hook 系统 (#37) @s3ich4n (#133)
- feat: 新增支持 OpenTelemetry 的 Hook 系统 (#37) @s3ich4n (#125)

**📦 依赖项更新**

- build(deps): 将 cryptography 从 46.0.5 升级到 46.0.6 @dependabot[bot] (#139)
- build(deps): 将 pygments 从 2.19.2 升级到 2.20.0 @dependabot[bot] (#138)
- build(deps): 将 requests 从 2.32.5 升级到 2.33.0 @dependabot[bot] (#137)
- build(deps): 将 urllib3 从 2.5.0 升级到 2.6.3 @dependabot[bot] (#129)
- build(deps): 将 cryptography 从 46.0.3 升级到 46.0.5 @dependabot[bot] (#132)

**🍃 维护工作**

- ci: 为 release-drafter 自动标签器支持带 scope 的 conventional commits @ZhuoZhuoCrayon (#131)
- docs: 添加贡献指南与 PR 模板 (#127) @s3ich4n (#130)
- ci: 在 Fork PR 中跳过 coverage 评论 @ZhuoZhuoCrayon (#128)
- ci: 更新 GitHub token 引用并提升代码质量 @ZhuoZhuoCrayon (#126)
- ci: 添加预发布自动化技能 @ZhuoZhuoCrayon (#124)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v3.1.1...v3.2.0


v3.1.1 - 2026-01-16
---------------------

`English Documents Available (v3.1.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v311---2026-01-16>`_ | 简体中文

**🐛 Bug 修复**

- fix: 添加 @wraps 装饰器到内部函数以更好地保留元数据 @MaksimZayats (#120)

**🍃 维护工作**

- ci: 添加 AI 驱动的自动化预发布准备 @ZhuoZhuoCrayon (#122)
- ci: 移除 commitlint action 中的 token 配置 @ZhuoZhuoCrayon (#121)
- ci: 使用 prek 作为 pre-commit 的替代 @ZhuoZhuoCrayon (#119)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v3.1.0...v3.1.1


v3.1.0 - 2025-12-30
---------------------

`English Documents Available (v3.1.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v310---2025-12-30>`_ | 简体中文

**🚀 功能**

- feat: 添加对 Redis 集群模式的支持 (resolved #92) @ZhuoZhuoCrayon (#117)

**✨ 优化**

- perf: 使用标准 Redis URL 简化 RedisStore 配置 @ZhuoZhuoCrayon (#115)

**🍃 维护工作**

- docs: 优化文档代码框样式 @ZhuoZhuoCrayon (#116)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v3.0.1...v3.1.0


v3.0.1 - 2025-11-27
---------------------

`English Documents Available (v3.0.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v301---2025-11-27>`_ | 简体中文

**📦 依赖项更新**

- build: 添加 py.typed 文件以支持类型提示 @ZhuoZhuoCrayon (#113) (resolved #112)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v3.0.0...v3.0.1


v3.0.0 - 2025-11-18
---------------------

`English Documents Available (v3.0.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v300---2025-11-18>`_ | 简体中文

**🔥 破坏性变更**

- build: 从 Poetry 迁移到 Hatch 和 uv @ZhuoZhuoCrayon (#97)
    - 结束对 Python 3.8 和 3.9 的支持，最低要求的 Python 版本现在是 3.10。

**🚀 功能**

- feat: 添加对 Python 3.13 和 3.14 的支持 @ZhuoZhuoCrayon (#98)

**✨ 优化**

- perf: 在桶算法中用 Redis 服务器时间替换服务时间戳 @ZhuoZhuoCrayon (#108)
- perf: 优化高并发场景下的桶计数准确性 @ZhuoZhuoCrayon (#101)

**📦 依赖项更新**

- build: 放宽对 redis-py 的依赖版本限制 @ZhuoZhuoCrayon (#97) (resolved #96)

**🍃 维护工作**

- ci: 调整发布草稿的类别和标签 @ZhuoZhuoCrayon (#106)
- ci: 通过添加并行测试执行支持来加快 pytest 执行速度 @ZhuoZhuoCrayon (#103)
- docs: 更新 Python 徽章以使用 Shields.io 格式 @ZhuoZhuoCrayon (#107)
- docs: 加强 Copilot 审查确认规则 @ZhuoZhuoCrayon (#105)
- docs: 添加 PR 指南确认要求 @ZhuoZhuoCrayon (#102)
- docs: 添加 GitHub Copilot 代码审查指南 @ZhuoZhuoCrayon (#100)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.2.3...v3.0.0


v2.2.3 - 2025-08-30
--------------------

`English Documents Available (v2.2.3) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v223---2025-08-30>`_ | 简体中文

**🐛 Bug 修复**

- fix: 移除注册阶段冗余的提示性日志 @ZhuoZhuoCrayon (fixed #93) @ZhuoZhuoCrayon (#94)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.2.2...v2.2.3


v2.2.2 - 2025-07-25
--------------------

`English Documents Available (v2.2.2) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v222---2025-07-25>`_ | 简体中文

**🐛 Bug 修复**

- fix: 修复「滑动窗口」算法的 retry_after 计算不准确的问题 @ZhuoZhuoCrayon (#89)

**📝 文档**

- docs: 添加 API 参考文档 @ZhuoZhuoCrayon (#90)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.2.1...v2.2.2


v2.2.1 - 2025-06-28
--------------------

`English Documents Available (v2.2.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v221---2025-06-28>`_ | 简体中文

**✨ 优化**

- perf: 在 Throttled 中添加对 cost=0 的支持 @ZhuoZhuoCrayon (#85)

**🐛 Bug 修复**

- fix: 修复「令牌桶」和「漏桶」算法 ``retry_after`` 计算不准确的问题 @ZhuoZhuoCrayon (#87)

**📝 文档**

- docs: 添加 throttled-py 使用文档，欢迎访问 <https://throttled-py.readthedocs.io/en/latest/> @ZhuoZhuoCrayon (#84)

**🍃 维护工作**

- ci: 更新 release drafter 配置中的 changelog 链接格式 @ZhuoZhuoCrayon (#86)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.2.0...v2.2.1


v2.2.0 - 2025-05-31
--------------------

`English Documents Available(v2.2.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v220---2025-05-31>`_ | 简体中文

**🚀 功能**

- feat: 增强 Throttled 装饰器，支持 cost 参数 @River-Shi (#77)

**📝 文档**

- docs: 在 README 中添加 HelloGitHub 推荐徽章 @ZhuoZhuoCrayon (#76)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.1.0...v2.2.0


v2.1.0 - 2025-05-26
--------------------

`English Documents Available(v2.1.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v210---2025-05-26>`_ | 简体中文

**✨ 优化**

- refactor: 简化限流器与存储后端实现 @ZhuoZhuoCrayon (#68)

**🚀 功能**

- feat: 新增 Throttled 的异步支持 (issue #36) @ZhuoZhuoCrayon (#73)
- feat: 实现具有异步支持的「GCRA」限流器 (issue #36) @ZhuoZhuoCrayon (#72)
- feat: 实现具有异步支持的「令牌桶」限流器 (issue #36) @ZhuoZhuoCrayon (#71)
- feat: 实现具有异步支持的「滑动窗口」限流器 (issue #36) @ZhuoZhuoCrayon (#70)
- feat: 实现具有异步支持的「漏桶」限流器 (issue #36) @ZhuoZhuoCrayon (#69)
- feat: 实现具有异步支持的「固定窗口」限流器 (issue #36) @ZhuoZhuoCrayon (#67)
- feat: 新增 RedisStore 的异步实现 (issue #36) @ZhuoZhuoCrayon (#66)
- feat: 新增 MemoryStore 的异步实现 (issue #36) @ZhuoZhuoCrayon (#65)

**📝 文档**

- docs: 新增异步示例 @ZhuoZhuoCrayon (#74)
- docs: 更新 README_ZH.md 中的英文链接 @ZhuoZhuoCrayon (#64)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.2...v2.1.0


v2.0.2 - 2025-05-03
--------------------

`English Documents Available(v2.0.2) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v202---2025-05-03>`_ | 简体中文

**📝 文档**

- docs: 优化 README 导航 @ZhuoZhuoCrayon (#61)
- docs: 优化低配置服务器的快速入门示例 @ZhuoZhuoCrayon (#60)

**📦 依赖项更新**

- build: 更新包元数据 & README 导航链接 @ZhuoZhuoCrayon (#62)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.1...v2.0.2


v2.0.1 - 2025-05-02
--------------------

`English Documents Available(v2.0.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v201---2025-05-02>`_ | 简体中文

**✨ 优化**

- perf: 优化限速算法性能 @ZhuoZhuoCrayon (#55)

**📝 文档**

- docs: 更新 readme pypi 链接 @ZhuoZhuoCrayon (#57)
- docs: 修复 README 中的拼写错误 @ZhuoZhuoCrayon (#53)

**📦 依赖项更新**

- build: 更新包元数据 @ZhuoZhuoCrayon (#56)

**🧪 测试**

- test: 重写计时器实现并添加回调支持 @ZhuoZhuoCrayon (#54)

**🍃 维护工作**

- ci: 更新 ci/skip-changelog 的正则表达式 @ZhuoZhuoCrayon (#58)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v2.0.0...v2.0.1


v2.0.0 - 2025-04-22
--------------------

`English Documents Available(v2.0.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v200---2025-04-22>`_ | 简体中文

**🔥 破坏性变更**

- build: 通过 extras 使存储依赖项可选 (#45) @ZhuoZhuoCrayon (#50)
    * 更多详情请参考 `额外依赖 <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/README_ZH.md#1%E9%A2%9D%E5%A4%96%E4%BE%9D%E8%B5%96>`_ 部分。

- fix: 移除已弃用的拼写错误别名 "rate_limter" (#38) @ZhuoZhuoCrayon (#51)

**🐛 Bug 修复**

- fix: 移除已弃用的拼写错误别名 "rate_limter" (#38) @ZhuoZhuoCrayon (#51)

**📦 依赖项更新**

- build: 通过 extras 使存储依赖项变为可选 (#45) @ZhuoZhuoCrayon (#50)

**🍃 维护工作**

- ci: 实现自动化发布草稿工作流 @ZhuoZhuoCrayon (#47)

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.1...v2.0.0


v1.1.1 - 2025-04-19
--------------------

`English Documents Available(v1.1.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v111---2025-04-19>`_ | 简体中文

**更新内容**

* refactor: 用 ``time.monotonic()`` 替换 ``time.time()``，以减少系统时钟更新的影响 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/41
* feat: 增加 ``per_duration`` 和 ``per_week`` 的 Quota 快捷创建方式 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/43
* fix: 修复 ``per_day`` 时间跨度计算不准确的问题 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/42

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.1.0...v1.1.1


v1.1.0 - 2025-04-17
--------------------

`English Documents Available(v1.1.0) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v110---2025-04-17>`_ | 简体中文

**更新内容**

* feat: 新增「retry_after」到 LimitedError 的异常信息 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/34
* feat: 新增上下文管理器支持 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/35
* fix: 修正「rate_limter」拼写为「rate_limiter」 (fixed #38) by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/39

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.3...v1.1.0


v1.0.3 - 2025-04-10
--------------------

`English Documents Available(v1.0.3) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v103---2025-04-10>`_ | 简体中文

**更新内容**

* feat: 新增「retry_after」到 RateLimitState by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/28
* feat: 新增「等待-重试」模式，并支持超时配置 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/29
* fix: 修复因 MemoryStore 过期时间精度不准确导致的「GCRA」限流器双倍流量问题 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/30
* test: 新增基准测试用例并在文档中增加 Benchmarks 说明 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/26

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.2...v1.0.3


v1.0.2 - 2025-03-29
--------------------

`English Documents Available(v1.0.2) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v102---2025-03-29>`_ | 简体中文

**更新内容**

* refactor: 标准化限流器 Key 格式为 "throttled:v1:{RateLimiterType}:{UserKey}" by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/24
* perf: 优化「令牌桶」Redis 限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/18
* perf: 优化「固定窗口」Redis 限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/19
* docs: 修复文档格式问题 by @JasperLinnn in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15
* test: 新增性能测试 Benchmark 类 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/16
* ci: 添加 GitHub Actions 工作流用于提交校验 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/22

**新贡献者**

* @JasperLinnn 在 https://github.com/ZhuoZhuoCrayon/throttled-py/pull/15 完成首次贡献

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/compare/v1.0.1...v1.0.2


v1.0.1 - 2025-03-15
--------------------

`English Documents Available(v1.0.1) <https://github.com/ZhuoZhuoCrayon/throttled-py/blob/main/CHANGELOG_EN.rst#v101---2025-03-15>`_ | 简体中文

**更新内容**

* feat: 支持 Redis、内存（线程安全）作为存储后端 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1
* feat: 实现「滑动窗口」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/2
* feat: 实现「令牌桶」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/3
* feat: 实现「漏桶」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/8
* feat: 实现「GCRA」限流器 by @ZhuoZhuoCrayon in https://github.com/ZhuoZhuoCrayon/throttled-py/pull/9

**新贡献者**

* @ZhuoZhuoCrayon 在 https://github.com/ZhuoZhuoCrayon/throttled-py/pull/1 完成首次贡献

**完整更新日志**: https://github.com/ZhuoZhuoCrayon/throttled-py/commits/v1.0.1
