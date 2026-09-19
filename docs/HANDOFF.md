# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以 GitHub 远端事实为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前处于 **全量审计修复完成、全项目最终验收通过、正式切换为长期维护模式 (Long-Term Maintenance Mode)**。业务范围已全面收口冻结。

全库状态与关键事实（README / PROJECT_STATE / HANDOFF / manifest / public manifest 五边数字完全一致）：
1. **依据审计工作簿全量纠错**：GB 50058-2014 独立建模纳管、工贸重大隐患原子条款补齐、两组重复法规版本合并去重、3 组重复演进关系去重、南京条例等官方逐字条文全文写回、关联矩阵 1886 项核验映射、隐患描述与措施反转纠正、草稿标记清理与发布门禁阻断清零（0 blocker）。
2. **全库知识源库存（Knowledge Base Total Inventory）**：
   - **103 个法规身份 (laws)**；
   - **106 个法规版本 (law-versions)**；
   - **2,992 条法规条款 (clauses)**；
   - **2,015 个隐患实体 (hazards)**：
     - **1,682 条现行有效 (active)**；
     - **246 条分类保留 (proposed)**；
     - **87 条归并替代 (superseded)**；
     - 隐患生命周期对账平衡：`1,682 + 246 + 87 = 2,015`；
   - **1,886 个关联 (links)**；
   - **1,199 个官方证据卡 (evidence)**；
   - **75 条管理要求 (requirements)**；
   - **26 条替代演进关系 (successions)**。
3. **正式公开站发布指标（Public Release Bundle）**：
   - **1,680 hazards**（全部为 active 状态，public proposed 严格为 0）；
   - **57 laws / 57 law versions**（全部具有现行有效条款支撑）；
   - **1,300 clauses**（全部包含逐字官方原文）；
   - **1,788 links**（全部通过严格 Gate）；
   - **69 个 canonical 来源关系**（11 份获准公开全文 + 58 个官方链接入口）；
   - `releaseHash=31bb6d1aaab330f05bd65c0d207bfb09107d1fab09f1b4ca4e04386ae1f63e60`。
4. **门禁与测试**：全量自动化门禁与测试（`validate_all.py`、`strict_release_audit.py`、`verify_unified_bundle.py`、`validate_publication_integrity.py`、Node 15/15 tests、Python 35/35 tests）全部 PASS，blocker 彻底归零（0）。
5. **母库物理属性与操作事实**：`source/library/fulltext.sqlite3` 物理属性（SHA-256=`4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`、size=106,958,848、mtime(UTC)=`2026-09-17T10:11:19.831234+00:00`、documents=171、FTS=215,464、integrity=ok）与写入前纯净备份完全一致。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。**业务范围已冻结，不主动扩大业务范围或为了“保持活跃”修改业务数据。** 仅当满足 [MAINTENANCE.md](MAINTENANCE.md) 规定的明确维护触发条件时，方可开启针对性的新维护批次。证据获取长效遵循 PR #62 确立的“本地母库优先，官方网络权威来源补齐”规则。阶段事实仍以 `PROJECT_STATE.md` 为唯一长期记录；本文件只保留接手入口和当前摘要。



