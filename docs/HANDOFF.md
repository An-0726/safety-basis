# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实和下一动作：[PROJECT_STATE](PROJECT_STATE.md)。如文档记录与远端 `main`、当前 commit 或 Actions 事实冲突，以远端实际状态为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 2026 云盘现场隐患补库审计：[DRIVE_HAZARD_INGEST_20260926](DRIVE_HAZARD_INGEST_20260926.md)。

**当前已核线上基线：2026-09-26。** PR #80 完成 2026 云盘现场问题首批定向补库；PR #81 将 CI/正式发布 `asOf` 统一为 `Asia/Shanghai`（中国标准时间）。当前 `main` head=`7231cd24c9a971123c44f972537e528fa855469a`。

当前 `knowledge/manifest.json`：**105 laws / 108 law versions / 2,996 clauses / 2,121 hazards / 1,955 links / 1,202 evidence / 26 successions / 75 requirements**；生命周期 **1,704 active / 320 proposed / 97 superseded**。

当前正式公开包（`asOf=2026-09-26`）：**1,704 hazards / 61 laws / 61 law versions / 1,333 clauses / 1,822 links / public proposed 0**；`releaseHash=c144beeaa60ed4ff4fbb3dc3ec1da92d45103cdd82cab6c29c6e8bcf57d73a90`。

main Validate run `36169948637`、Build/Pages Deploy/Online Verify run `36169948666` 全部成功；线上真实 Chromium 核对 1,704 hazards / 61 laws / 1,333 clauses / 1,822 links 无差异。

本轮新增/转正 4 个高频问题：安全警示标志褪色（既有候选转正）、变配电室防蛇鼠等小动物、安全出口/疏散指示标志灯具损坏、消防控制室专用电话/通信故障。最新南京明生医药安全现状评价报告 110 项检查均为符合，没有新增需限期整改的不符合项。

当前仍处于长期维护模式。继续工作时优先做 **2026 真实现场资料 → 既有 canonical 去重 → 高频真缺口 → 完整直接依据**；不要无目的把所有未关联条款转成隐患。7–9 月 legacy `.xls` 打分表需先与既有 1,929 条目标集做来源差异核对，再决定是否补库。
