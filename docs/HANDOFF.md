# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以 GitHub 远端事实为准。
- 架构与维护说明：[README](../README.md)；PHASE 11 触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前处于 **PHASE 11 长期维护循环**，PHASE 13 全库 434 backlog 逐条处置与质量闭环批次已完成。接手基线远端 main 为 `b24fd495cf52f8948ec5742dc3641c0799337a73`（PR #59）；本批完成 434 条 proposed 候选逐条机器最终处置（434/434），闭环修复 14 个 rejected link 状态及重名隐患合并，全库质量扫描器真实错误清零，且针对真实私有母库完成最新 HEAD 本地最终版验收（文档与段落数 171/215,464 保持不变，SQLite 零修改）。最新正式生命周期为 **1,494 active / 429 proposed / 92 superseded**，公开包为 **1,494 hazards / 58 law versions / 1,266 clauses / 1,610 links / public proposed 0**，`releaseHash=bb65650ba5e6730d1f2f4dbd950f1ff2d7bc09c8458422d471824722c3f9c31d`。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。当前 434 backlog 机器处置已闭环记录于 `docs/backlog_434_final_disposition.jsonl`，剩余 429 条 proposed 中包含 401 条现行条款/版本证据缺口、14 条表格/附录/外部标准交叉引用缺口、7 条明确非目标集范围实体、6 条条款适用对象不匹配及 1 条用语强度不匹配。阶段事实仍以 `PROJECT_STATE.md` 为唯一长期记录；本文件只保留接手入口和当前摘要。

