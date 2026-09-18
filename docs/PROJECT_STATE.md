# 项目阶段状态与恢复计划

本文件保留截至 2026-09-14 的业务核验记录，并补记 2026-09-16 至 2026-09-18 的 PHASE 5 Git 交付闭环、PHASE 6 候选证据回绑、PHASE 7 publication 来源归整、PHASE 8 前端/私有版一致性验收、PHASE 9 Release Candidate 全量验证、PHASE 10 正式发布及 PHASE 11 维护批次。历史统计数字仍按对应阶段记录；不得将历史阶段数字冒充当前发布结果。

**PHASE 10 DONE；PHASE 11 长期维护循环已启动。** 2026-09-17 已完成远端治理、publication 长期门禁、GB 46768-2025 收录、搜索修复及首批电气隐患转正；2026-09-18 已对最新 `origin/main` 与真实私有母库重新完成本地最终版验收，当前回到等待下一维护触发条件的状态。

## 1. ULTIMATE GOAL — 最终目标

形成一套可长期维护、可审计、可持续部署的安全隐患法规依据网站：

- 私有法规证据库分层清楚：原件、历史版本、来源副本、OCR/文本派生物、全文检索数据库各司其职；
- `knowledge/` 是唯一正式结构化法规/版本/条款/隐患知识源；
- 同一法规同一真实版本只有一个 canonical identity，多来源只作为来源；
- 正式引用链满足：`隐患 → 法规身份 → 适用版本 → 具体条/款/项 → 逐字原文 → 官方/原始证据 → 适用性审核`；
- `proposed` 候选不得进入正式公共站；
- 本地私有版可从仓库 + `source/library/` 重建；
- `main` Validate / Build / Pages Deploy 全绿；
- 线上完成搜索、法规详情、来源链、候选隔离、历史/upcoming、桌面/移动端抽检；
- 任意新窗口不依赖旧聊天即可继续。

### Definition of Done

以下为整个项目的最终验收目标，不作为局部任务的完成条件：

1. 私有母库实体、重复、历史版本、派生物关系已解释；
2. 工作 SQLite 在实际本机运行时完整性正常，任何修复有备份和变更记录；
3. `knowledge/` 不存在未经解释的同法规同真实版本重复；
4. 1,929 目标隐患均有明确状态；
5. 正式记录全部通过 Gate；
6. `proposed` 不进入公开正式包；
7. 本地私有版可重建；
8. GitHub Actions 全绿；
9. GitHub Pages deploy success；
10. 线上抽检通过；
11. `docs/PROJECT_STATE.md` / README / HANDOFF 与最终状态一致。

---

## 2. 当前正式基线

**LAST VERIFIED：2026-09-18（PHASE 11 最新 `origin/main` + 真实私有母库本地最终版验收）。**

PHASE 10 正式发布 PR #40 已合并，发布合并提交为 `3c486cba5142a85ebaef366f04dbc7d4e53a91ba`；PR #41 完成 PHASE 10 状态收尾。PHASE 11 首轮维护随后完成：PR #42 收口等待态文档与远端审计；PR #43 将 publication canonical / catalog / 物理全文 / search 派生物一致性固化为长期硬门禁；PR #45 为该门禁补齐合成失败回归测试和 schema/asOf 契约。PR #45 合并提交为 `9e8de313e2321a9b81b8e812155434d7735e463b`，其后 `main` Validate run `35180759610` success，Build/Pages run `35180759551` 的 build 与 deploy 均 success。部署地址仍为 `https://an-0726.github.io/safety-basis/`。

PHASE 10 的首次正式发布基线继续作为历史发布证据；其后 PHASE 11 已发生正式业务数据变化。最新主线为 `125a7afd76d9e1152d9d7f2f9ff70f9cde9e818d`（PR #54），对应 Validate run `35234313626`、Build/Pages run `35234313621` 均 success，并已使用真实私有母库完成本地最终版重建与只读不变量复核。

公开发布架构已收口：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物，不提交 Git；
- 正式站只发布 Gate 通过的已核验隐患；
- `proposed` 不进入公网；
- `upcoming` 尚未实施版本不能支撑当前正式隐患。

### `main` 历史首次正式发布基线（PHASE 10）

- 1,429 条正式隐患；
- 57 个正式引用法规版本；
- 1,205 条正式条款；
- 1,544 个正式关联；
- 499 条 `proposed` 候选仅留 `knowledge/`，公网候选 0。
- PR #40 首次正式部署验收基线：`releaseHash=552cca4f3e12877c7af1f56cd323220fe6af5631e4b334ffddb04881bbc83a07`，`dataVersion=2026.09.16.3c486cba5142`。后续纯文档收尾提交可能触发等价重部署，不改变 governed knowledge/publication 业务数据。

### 当前 knowledge 状态

PHASE 6 从 519 条 `proposed` 基线候选出发，逐条生成最终处置；其中 20 条转为 `active`，499 条继续保持 `proposed`。PHASE 11 随后新增 1 条正式电气隐患并将 12 条电气候选转正。因此当前 `main` lifecycle 为：**1,442 active、487 proposed、86 superseded，共 2,015**。

当前 manifest 库存为：**103 个法规身份、106 个法规版本、2,920 条条款、2,015 个隐患实体、1,581 个关联、1,165 个 evidence、28 条 succession、75 条 requirements**。

