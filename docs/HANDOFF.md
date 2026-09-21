# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以远端事实为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

**2026-09-21 工程级审计整改已正式上线。** PR #74 已合并 `main`（merge commit `d2384ea38e41b40a7cad6dc3b1f3acc5fc8aeee3`），main Validate、Build、GitHub Pages Deploy 和部署后真实 Chromium Online Verify 均已通过；Stable ID 和历史记录保持可追溯。

当前 checkout 的 `knowledge/manifest.json`：**104 laws / 107 law versions / 2,993 clauses / 2,053 hazards / 1,923 links / 1,201 evidence / 26 successions / 75 requirements**；生命周期 **1,680 active / 276 proposed / 97 superseded**。

当前正式公开包（`asOf=2026-09-21`）：**1,680 hazards / 59 laws / 59 law versions / 1,303 clauses / 1,790 links / public proposed 0**；`releaseHash=bf2418ce9d28737813a62fc2b3f7a51b552b4fba4106121452b0183a3323d5bc`。main Validate run `35525815957`、Build/Deploy/Online Verify run `35525815952` 全部通过。

本轮关键处置：修复 manifest/物理库存漂移并建立永久硬门禁；PR #70 的 36 条批量隐患完成 7 条合并、29 条降为 proposed，错误 direct 关联退出发布；长丰批量导入器默认改为 proposed/pending；补录 GB 14784-2013 输送机急停直接依据；收紧配电柜门保护连接适用条件并归并重复实体；修复仓储“五距”直接依据；灭火器维修合格证、燃料 SDS、实验室酒精在证据/现场条件不足时不强行转正。

接手后先核对远端 `main` / Actions 与线上站点；当前项目已转入长期维护。后续新增法规、隐患或网页修改继续遵循 Gate、PR、Pages 部署和线上复验流程。
