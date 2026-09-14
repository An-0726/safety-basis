# AGENTS.md — 仓库长期接手记忆与总施工计划

> **这是 AI / Codex / 新维护者的唯一实时接手入口。**
> 新窗口必须先读本文件，再读根目录 `AGENT_EXECUTION_PROTOCOL.md`，然后按 `CURRENT PHASE / NEXT ACTION / MASTER ROADMAP` 连续执行。完成一个动作后必须更新本文件并自动推进，不依赖旧聊天解释项目状态。

## 0. 一句话接手

> **接手 `An-0726/safety-basis`。先读 `AGENTS.md` 和 `AGENT_EXECUTION_PROTOCOL.md`；总控负责法规核验、隐患描述、证据链、knowledge/canonical、candidate、发布与上线判断；只有必须操作用户本机且当前工具做不到的步骤，才生成严格提示词交给本地 Luna 执行，回传后由总控复核。当前工作停在 PHASE 5 的 2,014 knowledge hazards ↔ 1,929 目标 ID 精确对账，尚未完成差集分类；不要把 `2014-1929=85` 当作已证实的重复数。最终目标是数据 Gate 全绿、合并 `main`、GitHub Pages 部署成功并完成线上验收。**

---

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

只有以下全部满足，才算本轮整体整理完成：

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
11. `AGENTS.md` / README / HANDOFF 与最终状态一致。

---

## 2. 当前正式基线

**LAST VERIFIED：2026-09-14**

当前 Git 唯一正式主线：`main`。当前阶段工作 PR：**#36 `Phase 4: canonicalize private-library law gaps`**，分支 `phase4-canonical-gaps-20260914`；PR 分支上的 `Validate safety data` 与 `Build current verified website` 已成功，待本次 handoff 更新后重新验收再合并。

公开发布架构已收口：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物，不提交 Git；
- 正式站只发布 Gate 通过的已核验隐患；
- `proposed` 不进入公网；
- `upcoming` 尚未实施版本不能支撑当前正式隐患。

当前正式发布基线仍为：

- 1,409 条正式隐患；
- 55 个实际引用法规版本；
- 1,193 条正式条款；
- 1,524 个正式关联；
- 512 条 `proposed` 候选仅留 `knowledge/`，公网候选 0。

PHASE 4 后当前 knowledge 库存：**102 个法规身份、105 个法规版本、2,843 条条款、2,014 个隐患实体、1,547 个关联、1,114 个 evidence、28 条 succession、75 条 requirements**。

新版 Excel 目标集：**1,929 个唯一隐患 ID（621 修订、1,308 保留）**。它不是正式发布数量。

### 转手快照 — 2026-09-14

- PHASE 5 已启动，但**只确认了两侧基数和目标口径，尚未完成逐 ID reconciliation**；
- 已确认：`knowledge/hazards` 当前共有 **2,014 个隐患实体**；2026-09-14 revised workbook 目标集共有 **1,929 个唯一 ID**；
- `2,014 - 1,929 = 85` 只是算术差额，**不得解释为 85 个重复项、85 个废弃项或 85 个应删除项**；真实差额必须按 `mergedInto / aliases / lifecycle / review / target membership` 逐实体解释；
- 本轮在准备转手前曾尝试从 GitHub 目录树继续提取完整 ID，但**精确差集尚未产出，也没有生成可提交的 PHASE 5 mapping/report**；下一位应重新从权威 staging/mapping + `knowledge/hazards` 做确定性全量读取，不依赖聊天里未落盘的中间列表；
- 本轮**没有修改任何 PHASE 5 hazard 实体、稳定 ID、review、relation、SQLite/FTS/archive**；不要把当前 handoff 文档提交误解为 PHASE 5 数据已处理；
- 当前最安全的恢复点仍是：先完成 PR #36 的 handoff/CI/merge 闭环，再从最新 `main` 新开 PHASE 5 分支做实质数据对账。

### 最近 Git 里程碑