新版 Excel 目标集仍为：**1,929 个唯一隐患 ID（621 修订、1,308 保留）**。它不是正式发布数量。

### 最近 Git 里程碑

- PR #29：正式/候选发布边界与 current 现场生成收口；
- PR #30：建立 `AGENTS.md` 作为仓库长期接手入口；
- PR #31：扩展为完整 MASTER ROADMAP；
- PR #32：完成 PHASE 1 私有母库审计，加入私有母库修复方案、安全维护工具和测试；
- PR #34：新增 `AGENT_EXECUTION_PROTOCOL.md`，固化“总控判断、本地 Luna 只执行本机操作”的协作边界；
- PR #36：完成 PHASE 3 document mapping 收口和 PHASE 4 六个 canonical gaps；CI Validate/Build 成功并已合并 main；
- PR #38：完成 PHASE 5 隐患目标集对账并已合并 main；
- PHASE 6 工作分支：完成 519 条候选最终处置、20 条正式回绑、499 条证据不足保留 proposed；
- PHASE 7 工作分支：publication 题录已 canonical 化为 106 个 law-version 行，全文目录收口为 69 个 canonical 来源关系，审计与验证全部通过；
- PHASE 8 工作分支：公开前端、canonical 跳转和本地私有全文展示边界已验收；公开/私有审计均 PASS，最终 workflow run `35120861560` success；
- PHASE 9 RC 工作分支：公共 RC 全量验证 workflow run `35122196162` success；同一 RC 源码快照结合真实私有 SQLite 完成本地最终版构建，输入库内容哈希不变；
- PHASE 10：PR #40 已合并 `main`（发布合并提交 `3c486cba5142a85ebaef366f04dbc7d4e53a91ba`）；PR checks、main Validate、main Build、Pages Deploy 全绿；已部署 artifact 与公网 HTTP 验收均 PASS。
- PR #41：完成 PHASE 10 状态收尾和一次性 workflow/trigger 清理，`main` 收口到长期维护入口。
- PR #42：完成 PHASE 11 首轮等待态远端审计，刷新 README / MAINTENANCE / HANDOFF 并固化维护触发条件。
- PR #43：新增 `tools/v4/validate_publication_integrity.py`，把 PHASE 7 一次性 publication canonical / 全文 / search 一致性审计升级为 Validate 与 Pages Build 都必须执行的长期硬门禁；合并后业务 releaseHash 仍为 `552cca4f3e12877c7af1f56cd323220fe6af5631e4b334ffddb04881bbc83a07`。
- PR #45：为 publication 长期门禁增加正常/失败合成回归测试和 catalog/search/text/gram schema + asOf 契约；合并后 main Validate `35180759610`、Build/Pages `35180759551` 全绿。
- PR #46：同步 Phase 11 当前状态文档，保持 long-lived 架构与维护文档与实际治理状态一致。
- PR #47：记录 current-main 本地验收状态（`docs/PHASE11_LOCAL_ACCEPTANCE_20260917.md` 及状态文档同步）；合并提交 `e3d2e2ac689b26c5dc4058e66feff095039b1358`，main Validate run `35199100753`、Build/Pages run `35199100714` 均 success。
- PR #48：为 `main` 配置并激活 GitHub Repository Ruleset（ID `23589482`），确立技术保护强制，并修复 Windows 本地 SQLite 文件句柄未关闭问题；PR CI 与 main CI/Pages 全绿。
- PR #49：记录历史远端分支清理闭环并关闭 Issue #44。
- PR #50：收录强制性国家标准 GB 46768-2025 及 63 条核心规范条款。
- PR #51：修复连续中文复合检索切词与假阳性问题。
- PR #52：补录配电箱（柜）前通道或维护空间被遮挡、占用的高频电气隐患。
- PR #53：将 12 条证据链完整的常见电气候选转为正式隐患。
- PR #54：按实施日期门禁校正 GB/T 13869-2017/2026 的 current/upcoming 版本治理；最新主线 CI 与 Pages 均 success。

---

## 4. 私有母库当前已核事实

