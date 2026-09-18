# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以 GitHub 远端事实为准。
- 架构与维护说明：[README](../README.md)；PHASE 11 触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前处于 **PHASE 11 长期维护循环中的 PR #60 与 PR #61 定点纠错专项**。接手基线远端 main 为 `70981323246c72161a38ada5de782660bbc3a56a`（PR #63），当前工作分支为 `governance/official-web-evidence-policy-20260919`。

本专项不开展新的 proposed→active 或新法规批次，全面完成定点纠错与合规性闭环：
1. **母库操作事实客观记录**：客观记录本轮曾对 `source/library/fulltext.sqlite3` 执行过写入后从备份完全恢复，不再表述为“全过程只读零修改”；当前物理属性（SHA-256=`4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`、size=106,958,848、mtime(UTC)=`2026-09-17T10:11:19.831234+00:00`、documents=171、FTS=215,464、integrity=ok）与写入前纯净备份完全一致。
2. **PR #60 blockers 彻底清零**：危险化学品安全法第五条纠正为全国人大常委会正式法律原文（主席令第六十四号）；彻底清理指向已合并实体的残留链接；撤销对 GB 12158 5 条 proposed 候选的不当标题合并（恢复为独立 proposed 候选，proposed 从 421 增至 426，superseded 从 92 降至 87）；依据标准原件 PDF 还原 9 条 active clause 的科学计数法指数及排版（Unicode 上标），文本损坏警告清零。
3. **PR #61 8 条转正危废隐患逐条严格缩窄重构**：逐条纠除残留的旧版附录A表述、非官方“专用设施”、越权“防火/防雷/消防/通讯”及宽泛选址，严格补齐 6.2.2 触发条件，理清 6.1.1 堆存与 8.3.5 贮存点清运适用边界，重算 reviews 与 contextHashes。
4. **GB 18597 法规版本模型纠正**：删除多余的 `LV_STD_GB18597_2023`，条款统一切换归并至知识库既有规范版本卡 `L023`（挂靠 `LF_L023`），修正 publication 题录条目。

最新正式生命周期为 **1,502 active / 426 proposed / 87 superseded（共 2,015）**，公开包为 **1,502 hazards / 58 law versions / 1,276 clauses / 1,621 links / public proposed 0**，`releaseHash=491d2e5236b2f0b35deb8cc52e029e8731d6cbd46b3d49d8a14d0fd68af61181`。全量 Gate、单元测试、本地发布包及扫描器校验全绿。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。**证据获取固定采用“本地优先、官方网络补齐”路线：`source/library/` 不是唯一证据源，本地找不到时必须继续查询权威官方网页/PDF；官方来源满足现行版本、精确条款、完整原文和适用性要求后，可直接建立正式 evidence 链，不要求先写 SQLite。** 当前 18 条危废候选机器处置记录于 `docs/phase14-gb18597-disposition.jsonl`，全库 backlog 基础记录见 `docs/backlog_434_final_disposition.jsonl`。阶段事实仍以 `PROJECT_STATE.md` 为唯一长期记录；本文件只保留接手入口和当前摘要。


