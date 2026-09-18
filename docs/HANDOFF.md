# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以 GitHub 远端事实为准。
- 架构与维护说明：[README](../README.md)；PHASE 11 触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前处于 **PHASE 11 长期维护循环**，PHASE 12 exact-locator 批次已完成并合入 `main`。当前远端主线为 `f6cf9ed34a7a42ba70f65336dc91aa4c6ce8a823`（PR #58），最新 Validate / Build / Pages deploy 均 success；正式基线为 **1,495 active / 434 proposed / 86 superseded**，公开包为 **1,495 hazards / 58 law versions / 1,267 clauses / 1,611 links / public proposed 0**。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。当前下一业务动作是对剩余 **434 条 proposed** 按证据状态继续分批核验：优先现行精确条款 + 原文证据 + 明确适用对象，交叉引用/表格/条件性或重复对象未闭环的一律继续 proposed。阶段事实仍以 `PROJECT_STATE.md` 为唯一长期记录；本文件只保留接手入口和当前摘要。
