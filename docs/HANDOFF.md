# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以 GitHub 远端事实为准。
- 架构与维护说明：[README](../README.md)；PHASE 11 触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前处于 **PHASE 11 长期维护循环**，PHASE 14 GB 18597-2023 危废专项收录与转正批次已通过 PR #61 合并；最近业务数据里程碑为 `3fa240a911d18c13ed42c59d0f894d5bc354d4dc`，但接手时仍必须重新核对远端 `main`，不得把文档中的 SHA 当永久 current。PHASE 14 收录强制性国家标准 GB 18597-2023 现行版本卡及 20 条核心规范条款，复核 18 条危废候选，8 条转为 active，其余 10 条继续 proposed。最新正式生命周期为 **1,502 active / 421 proposed / 92 superseded**，公开包为 **1,502 hazards / 59 law versions / 1,276 clauses / 1,621 links / public proposed 0**，`releaseHash=e9ba28076196e90f70fd5737d73a222068d5ad2dad3263340d654adb52650cf2`。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。**证据获取固定采用“本地优先、官方网络补齐”路线：`source/library/` 不是唯一证据源，本地找不到时必须继续查询权威官方网页/PDF；官方来源满足现行版本、精确条款、完整原文和适用性要求后，可直接建立正式 evidence 链，不要求先写 SQLite。** 当前 18 条危废候选机器处置记录于 `docs/phase14-gb18597-disposition.jsonl`，全库 backlog 基础记录见 `docs/backlog_434_final_disposition.jsonl`。阶段事实仍以 `PROJECT_STATE.md` 为唯一长期记录；本文件只保留接手入口和当前摘要。