本地工作仓库：`D:\ESH\ESH_Codex\work\safety-basis\`

私有法规母库：`D:\ESH\ESH_Codex\work\safety-basis\source\library\`

Google Drive for desktop 已同步项目。Drive 关键词搜索可能漏掉 `.sqlite3` 二进制文件；应直接读取已知 `source/library` 文件夹，不可因搜索 0 条判断不存在。

### PHASE 1 最终只读审计

- SQLite 文件大小：106,958,848 bytes；`documents=170`；`fulltext_fts=215,326`；唯一文件 SHA-256=166；
- 4 组同一 SHA 双登记，共 8 行；`sum(paragraph_count)=count(fulltext_fts)=215,326`；逐 document FTS 数量一致；
- 同标题双记录 20 组，其中 2 组是真实不同版本，其余为同真实版本旧身份/再导入/多载体；
- 明确真实不同版本：`AQ 4228-2012 / AQ 4228-2025`、`GB/T 13869-2017 / GB/T 13869-2026`；
- current `archive/` 有 136 个 SHA：129 个被当前 `archive_ref` 直接引用，另 7 个为历史纯文本派生物；
- 38 行旧 `evidence/...` 引用不可按标题猜目标；
- inventory：144 原文件 / 138 唯一 SHA / 6 完全重复；inventory-only 不可批量自动导入；
- `pending-originals` 中 TSG 08-2026、TSG 92-2026 待 OCR 载体须先核版本/来源，不可直接再次导入；
- `document_id` 混有 `LF_*`、`LV_*`、旧 `Lxxx`、标准号，不能直接当 canonical law-version 主键。

详细规则：`docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`。

### PHASE 3 第一批：FTS5 修复 — 本机 PASS，云盘内容不变量复核 PASS

本机一致性备份：`source\library\backups\fulltext.sqlite3.bak-20260914-155510+0800`。

修复后：documents=170；ftsRows=215,326；paragraphCountSum=215,326；FK errors=0；逐 document mismatch=0；`ftsContentSha256=1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd` 未变；数据库文件 SHA-256=`7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`；本机 `integrity=["ok"]`。

搜索抽检：`洗眼器=15`、`危险化学品=13,864`、`GB 55036=707`。总控从 Drive 下载同字节文件独立复核，行数、全文摘要、FK、搜索结果全部一致。

兼容性备注：总控 Linux/Python SQLite 3.46.1 对同一字节文件的 `PRAGMA integrity_check` 仍报告 FTS5 inverted-index 错误，而项目实际本机运行时为 `ok`。因此后续 FTS 维护以**项目本机运行时 + 内容不变量 + 搜索抽检**联合验收，不允许因异构运行时单项结果自动覆盖数据库。

### PHASE 3 第二批：170 documents canonical / alias 映射 — PASS

完整报告：`docs/PRIVATE_LIBRARY_DOCUMENT_MAPPING_20260914.md`。

- `GB/T 12801-2008`、`GB 55036-2022` raw SHA + extracted-text SHA 均相同，可列为未来独立高风险物理去重候选；
- `HJ 2025-2012`、`GB 15603-2022` raw SHA 相同但历史抽取文本/段落数不同，只做 alias，不物理删旧 FTS；
- 18 组同真实版本双身份已分类：12 组原已对齐 knowledge，6 组为 canonical gap；
- 2 组真实不同版本禁止合并；
- 38 条 legacy `evidence/...` 中仅 `LF_L027 / HJ 2025-2012` 有同 SHA current archive 目标可安全重绑，其余 37 条继续保留 legacy provenance；
- 7 个 archive-only 历史纯文本派生物不生成独立法规身份；
- 当前不做 document 物理 DELETE/archive 移动；任何物理压缩另开高风险批次。

### PHASE 4：六个 canonical gaps — PASS

已由总控回到官方来源核验，并在 PR #36 建立完整 law/lawVersion/evidence/review/succession 链：

- `危险化学品目录（2015版）`：1 个 law identity，显式建模为 2015 base → 2023 柴油调整后 → 2026 新增 5 种化学品后三个版本状态；私有 2015 原件仍映射 2015 版本，不冒充 2026 当前完整状态；
- `各类监控化学品名录`（工业和信息化部令第52号）；
- `GB 17914-2013`、`GB 17915-2013`、`GB 17916-2013`；
- `特种设备安全监察条例（2009修订）`。

新增：6 laws、8 lawVersions、8 authoritative evidence、6 law reviews、8 lawVersion reviews、2 successions；manifest 已更新到 102 laws / 105 lawVersions / 1,114 evidence / 28 successions。review hash 使用仓库 `canonical.py` 口径绑定。

私有 `source/library/document-aliases.json` 已在 Drive 原位回填 6 个 `canonicalVersionId`，`knowledgeUnmappedTitles=[]`；其策略仍是 `local_display_grouping_only`，`databaseMutation=false`、`archiveMutation=false`，未写 SQLite/FTS/archive。

PR #36 在 canonical 数据提交后已通过：

- `Validate safety data` — success；
- `Build current verified website` — success。

### PHASE 5：1,929 目标 ID 与 2,014 knowledge hazards 全量对账 — PASS

权威目标源已固定为本机 `D:\Desktop\隐患库_1929条_新版口径全部整改完成_20260914.xlsx`，工作表 `隐患明细_修订后!A2:R1930`，文件 SHA-256=`c84ec965ce808c780547842a1a82cb7eca01d0a8fdd018c054414b2b5be24a6f`。

- 工作簿 1,929 行、1,929 个唯一隐患 ID：621 条“已修订”、1,308 条“原审查通过/保留”；
- `knowledge/hazards` 2,014 个文件、2,014 个唯一对象 ID，文件名与对象 ID 一致；
- 1,929 个目标 ID 全部直接存在于 knowledge，`target-missing=0`；
- 目标集实际分类：1,409 `target-current`、512 `target-proposed`、8 `target-merged-alias`；
- knowledge 目标外 85 条不是“85 条重复”：56 条 merged 历史、21 条 split 父项、1 条正向事实非隐患历史、7 条 active 目标外待复核；
- 全库 64 条 `mergedInto` 边：缺失目标 0、循环 0；
- 工作簿标题与 knowledge 标题逐字一致 1,861 条；统一中英文标点和空格后一致 1,920 条；另 9 条为实质表述差异，需确认是已审阅专业化改写还是同步遗漏；
- 8 个目标内 merged alias 已统一为 `superseded`，不删除稳定 ID、merge 去向或证据；
- 7 个目标外且缺少完整正式 Gate 的实体已统一为 `proposed`，其 8 条 link review 已退回 rejected 并重绑上下文；
- 9 个实质标题差异均有 verified hazard review，且 Git 历史显示来自正式核验/官方来源核验批次，保留 knowledge 的专业化表述；
- 最终 lifecycle 库存：1,409 active、519 proposed、86 superseded，共 2,014；
- `validate_all.py` PASS，`strict_release_audit.py` PASS（blocker 0），正式包现场重建/verify PASS（releaseHash=`9acfc43cba1f2b58bc78307b7ac097e31d09872ebba63b0f470357fd95b47ec0`）；正式发布仍为 1,409 / 55 / 1,193 / 1,524，公网候选 0；
- pipeline 单元测试 26/26 PASS，Node 测试 13/13 PASS；reconciliation 连续重跑结果确定一致。

可重复执行工具：`tools/maintenance/reconcile_hazard_target_set.py`；受限状态修复工具：`tools/maintenance/apply_hazard_reconciliation_status.py`。机器映射：`docs/hazard-reconciliation.jsonl`。人类报告：`docs/HAZARD_RECONCILIATION.md`。工作簿未修改；私有母库、SQLite、archive 未修改。

### PHASE 6：519 条候选法规证据回绑 — PASS

完整人类报告：`docs/PHASE6_FINAL_DISPOSITION.md`；机器明细：`docs/phase6-final-disposition.jsonl`；可重复执行工具：`tools/maintenance/finalize_phase6.py`。

- PHASE 6 基线 519 条 `proposed` 全部生成最终处置，覆盖率 **519/519**；
- 110 条 exact current reviewed clause 候选全部重新复核，不再把 locator 相同直接等同为可转正；
- 20 条对象、现行条款逐字原文、官方/原始证据、适用性和当前上下文 review 全部闭环，经 Gate 后转为 `active`；
- 499 条继续 `proposed`，每条在机器处置清单中保留原因和下一证据动作；其中大量项目属于“未找到精确当前已核条款”或“仅 locator 匹配但语义适用性未证明”，另有错误条款对象、混合对象、数值口径变化、推荐性措辞、原文质量异常等明确原因；
- 新纳管现行《江苏省生产经营单位安全风险管理条例》（2024-11-01施行），建立 law/version/evidence/review 及第8、11、12、16条逐字官方证据链；对江苏风险辨识、风险管控清单、较大以上风险公示等候选优先采用当前更强、更直接的现行地方性法规；
- 关键保守判定包括：GB 55037-2022 第3.4.5条现行坡度上限为10%，不拿来支撑“>8%”；该条没有固定“距外墙5m”阈值；GB 50187-2012 第5.7.4条“出入口数量不宜少于2个”不机械当绝对违法；粉尘防爆第十八条不跨对象支撑一般废气收集、压差、集气罩、选址；GB 12158-2024 第7.6条当前 knowledge 文本质量异常，未转正式链；
- 工作分支最终 lifecycle：**1,429 active、499 proposed、86 superseded，共 2,014**；
- manifest：**103 laws / 106 lawVersions / 2,847 clauses / 2,014 hazards / 1,567 links / 1,161 evidence / 28 successions / 75 requirements**；
- 一次性 PHASE 6 finalization workflow 完整执行成功：`validate_all.py`、`strict_release_audit.py`、Node tests、pipeline Python tests、fresh current bundle build 和 `verify_unified_bundle.py` 均成功；workflow run `35078569190` conclusion=`success`；
- 本批未写私有 SQLite/FTS/archive，未修改既有 hazard 稳定 ID，未合并 PR，未部署 Pages，未做线上发布；一次性 workflow 与 trigger 在成功后已从分支清理。

### PHASE 7：publication / 官方来源 / 全文资料归整 — PASS

完整人类报告：`docs/PHASE7_PUBLICATION_AUDIT.md`；机器审计：`docs/phase7-publication-audit.json`；可重复执行工具：`tools/maintenance/finalize_phase7_publication.py`。

- `source/publication/law-index.json` 从 216 行归整为 **106 个 canonical law-version 行**，与 `knowledge/law-versions` 形成 1:1 身份投影；publication 不再创建第二套法规/版本身份；
- 清理 144 个 stale publication IDs，并在需要时通过 canonical ID、精确官方 URL 或“唯一官方名称 + 生效日期”解析到现有 knowledge 版本，不按标题相似猜测；
- 全文 catalog 从 155 行收口为 **69 个 canonical 来源关系**：其中 **11 份**明确 `official_legal_text` 且 `fullTextReviewed=true` 的获准官方全文继续公开，**58 个**只保留 metadata-only 官方入口；
- 86 个无法解析到 governed knowledge identity 的旧全文目录行退出 public catalog；对应 publication 文本/索引作为可重建派生物清理，不触碰私有原件、SQLite、OCR 或 archive；
- 全文搜索索引确定性重建为 **256 个 gram shards**；proposed hazard 泄漏 **0**，private-boundary marker 泄漏 **0**；
- `knowledge/` 未修改，知识库存继续保持 **103 laws / 106 lawVersions / 2,847 clauses / 2,014 hazards / 1,567 links / 1,161 evidence / 28 successions / 75 requirements**，hazard lifecycle 继续为 **1,429 active / 499 proposed / 86 superseded**；
- 一次性 PHASE 7 workflow run `35095422830` 已 `completed / success`；`validate_all.py`、`strict_release_audit.py`、Node tests、pipeline Python tests、fresh current bundle build 和 `verify_unified_bundle.py` 全部成功；
- 本批未修改私有 SQLite/FTS/archive，未修改稳定 knowledge IDs，未提交 release/current 生成包，未合并 PR，未部署 Pages，未做线上发布。

### PHASE 8：前端与本地私有版一致性验收 — PASS

可重复执行审计：`tools/maintenance/audit_phase8_consistency.py`；公开审计：`docs/phase8-public-audit.json`；私有审计：`docs/phase8-private-audit.json`；本地展示回归测试：`tools/pipeline/tests/test_library_site_phase8.py`。

- 公网 fresh bundle 审计 PASS：**1,429** 个正式隐患、**1,205** 个随正式链发布的条款、**57** 个实际正式法规版本；`knowledge/` 中 499 个 proposed 在公网为 **0**；private-boundary marker 命中 **0**；
- publication 全文/入口边界保持为 **69** 个 catalog documents，其中 **11** 份获准全文、**58** 个 link-only 官方入口；其中 27 个是 catalog-only canonical versions，不被错误当成当前正式法规跳转；
- `web/js/library.js` 已只对实际 formal law index 中的版本显示“查看收录条款与关联隐患”，source-only 全文/入口不再生成无效正式法规跳转；
- 本地 `tools/v4/library_site.py` 使用 `document-aliases.json` 仅做私有展示分组/canonical label，不改变正式 authority；只有实际存在的原始文件才生成“打开原始文件”链接，legacy `evidence/...` provenance 不再变成断链；
- 私有库只读审计 PASS：SQLite **170 documents / 215,326 FTS rows / 215,326 paragraphCountSum / per-document mismatch 0**；132 个 archive-backed document rows 对应 129 个唯一 archive SHA，Drive 当前 archive 中 **129/129** 全部找到；38 条 legacy evidence provenance 保留；unknown prefix 0、archive SHA mismatch 0；
- private alias 共 **18 groups / 36 member document keys / 18 canonicalVersionIds**，missing members 0、knowledge unmapped titles 0；审计未写 SQLite/FTS/archive；
- PHASE 8 finalizer workflow run `35120861560` 已 `completed / success`：frontend/private compatibility tests、`validate_all.py`、`strict_release_audit.py`、fresh current bundle build + verify、公开一致性审计、私有/公开边界检查、公开审计报告提交全部成功；
- 本阶段没有修改 `knowledge/`、`source/publication/` 的业务数据，没有提交 `source/releases/current/` 生成物，没有 merge PR，没有部署 Pages，没有线上发布；一次性 PHASE 8 workflow/trigger 已在成功后清理。

### PHASE 9：全量验证与 Release Candidate — PASS

公开 RC 验收记录：`docs/phase9-rc-public.json`。

- 工作分支：`phase9-release-candidate-20260917`；公共 RC 验证源提交为 `c74a0970f1cc64e5d2bad9944340304c171050f2`，workflow 自动记录提交为 `c58261f77d77ebe79e73e6f0385060caefab764c`；
- GitHub Actions run `35122196162` 已 `completed / success`：Node tests、pipeline Python tests、`validate_all.py`、`strict_release_audit.py`、fresh unified release build、`verify_unified_bundle.py`、PHASE 8 regression audit 全部 PASS；
- 公共 RC 保持 **1,429 hazards / 57 laws / 57 lawVersions / 1,205 clauses / 1,544 links**，strict blockers 0，knowledge 中 499 proposed 在公网仍为 0；publication 仍为 69 个 catalog documents（11 full text + 58 link-only）；
- 使用 run `35122196162` 上传的同一 RC 源码快照，在本地接入真实私有 `fulltext.sqlite3` 与 `document-aliases.json` 后实际执行 `tools/build_local_release.py`，直接退出码 **0**；
- 本地最终版生成成功：**170 documents / 215,326 FTS rows / 215,326 paragraphCountSum / 36 canonical alias members**；生成 170 个法规全文页面及统一入口；
- 私有 SQLite SHA-256 在构建前后均为 `7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`，alias 文件构建前后哈希也一致，确认本地构建只读、未修改私有库；
- 本地重建公开包 verify PASS，releaseHash=`680089d53c1fe793bcc71f420093aa1080126e29e4c4d9b2a043849cf01209a9`；该哈希属于本地当日重建产物，不替代公共 RC 报告中的 GitHub Actions RC releaseHash；
- 本阶段未修改 `knowledge/` 业务数据、未修改私有 SQLite/FTS/archive、未提交 `source/releases/current/` 生成物、未合并 main、未部署 Pages、未做线上验收。

---

## 5. MASTER ROADMAP

状态：`DONE` / `IN PROGRESS` / `PENDING` / `BLOCKED`。

### PHASE 0 — 架构与发布边界收口 — DONE
knowledge 主导；candidate 不发布；upcoming 不提前支撑；current 现场生成。

### PHASE 1 — 私有母库只读实体审计 — DONE
170 documents、archive、incoming、inventory、pending、knowledge 初步身份映射完成。

### PHASE 2 — 母库整理方案与安全变更清单 — DONE
修复/归并分批、备份回滚门禁、维护工具和测试已建立。

### PHASE 3 — 私有母库实际修复与确定性去重 — DONE
FTS 修复和完整 document mapping 已闭环；暂不执行非必要物理去重。

### PHASE 4 — `knowledge/` 法规身份/版本 canonical 化 — DONE
六个 private canonical gaps 已正式纳管，危险化学品目录修订链已显式建模，private alias 已全部映射 knowledge canonical；PR #36 CI Validate/Build 已成功。

### PHASE 5 — 2,014 knowledge 隐患实体 ↔ 1,929 目标集对账 — DONE
完整机器映射和人类报告已生成；目标缺失 0，85 条目标外实体已逐项分类，24 个状态/标题差异已闭环，Gate 和正式包验证通过。

### PHASE 6 — 候选法规证据回绑与转正 — DONE
519/519 候选已形成最终处置；20 条完整 Gate 后转 active，499 条证据/适用性不足继续 proposed 并保留明确原因；110 条 exact 候选全部复核；现行江苏风险管理条例已纳入 canonical 证据链；PHASE 6 验证链全部通过。

### PHASE 7 — publication / 官方来源 / 全文资料归整 — DONE
publication 已收口为 knowledge canonical 身份投影；题录、官方入口、获准全文与搜索索引边界完成归整，proposed/private 泄漏均为 0。

### PHASE 8 — 前端与本地私有版一致性验收 — DONE
公网仅投影正式 Gate 数据；source-only catalog 不生成错误正式法规跳转；本地私有版 canonical alias、全文和原始文件链接边界已验证；公开/私有审计均 PASS。

### PHASE 9 — 全量验证与 Release Candidate — DONE
公共 RC workflow 与真实私有库 local release build 均已完成并 PASS；输入私有库哈希构建前后不变，proposed/private 发布边界保持不变。

### PHASE 10 — 最终合并 main、GitHub Pages 部署、线上验收 — DONE
PR #40 checks 全绿后已合并 `main`；main Validate/Build/Deploy 全部 success；GitHub Pages 发布成功；对实际部署 artifact 完整性、公开边界、搜索索引/法规索引/全文目录执行验收，并通过 GitHub-hosted runner 对公网 URL 做独立 HTTP 抽检，全部 PASS。

### PHASE 11 — 长期维护循环 — IN PROGRESS
首轮维护治理已完成：等待态审计、publication 长期完整性门禁及门禁回归测试均已进入 `main`；当前没有新的正式业务数据待发布，回到等待下一法规/版本/隐患/证据/维护触发条件的状态。SQLite 仍按既有规则定期备份/integrity；仅阶段状态实际变化时更新本文件。

---

## 6. CURRENT PHASE — 当前阶段

**PHASE 11 长期维护循环已启动；首轮治理维护 DONE，当前处于等待下一触发条件状态。**

2026-09-17 首轮 PHASE 11 维护完成四组实际动作：

- PR #42：核对远端 `main` / workflows / Actions / PR / issue / 生成物边界，刷新 README、MAINTENANCE、HANDOFF 并新增等待态审计记录；
- PR #43：新增只读 `validate_publication_integrity.py` 并同时接入 Validate 与实际 Pages Build，长期阻断 publication 非 canonical 身份、catalog/物理全文不一致、陈旧 search-index/gram shard、proposed/private 泄漏等问题；
- PR #45：新增 1 个正常通过 + 6 个失败场景的合成回归测试，并固定 catalog / search-index / full-text / gram schema 与 catalog/search `asOf` 一致性。
- 首轮本地验收：在独立临时 worktree 上检出 `c2ffe2042a316881f229eea8899156fa897f601d`（与当时最新 `origin/main` 完全一致），复用真实私有 `source/library/` 后执行 `py -3 tools/build_local_release.py`，`validate_all.py`、`strict_release_audit.py`、`validate_publication_integrity.py` 与 `verify_unified_bundle.py` 全部 PASS；完整记录见 `docs/PHASE11_LOCAL_ACCEPTANCE_20260917.md`。

PR #45 合并提交 `9e8de313e2321a9b81b8e812155434d7735e463b` 后，`main` Validate run `35180759610` success；Build/Pages run `35180759551` 的 build 与 deploy 均 success。PHASE 11 治理改动没有修改正式业务数据：公开投影仍为 **1,429 hazards / 57 law versions / 1,205 clauses / 1,544 links**，499 proposed 仍保持公网 0，publication 仍为 69（11 full_text + 58 link_only），已验收业务 `releaseHash` 仍为 `552cca4f3e12877c7af1f56cd323220fe6af5631e4b334ffddb04881bbc83a07`。

首轮私有本地版验收的历史结果为：HEAD=`c2ffe2042a316881f229eea8899156fa897f601d`，**1,429 active / 499 proposed / public proposed 0 / 57 formal law versions / 1,205 clauses / 1,544 links / 170 private document carriers**，全部 Gate 与 unified bundle verify 均 PASS。该结果不再代表最新主线统计。

远端治理进展：2026-09-17 已为 `main` 正式配置并激活 GitHub Repository Ruleset（ID `23589482`，名称 `Protect main`，状态 `active`），`branches/main` 的 `protected` 状态已技术实测生效（`true`）。技术保护规则完全满足项目治理要求：
- 变更必须通过 Pull Request 引入（单人维护采用 `required_approving_review_count: 0`，避免自锁死循环）；
- 必需状态检查强制绑定当前生产 check-runs：`validate` 与 `build`；
- 禁止 force push（`non_fast_forward`）；
- 禁止删除 `main`（`deletion`）；
- 保持 GitHub Pages 从 `main` 自动发布机制正常运转。

远端治理与分支清理已完全收口：2026-09-17 经用户明确审批，已从 `origin` 批量清理 29 个已完成/被替代的历史远端分支；明确包含历史独有提交的 3 个分支（`chat-v4`、`phase3-local-alias-grouping-20260914`、`verify-batch-003`）严格保留。远端分支只保留主干与上述 3 个归档证据分支。Issue #44 所跟踪的主干技术保护与历史分支清理两项任务均已完全解决，Issue #44 正式 CLOSED（completed）。

新标准收录进展：2026-09-17 完成强制性国家标准《有限空间作业安全技术规范》（GB 46768-2025）的全流程收录与结构化条款入库：
- 原件入库：官方原件 PDF 归档至 `source/library/archive/e8af78774afffaa1b758a63cc1a8e69b802d345df4da73c197f861248d0bdcf8/original`；
- 私有全文母库：`fulltext.sqlite3` documents 表新增 1 行至 171 份，全文检索表新增 138 段至 215,464 行，`document-aliases.json` 建立到 canonicalVersionId `LV_STD_624AF774D05822F9B543D281` 的映射；
- 知识库：新增 1 项权威归档证据（`E_46768_GB46768`），新增 63 条第 4~7 章核心规范条款（`C_46768_4_1_1` 至 `C_46768_7_2`）及逐条 verified review，条款总量增至 2,910；
- 验证：`validate_all.py`、`strict_release_audit.py`、`validate_publication_integrity.py`、全量单元测试与本地最终版（171 document carriers）构建验证全部 PASS。

---


搜索算法升级进展：2026-09-17 完成前端中文复合检索切词与假阳性防护升级（PR #51）：
- 在 `web/js/search.js` 引入领域词汇最长匹配切词，将无空格连续中文（如 `配电箱遮挡`）自动切分为概念单元并强制 `termsMatch` 概念全命中；
- 扩容 `遮挡/堵塞/堆物/占用/妨碍` 同义词组，将 2-gram 弱模糊门槛收紧至 75%，彻底消除“配电箱遮挡”命中“配线不整齐或绞接”等假阳性；
- 单元测试与 GitHub Actions CI 双绿通过并合入主干，Pages 部署成功生效。

高频电气隐患补录进展：2026-09-17 正式收录漏录的高频电气隐患“配电箱（柜）前堆放杂物，操作通道或维护空间被遮挡、占用”（`H_ELEC_PDX_CHANNEL_BLOCKED`）：
- 关联直接依据 1：《用电安全导则》（GB/T 13869-2017）第 5.1.1 条（用电产品周围安全通道、工作空间及防堆放要求）；
- 关联直接依据 2：《低压配电设计规范》（GB 50054-2011）第 4.2.5 条表 4.2.5 注 4、注 5（挂墙式配电箱箱前操作通道宽度不宜小于 1m，落地式动力箱柜通道宽度要求）；
- 补齐条款实体 `C_GB50054_4_2_5_5`、权威证据 `E_GB50054_4_2_5` 及完整 verified review 边车；
- 知识库 active 隐患数增至 **1,430**，条款数增至 **2,911**，关联数增至 **1,569**，`validate_all.py` 与 `strict_release_audit.py` 均 PASS。


高频电气候选隐患首批转正进展：2026-09-17 针对 499 条 proposed 候选开展电气专业攻坚，首批严格核实并转正 12 项高频电气隐患：
- 转正隐患清单：`H032`（通道/空间不足）、`H_BE5284032A21441CA62FFDE0B2`（安装环境）、`H_AC89D3C3CCF049EF991BA4E42F`（线路绝缘强度）、`H_DEED92095F4043AFB93AB75583`（接地线可靠连接）、`H_B0A88B69CC0047CE8BF9D87EB6`（插头插座接线）、`H_1A8786209C974B6BB28C4ADFA5`（超负荷运行）、`H_2724BCA646E74C1694B53CF8DB`（停运切断电源）、`H_8ECAE760F5A5413D8013602429`（移动设备软电缆）、`H_265A5682E86D43F0B813544099`（箱门软导线跨接及标识）、`H_3E588442618F422D926705893B`（柜台箱金属框架接地）、`H_43C6C076F9FC456DB09138A19A`（配电箱门接地连接）、`H_5565236C0E354D5D8428BC1DEB`（箱体箱门软铜线跨接）；
- 依据回绑：全部回绑至现行有效标准《用电安全导则》（GB/T 13869-2017）第 5.1.1、5.1.2、5.1.3、5.2.1、5.2.2 条，以及《建筑电气工程施工质量验收规范》（GB 50303-2015）第 5.1.1 条主控项目；
- 补齐 9 条核心条款实体、2 项权威官方发布/归档原件证据（`E_GBT13869_2017`、`E_GB50303_2015`）及 12 组完整 verified review 边车；
- 知识库 lifecycle 更新为：**1,442 active / 487 proposed / 86 superseded，总计 2,015**；
- 条款总数增至 **2,920**，关联总数增至 **1,581**，证据总数增至 **1,165**；全量 Gate 校验均 PASS。

最新主线本地最终版复验：2026-09-18 在同一独立验收 worktree 检出 `125a7afd76d9e1152d9d7f2f9ff70f9cde9e818d`，与当时 `origin/main` 完全一致。真实私有库只读审计为 **171 documents / 215,464 FTS rows / 215,464 paragraphCountSum / mismatch 0 / integrity ok**，SQLite SHA-256 为 `4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`，构建前后 SHA/size/mtime 完全不变。现场重建结果为 **1,442 active / 487 proposed / public proposed 0 / 58 formal law versions / 1,216 published clauses / 1,558 published links / 171 private document carriers**，releaseHash=`b1f29e07b00e9e56c53bf4eb1ea7d0c13e84ec31657b895b3a7bdc3c8a2dd094`；全部 Gate 与 unified bundle verify PASS。完整复验记录见 `docs/PHASE11_LOCAL_ACCEPTANCE_20260917.md` 第 6 节。

GB/T 47236-2026 候选专题批次：2026-09-18 从 487 条 proposed 基线中复核 17 条。16 条候选的隐患反向表述与官方归档现行条款直接对应，适用范围统一限定为该标准覆盖的低压铸造机、差压铸造机及其他金属型铸造设备，已补齐 hazard/link 当前审核哈希并转为 active。`H_GBT47236_4_2_2_3` 同时包含运动部件防护与警告标志两个对象，与既有 `H_F8BD176AF46643EA9E3CC56A6F` 仅部分重叠，继续 proposed，未强行合并。本批后 lifecycle 为 **1,458 active / 471 proposed / 86 superseded**；fresh public bundle 为 **1,458 hazards / 58 law versions / 1,232 clauses / 1,574 links / public proposed 0**，releaseHash=`6c67b709ba8405e3a9763ff275b4cb1b7c9c14422754714eab379c44c61f47f0`。Validate、strict release audit、publication integrity 和 unified bundle verify 均 PASS；未修改私有 SQLite/archive。

GB/T 47236-2026 独立义务专题批次：同日继续从 471 条 proposed 中复核并转正 26 条。本批只选择条款自身已经完整规定所述义务的项目，不使用外部标准题名、表格标题或推荐性措辞补足缺失判断；全部候选均限定至该标准覆盖设备并补齐当前 hazard/link 审核。批次后 lifecycle 为 **1,484 active / 445 proposed / 86 superseded**；fresh public bundle 为 **1,484 hazards / 58 law versions / 1,258 clauses / 1,600 links / public proposed 0**，releaseHash=`24913cd6f3f6014c0c50d05069ce4741969631011876d1ef8a1a9905512edfa6`。Validate、strict release audit、publication integrity、unified bundle verify 和 15 项 Node 测试均 PASS；未修改私有 SQLite/archive。

### PHASE 12 exact-locator 候选批次 — 2026-09-18

从 445 条 proposed 中复核 15 条精确定位候选，11 条通过当前条款、对象、审核哈希和重复门禁后转为 active；4 条因同条款已有活动隐患保留 proposed。当前 lifecycle 为 **1,495 active / 434 proposed / 86 superseded**；fresh public bundle 为 **1,495 hazards / 58 law versions / 1,267 clauses / 1,611 links / public proposed 0**，releaseHash=`b99833df4c0cbcd8bd3e9f7a14880c74de883e9add5dd22a4a270d3201752643`。Validate、strict release audit、publication integrity、unified bundle verify 和 15 项 Node 测试均 PASS；未修改私有 SQLite/archive。机器明细见 `docs/PHASE12_EXACT_LOCATOR_BATCH.md` 和 `docs/phase12-exact-locator-disposition.jsonl`。

## 7. NEXT ACTION — 下一动作

> **当前第二个 GB/T 47236-2026 专题批次已完成本地数据、Gate 与 fresh bundle 验证，待提交 PR、CI、合并和 Pages 验收。合并后继续按证据集中的专题批次处理剩余 445 条 proposed；下一批应优先核验被引用标准的具体条款与表格内容，不得只凭交叉引用标题转正。**

进入下一维护批次时继续遵守现有边界：新证据先进入私有来源层并核身份/版本/效力；`knowledge/` 仍是唯一正式结构化事实源；候选必须经完整 Gate 才能转正式；`proposed` 不得直接进入公网。每次**正式业务数据**变化后执行 Validate → strict gate → publication integrity → fresh build → verify → Pages → online acceptance。纯文档/治理/测试变化只执行其受影响检查和正常主线 CI，不为制造新数字而重复业务线上验收。

仓库治理方面，所有未结事项已全部清零，日常不盲目频繁改写文件或提交，保持生产环境高度平稳。