- PR #29：正式/候选发布边界与 current 现场生成收口；
- PR #30：建立 `AGENTS.md` 作为仓库长期接手入口；
- PR #31：扩展为完整 MASTER ROADMAP；
- PR #32：完成 PHASE 1 私有母库审计，加入私有母库修复方案、安全维护工具和测试；
- PR #34：新增 `AGENT_EXECUTION_PROTOCOL.md`，固化“总控判断、本地 Luna 只执行本机操作”的协作边界；
- PR #36（当前）：完成 PHASE 3 document mapping 收口和 PHASE 4 六个 canonical gaps；CI Validate/Build 已成功，待本文件更新后最终验收/合并。

---

## 3. 权威层级与硬规则

### 法规事实

正式法规事实必须回到官方原文/原始证据和 `knowledge/`。AI 摘要、搜索摘要、OCR、TXT、HTML、Excel“条款要点”只能用于定位，不能作为正式法规原文。

找不到准确原文或条款时标记“待核实 / 证据不足”，不得编造。

“最新发布”不等于“当前适用”。真实不同版本分别保留；尚未实施版本不得提前作为当前依据。

### 项目数据

- `knowledge/`：正式结构化法规身份、版本、条款、隐患、关联、审核；
- `source/library/archive/`：私有证据归档，默认不可变；
- `source/library/fulltext.sqlite3`：私有全文检索数据库，可维护索引，但不是最高法律证据；
- `source/library/incoming-*`：收件/暂存；
- `source/publication/`：公开来源资料层；
- `source/releases/current/`、`dist/`、网页索引：可重建成品，不得反向当母库。

禁止为了界面整洁重编号 `LF_* / LV_* / C_* / H_*` 稳定 ID。归并优先 alias / canonical mapping。

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

### PHASE 5 — 2,014 knowledge 隐患实体 ↔ 1,929 目标集对账 — IN PROGRESS
逐项解释当前正式、当前候选、历史实体、合并别名、目标外实体、目标缺失/待判断，不靠总数猜重复。

### PHASE 6 — 候选法规证据回绑与转正 — PENDING
按“法规身份 → 当前适用版本 → 条/款/项 → 官方原文 → 原始证据 → 适用性审核”处理；证据不足继续 candidate。候选数量以 PHASE 5 对账后的实时结果为准，不再机械沿用旧 512 总数。

### PHASE 7 — publication / 官方来源 / 全文资料归整 — PENDING
publication 只挂来源；正式法规数由 knowledge 决定。

### PHASE 8 — 前端与本地私有版一致性验收 — PENDING
公网只显示正式数据；本地版加载私有全文；canonical 化不得导致全文链接或 archive_ref 失联。

### PHASE 9 — 全量验证与 Release Candidate — PENDING
至少运行 `validate_all.py`、`strict_release_audit.py`、统一 release build/verify、pipeline unit tests、node tests、local release build。

### PHASE 10 — 最终合并 main、GitHub Pages 部署、线上验收 — PENDING
工作分支 PR → CI 全绿 → 合并 main → main Validate/Build/Deploy success → 线上抽检。

### PHASE 11 — 长期维护循环 — PENDING
新法规/版本先入私有证据层，核身份/版本/效力后更新 knowledge；SQLite 定期备份/integrity；每个实质阶段更新本文件。

---

## 6. CURRENT PHASE — 当前阶段

**PHASE 5 — 2,014 knowledge 隐患实体 ↔ 1,929 目标集逐项对账。**

PHASE 4 的法规 canonical 决策、正式 knowledge 数据、verified reviews、private alias 回填和 CI 验收已经完成。当前不需要 Luna；总控直接读取仓库/Drive 中 2026-09-14 revised workbook 的 staging/mapping 数据和 2,014 个 knowledge hazards 做确定性对账。

**转手状态：** 当前只完成了 PHASE 5 入口确认，尚未形成权威完整 reconciliation。下一位接手者应把聊天中的任何目录树/临时提取都视为非权威中间态，从落盘数据重新全量计算。

---

## 7. NEXT ACTION — 下一动作

