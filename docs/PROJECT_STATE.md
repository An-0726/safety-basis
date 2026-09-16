# 项目阶段状态与恢复计划

本文件保留截至 2026-09-14 的业务核验记录，并补记 2026-09-16 至 2026-09-17 的 PHASE 5 Git 交付闭环、PHASE 6 候选证据回绑、PHASE 7 publication 来源归整和 PHASE 8 前端/私有版一致性验收最终状态。历史统计数字仍按对应阶段记录；工作分支新统计单独明确标注，不将未合并结果冒充已经发布的 `main` 结果。

**PHASE 8 已按用户明确授权完成，当前暂停。** PHASE 9 尚未启动；没有新的明确授权，不继续 Release Candidate、PR 合并、Pages 部署或线上发布。

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

**LAST VERIFIED：2026-09-17（PHASE 8 工作分支）；`main` 正式发布基线仍停留在 PHASE 5。**

当前 Git 唯一正式主线仍为 `main`。PR #36 `Phase 4: canonicalize private-library law gaps` 已合并到 `main`（提交 `0118a13a`）；PHASE 5 PR #38 已于 2026-09-16 合并，当前 `main` 合并提交为 `88cc7f7`（完整 SHA：`88cc7f739e154c26f3866857e9c3f6b0ffa7be5f`）。PHASE 6/7/8 连续工作成果当前位于分支 `phase8-frontend-private-consistency-20260916`，尚未创建/合并对应发布 PR，尚未部署 Pages 或做线上发布。

公开发布架构已收口：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物，不提交 Git；
- 正式站只发布 Gate 通过的已核验隐患；
- `proposed` 不进入公网；
- `upcoming` 尚未实施版本不能支撑当前正式隐患。

### `main` 当前正式发布基线（PHASE 5）

- 1,409 条正式隐患；
- 55 个实际引用法规版本；
- 1,193 条正式条款；
- 1,524 个正式关联；
- 519 条 `proposed` 候选仅留 `knowledge/`，公网候选 0；其中目标集内 512 条、目标集外 7 条。

### PHASE 8 工作分支继承的最新 knowledge 状态

PHASE 6 从 519 条 `proposed` 基线候选出发，逐条生成最终处置；其中 20 条在官方原文、对象适用性、当前 review hash 和完整 Gate 均满足后转为 `active`，499 条因证据、对象、条件、现行数值、条文质量或适用性不足继续保持 `proposed`。PHASE 7/8 未改变该业务状态。因此当前工作分支 lifecycle 为：**1,429 active、499 proposed、86 superseded，共 2,014**。

当前 manifest 库存为：**103 个法规身份、106 个法规版本、2,847 条条款、2,014 个隐患实体、1,567 个关联、1,161 个 evidence、28 条 succession、75 条 requirements**。

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
- PHASE 8 工作分支：公开前端、canonical 跳转和本地私有全文展示边界已验收；公开/私有审计均 PASS，最终 workflow run `35120861560` success；PHASE 6/7/8 尚未进入发布 PR。

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

### PHASE 9 — 全量验证与 Release Candidate — PENDING
至少运行 `validate_all.py`、`strict_release_audit.py`、统一 release build/verify、pipeline unit tests、node tests、local release build。

### PHASE 10 — 最终合并 main、GitHub Pages 部署、线上验收 — PENDING
工作分支 PR → CI 全绿 → 合并 main → main Validate/Build/Deploy success → 线上抽检。

### PHASE 11 — 长期维护循环 — PENDING
新法规/版本先入私有证据层，核身份/版本/效力后更新 knowledge；SQLite 定期备份/integrity；仅阶段状态实际变化时更新本文件。

---

## 6. CURRENT PHASE — 当前阶段

**PHASE 8 DONE；PAUSED。**

用户已明确要求从仓库真实全局状态继续，并确认不应停留在 PHASE 7。PHASE 8 现已完成：公开前端只展示正式 Gate 数据；source-only publication catalog 不再产生无效正式法规跳转；本地私有版使用 canonical alias 展示且不会把 legacy provenance 转成断链原件链接。

当前工作分支 `phase8-frontend-private-consistency-20260916` 继承 PHASE 6/7 的业务数据，`knowledge/` 在 PHASE 8 零修改：**1,429 active / 499 proposed / 86 superseded / 2,014 total**；manifest 继续为 **103 laws / 106 lawVersions / 2,847 clauses / 2,014 hazards / 1,567 links / 1,161 evidence / 28 successions / 75 requirements**。

公开审计 `docs/phase8-public-audit.json` 为 PASS：1,429 public hazards、1,205 public clauses、57 formal law versions、69 catalog documents（11 full text + 58 link-only），499 proposed 保持 public 0，private boundary marker hits 为空。私有审计 `docs/phase8-private-audit.json` 为 PASS：170 documents / 215,326 FTS rows 与 paragraph sum 一致，129/129 current archive SHA folders 找到，18 组 alias 无缺员/无 knowledge unmapped title，且只读未修改 SQLite/FTS/archive。

最终一次性 workflow run `35120861560` 已 `completed / success`，受影响测试、严格 Gate、fresh bundle 构建/校验、公开一致性审计和边界检查全部通过。成功后 PHASE 8 的一次性 workflow/trigger 已清理。误从过期 PHASE 6/7 状态创建的 Draft PR #39 已关闭且未合并，避免重复 Phase 7 工作。

本阶段没有发布 Release Candidate，没有合并 PHASE 6/7/8 到 main，没有部署 Pages，没有做线上验收。

---

## 7. NEXT ACTION — 下一动作

> **PAUSED。PHASE 9 尚未启动。下一动作仅在用户新的明确授权后执行：进入 PHASE 9 全量验证与 Release Candidate。**

如后续获授权，PHASE 9 从当前 `phase8-frontend-private-consistency-20260916` 的已验证状态继续，不重新做 PHASE 6/7/8，也不改变 499 条 proposed 的隔离状态。至少完成 `validate_all.py`、`strict_release_audit.py`、统一 release build/verify、pipeline unit tests、Node tests 与 local release build，并形成明确的 Release Candidate 验收记录。PR/合并 main、Pages 部署和线上验收仍属于 PHASE 10，不得自动越级执行。

---