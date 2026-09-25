# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。如文档记录与远端 `main`、当前 commit 或 Actions 事实冲突，以远端实际状态为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

**当前已核线上基线：2026-09-23。** PR #79 已合并 `main`（merge commit `5e914ae82e9ead0eac7f0e64383556c16fdc556c`），完成 GB 46768-2025 有限空间与 GB 15607-2023 粉末静电喷涂首批法规反查补库。

当前 `knowledge/manifest.json`：**104 laws / 107 law versions / 2,993 clauses / 2,118 hazards / 1,951 links / 1,201 evidence / 26 successions / 75 requirements**；生命周期 **1,700 active / 321 proposed / 97 superseded**。

当前正式公开包（`asOf=2026-09-23`）：**1,700 hazards / 60 laws / 60 law versions / 1,330 clauses / 1,818 links / public proposed 0**；`releaseHash=e90426307506851ca35c2980bcc81ba6c1c7b35df8adf3c64cde64cd8d5e7276`。

main Validate run `35852503379`、Build/Pages Deploy/Online Verify run `35852503526` 全部成功；线上 Chromium 验证的 hazards / laws / clauses / links 数量与构建期预期一致。

历史上 2026-09-21 已完成商贸集团检查文件夹 16 份 Word、134 条来源事项的 134/134 去向覆盖；该批新增缺口优先保持 proposed，只有直接依据完整、适用性明确并通过 Gate 的记录才转为 active。

当前项目处于长期维护模式。后续新增报告/检查记录中的现场问题，先与既有 canonical 隐患去重，再按“已有正式隐患复用 → 可核直接依据则转正/补关联 → 证据或适用性不足则 proposed”的顺序处理；不得因为来源文件写了法规条款就直接视为正式证据。
