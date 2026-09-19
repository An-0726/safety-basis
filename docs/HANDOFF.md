# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以 GitHub 远端事实为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前处于 **全项目最终验收通过、正式切换为长期维护模式 (Long-Term Maintenance Mode)**。业务范围已全面收口冻结。
接手基线远端 main 为 `24f0bc68de9a59de89f2a19a7f0e1276fb019f19` 及本轮 manifest 重建收口提交。

全库状态与关键事实（README / PROJECT_STATE / HANDOFF / manifest / public manifest 五边数字完全一致）：
1. **全库 426 条 proposed 候选逐条核销闭环**：PR #64 8 个批次完成全量审查，242 条转正 active，184 条依规范分类保留（含 149 条 upcoming、9 条 out of scope、8 条 applicability gap、7 条 evidence gap、5 条 cross-ref gap、5 条 rewrite hazard、1 条 merge/supersede），主审计对账平衡率 100%（`426 = 242 + 184`）。
2. **全库知识源库存（Knowledge Base Total Inventory）**：
   - **104 个法规身份 (laws)**；
   - **107 个法规版本 (law-versions)**；
   - **3,007 条法规条款 (clauses)**；
   - **2,015 个隐患实体 (hazards)**：
     - **1,744 条现行有效 (active)**；
     - **184 条分类保留 (proposed)**；
     - **87 条归并替代 (superseded)**；
     - 隐患生命周期对账平衡：`1,744 + 184 + 87 = 2,015`；
   - **1,886 个关联 (links)**；
   - **1,197 个官方证据卡 (evidence)**；
   - **75 条管理要求 (requirements)**；
   - **29 条替代演进关系 (successions)**。
3. **正式公开站发布指标（Public Release Bundle）**：
   - **1,744 hazards**（全部为 active 状态，public proposed 严格为 0）；
   - **60 laws / 60 law versions**（全部具有现行有效条款支撑）；
   - **1,354 clauses**（全部包含逐字官方原文）；
   - **1,863 links**（全部通过严格 Gate）；
   - **69 个 canonical 来源关系**（11 份获准公开全文 + 58 个官方链接入口）；
   - `releaseHash=5df466dec1a67757edd0a6a57f44a9cee0d2d84c40406f5efae69d1c31112f1a`。在线 Pages 站点（`https://an-0726.github.io/safety-basis/`）9 个 hazard shards 与 7 个 clause shards 100% 校验通过。
4. **历史悬空证据引用彻底清除**：补齐 5 张缺失证据卡（`E_PRIV_GBT13869_2017`、`E_STD_GB12801_2008`、`E_GBT12801_2008`、`EH_GBT12801_5_7_1_C`、`E_PHASE12_EXACT_LOCATOR`）并规范化 3 条 reviews，`Reviews with dangling evidenceRefs` 清零（0）。
5. **母库物理属性与操作事实**：`source/library/fulltext.sqlite3` 物理属性（SHA-256=`4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`、size=106,958,848、mtime(UTC)=`2026-09-17T10:11:19.831234+00:00`、documents=171、FTS=215,464、integrity=ok）与写入前纯净备份完全一致。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。**业务范围已冻结，不主动扩大业务范围或为了“保持活跃”修改业务数据。** 仅当满足 [MAINTENANCE.md](MAINTENANCE.md) 规定的明确维护触发条件时，方可开启针对性的新维护批次。证据获取长效遵循 PR #62 确立的“本地母库优先，官方网络权威来源补齐”规则。阶段事实仍以 `PROJECT_STATE.md` 为唯一长期记录；本文件只保留接手入口和当前摘要。



