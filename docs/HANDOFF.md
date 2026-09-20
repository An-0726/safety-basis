# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以远端事实为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前分支是 **2026-09-21 工程级审计整改发布候选**。本轮已经修改 `knowledge/`、`source/publication/`、发布门禁和网页路由；Stable ID 和历史记录保持可追溯。审计分支最终 QA 已通过，但在 PR 合并、main CI/Pages 部署和线上复验完成前，不宣称线上版本已更新。

当前 checkout 的 `knowledge/manifest.json`：**104 laws / 107 law versions / 2,993 clauses / 2,053 hazards / 1,923 links / 1,201 evidence / 26 successions / 75 requirements**；生命周期 **1,681 active / 276 proposed / 96 superseded**。

最终 QA 公开包（`asOf=2026-09-21`）：**1,679 hazards / 58 laws / 58 law versions / 1,302 clauses / 1,788 links / public proposed 0**；QA `releaseHash=4f491c8bf655236ca61e8df14a39769fb981937360e69f5f913225f42cc001b8`。GitHub Actions run `35524378609` 的自动门禁、全库 scanner、分类审计、构建验证及 Chromium 严格交互测试全部通过，scanner 为 0 ERROR。

本轮关键处置：修复 manifest/物理库存漂移并建立永久硬门禁；PR #70 的 36 条批量隐患完成 7 条合并、29 条降为 proposed，错误 direct 关联退出发布；长丰批量导入器默认改为 proposed/pending；补录 GB 14784-2013 输送机急停直接依据；收紧配电柜门保护连接适用条件并归并重复实体；修复仓储“五距”直接依据；灭火器维修合格证、燃料 SDS、实验室酒精在证据/现场条件不足时不强行转正。

接手后先核对远端 `main` / PR / Actions。下一动作是合并本候选、等待 main Validate / Build / Pages Deploy 全绿，再对公网 URL 做最终验收并把 PROJECT_STATE / HANDOFF 更新为正式部署状态。