> **总控先定位 1,929 目标 ID 的权威 staging/mapping 来源，逐项与 `knowledge/hazards` 2,014 实体做 ID/mergedInto/alias/lifecycle/review 状态对账，输出完整 reconciliation，不以 `2014-1929=85` 反推“重复”。每个 knowledge hazard 和每个目标 ID 都必须有唯一解释。**

执行顺序：

1. 定位并固定 2026-09-14 revised workbook 的 1,929 唯一目标 ID 清单及 staging 映射来源；
2. 全量读取 `knowledge/hazards` 的 `id / title / aliases / lifecycle / mergedInto` 与 hazard review 决策；
3. 先做纯 ID 集合核对并保存原始结果：`target ∩ knowledge`、`knowledge - target`、`target - knowledge`；不要跳过这一步直接靠标题猜；
4. 再逐项分类：`target-current`、`target-proposed`、`target-merged-alias`、`knowledge-extra-historical/non-target`、`target-missing`、`needs-review`；
5. 对 621 修订、1,308 保留分别核对实际实体去向，不因标题近似自动合并；
6. 输出机器可读 mapping + 人类审计报告，明确 2,014 与 1,929 差额的逐实体解释；
7. Gate/一致性检查通过后更新本文件并自动推进 PHASE 6。

**接手者不要依赖上一窗口未落盘的“候选 85 项”列表；本 handoff 明确记录：该精确列表尚未完成。**

PR #36 只收口 PHASE 3/4。完成本次 handoff 更新后重新等 CI，全绿即合并；PHASE 5 实质数据工作从最新 `main` 新开分支继续。

---

## 8. 写操作与风险边界

低风险可自主：法规核验、隐患描述、证据链分析、只读审计、生成 mapping/对账报告、在副本上验证、修改 Git 代码/测试/文档（走分支/PR/CI）。

高风险必须先备份和验证：写工作 SQLite、删除/移动 archive、合并 documents、删除 knowledge 正式实体、改稳定 ID、大批量正式条款/关联修改。

出现以下任一条件立即停止并回滚/调查：documents 数意外变化；FTS/paragraphCountSum 意外变化；全文内容摘要变化；逐 document FTS 不一致；全文检索明显缺失；archive_ref/SHA 失联；canonical 合并丢版本/来源/证据链。

---

## 9. 绝对禁止事项

- 不把私有 PDF、SQLite、OCR、企业资料提交 GitHub；
- 不提交 `source/releases/current/` 生成包；
- 不为整洁重编号稳定 ID；
- 不按标题相似直接删除法规或隐患；
- 不把同名不同真实版本合并；
- 不把 publication 多来源变成多个正式法规；
- 不把 upcoming 当当前依据；
- 不从 Excel/OCR/TXT/HTML 反向覆盖正式知识源；
- 不在 SQLite 正被写入时替换数据库文件；
- 不为了 candidate 清零编造证据；
- 不创建 `final2/latest2` 等平行最终版；
- 不把法规核验、隐患描述、证据链或 canonical 决策权交给本地 Luna。

---

## 10. Git、跨窗口与本地执行器规则

涉及代码、架构、正式数据、候选策略、发布规则或接手状态：

1. 从最新 `main` 建分支；
2. 修改；
3. 跑测试/Gate/构建；
4. 开 PR；
5. CI 全绿再合并 `main`；
6. main Pages 成功后才算公开站变更完成。

每个实质阶段结束前必须更新：`LAST VERIFIED`、MASTER ROADMAP 状态、当前已核事实、`CURRENT PHASE`、`NEXT ACTION`；架构/口径变化同步 README，人类交接重大变化同步 `docs/HANDOFF.md`。

协作边界以 `AGENT_EXECUTION_PROTOCOL.md` 为准：**总控负责判断与验收；Luna 只负责当前工具无法完成的本机执行。**本地执行器报告 PASS 后仍必须由总控独立复核。

`NEXT ACTION` 只是光标，`MASTER ROADMAP` 才是总任务。完成一个 NEXT ACTION 后不要停，除非遇到高风险写操作需要确认、本地状态无法验证、缺失证据或外部阻塞。
