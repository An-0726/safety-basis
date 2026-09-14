# AGENTS.md — 仓库长期接手记忆与总施工计划

> **这是 AI / Codex / 新维护者的唯一实时接手入口。**
> 新窗口先读本文件，再按 `CURRENT PHASE`、`NEXT ACTION`、`MASTER ROADMAP` 连续执行。完成一个动作后必须更新本文件并自动推进到下一个未完成动作；不要依赖旧聊天解释项目状态。

## 0. 一句话接手

> **接手 `An-0726/safety-basis`，先读根目录 `AGENTS.md`，按 `CURRENT PHASE / NEXT ACTION / MASTER ROADMAP` 从当前状态继续；最终目标是数据 Gate 全绿、合并 `main`、GitHub Pages 部署成功并完成线上验收。私有母库写操作必须先备份、再验证、可回滚。**

---

## 1. ULTIMATE GOAL — 最终目标

形成一套可长期维护、可审计、可持续部署的安全隐患法规依据网站：

- 私有法规证据库职责清楚：原件、历史版本、来源副本、OCR/文本派生物、全文检索数据库分层；
- `knowledge/` 是唯一正式结构化法规/版本/条款/隐患知识源；
- 同一法规同一真实版本只有一个 canonical identity，多来源只是来源；
- 正式引用链必须满足：`隐患 → 法规身份 → 适用版本 → 具体条/款/项 → 逐字原文 → 官方/原始证据 → 适用性审核`；
- `proposed` 候选不得进入正式公共站；
- 本地私有版可从仓库 + `source/library/` 重建；
- `main` Validate / Build / Pages Deploy 全绿；
- 线上完成关键搜索、法规详情、来源链、候选隔离、历史/upcoming、桌面端/移动端抽检；
- 任意新窗口不依赖旧聊天即可继续。

### Definition of Done

只有以下全部满足，才算本轮整体整理完成：

1. 私有母库实体、重复、历史版本、派生物关系已解释；
2. 工作 SQLite 完整性正常，任何修复均有备份和变更记录；
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

当前 Git 唯一主线：`main`。

已完成公开发布架构收口：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物，不提交 Git；
- 正式站只发布 Gate 通过的已核验隐患；
- `proposed` 不进入公网；
- `upcoming` 尚未实施版本不能支撑当前正式隐患。

当前正式发布基线：

- 1,409 条正式隐患；
- 55 个实际引用法规版本；
- 1,193 条正式条款；
- 1,524 个正式关联；
- 512 条 `proposed` 候选仅留 `knowledge/`，公网候选 0。

当前 knowledge 库存：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体、1,547 个关联。

新版 Excel 目标集：1,929 个唯一隐患 ID（621 修订、1,308 保留）。它不是正式发布数量。

### 最近 Git 里程碑

- PR #29：正式/候选发布边界与 current 现场生成收口；
- PR #30：建立 `AGENTS.md` 作为仓库长期接手入口；
- PR #31：扩展为完整 MASTER ROADMAP；
- PR #32：完成 PHASE 1 私有母库审计，加入私有母库修复方案、安全维护工具和测试；
- PR #32 已 squash 合并到 `main`：`f88af76d258035350047987d2008125854728fbe`；
- 该 main 提交的 Validate safety data 与 Build current verified website / Pages 流程均已成功。

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

本地工作仓库：

`D:\ESH\ESH_Codex\work\safety-basis\`

私有法规母库：

`D:\ESH\ESH_Codex\work\safety-basis\source\library\`

Google Drive for desktop 已同步项目。Drive 关键词搜索可能漏掉 `.sqlite3` 二进制文件；应直接读取已知 `source/library` 文件夹，不可因搜索 0 条判断文件不存在。

### PHASE 1 最终只读审计

- SQLite 文件大小：106,958,848 bytes；
- `documents`：170；
- `fulltext_fts`：215,326；
- 唯一文件 SHA-256：166；
- 同一 SHA 对应多条 document：4 组，共 8 行；
- `sum(documents.paragraph_count) = count(fulltext_fts) = 215,326`；
- 每个 document 的 FTS 行数与 `paragraph_count` 一致；
- 同标题双记录共 20 组，其中 2 组是真实不同版本，其余属于同一真实版本的旧身份/再导入身份/多载体表达；
- 明确真实不同版本至少包括 `AQ 4228-2012 / AQ 4228-2025`、`GB/T 13869-2017 / GB/T 13869-2026`；
- current `archive/` 有 136 个 SHA：129 个被当前 `archive_ref` 直接引用，另 7 个是历史纯文本派生物，不是 7 部漏入全文库的法规；
- 38 行旧 `evidence/...` 引用仍存在，不可按标题猜目标文件；
- inventory：144 个原文件 / 138 个唯一 SHA / 6 个完全重复；inventory-only 文件不能批量自动导入；
- `pending-originals` 中 TSG 08-2026、TSG 92-2026 历史待 OCR 载体不能直接再次导入，须先核版本和来源关系；
- `document_id` 同时存在 `LF_*`、`LV_*`、旧 `Lxxx`、标准号等命名，不能直接当 canonical law-version 主键；
- 工作母库原始 `PRAGMA integrity_check` 报：`malformed inverted index for FTS5 table main.fulltext_fts`；
- PHASE 1 未写工作母库、未删除/移动 archive 原件。

详细规则：`docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`。

### PHASE 3 隔离副本验证（已完成，尚未覆盖工作母库）

2026-09-14 已直接从 Google Drive 当前 `fulltext.sqlite3` 本体重新取得文件，并验证其仍为 106,958,848 bytes。

在隔离环境执行：

1. 对当前云盘本体只读 audit；
2. 使用 SQLite Backup API 创建一致性 pre-rebuild 备份；
3. 从备份复制生成 repaired candidate；
4. 仅执行：`INSERT INTO fulltext_fts(fulltext_fts) VALUES('rebuild');`；
5. 对 source / backup / repaired candidate 做全量一致性对比。

验证结果：

- source：170 documents / 215,326 FTS rows / paragraph_sum 215,326；
- backup：170 / 215,326 / 215,326；
- repaired candidate：170 / 215,326 / 215,326；
- 逐 document FTS 行数不一致：三者均为 0；
- 全文内容摘要（按 `document_key, paragraph_no, content` 排序计算）三者完全相同：`264275aa1b51d8e0e54ef8fa9d58cba52aa04858ca089d13979071136c95de74`；
- source `integrity_check`：FTS5 malformed inverted index；
- repaired candidate `integrity_check`：`ok`；
- repaired candidate `foreign_key_check`：0 errors。

结论：**FTS rebuild 可以修复当前索引损坏，并保持 documents、段落数和全文内容不变。**

注意：当前真正工作母库 `source/library/fulltext.sqlite3` 尚未被本轮 PHASE 3 覆盖/替换；只有隔离副本修复成功。

---

## 5. MASTER ROADMAP

状态：`DONE` / `IN PROGRESS` / `PENDING` / `BLOCKED`。

### PHASE 0 — 架构与发布边界收口 — DONE

knowledge 主导；candidate 不发布；upcoming 不提前支撑；current 现场生成；main CI / Pages 已成功。

### PHASE 1 — 私有母库只读实体审计 — DONE

170 documents、archive、incoming、inventory、pending、knowledge 初步身份映射已完成；重复、历史版本、派生物、legacy 引用已分类。

### PHASE 2 — 母库整理方案与安全变更清单 — DONE

已完成：

- FTS 索引修复与法规身份去重分批执行；
- 4 组同 SHA 重复禁止统一直接 DELETE；
- 真实历史版本继续保留；
- 7 个 archive-only 文本派生物不作为独立法规，本轮不删；
- 旧 `evidence/...`、pending、inventory-only 处理门禁；
- 备份、前后强一致性指标和回滚条件；
- `docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`；
- `tools/v4/private_library_maintenance.py`；
- `tools/pipeline/tests/test_private_library_maintenance.py`；
- PR #32 CI 与 main CI 均通过。

### PHASE 3 — 私有母库实际修复与确定性去重 — IN PROGRESS

第一批：**FTS 修复**。

已完成：

- 当前云盘数据库重新下载并核对；
- SQLite Backup API 备份流程在隔离副本跑通；
- repaired candidate rebuild 成功；
- 强一致性指标全部通过；
- integrity 从 FTS malformed 恢复为 `ok`。

未完成：

1. 确认本机工作 `fulltext.sqlite3` 当前没有程序写入/占用；
2. 在工作母库旁创建可恢复的一致性备份；
3. 使用仓库维护工具对**工作母库**执行仅 FTS rebuild；
4. 对工作母库执行 post-audit 和搜索抽检；
5. 确认 Google Drive 同步后的本体仍通过相同指标；
6. 再进入 document alias/canonical mapping；
7. document 物理删除/合并必须作为独立后续批次，禁止与 FTS rebuild 同批。

退出条件：工作母库 `integrity_check=ok`；170 documents、215,326 rows、全文摘要保持；本地检索正常；备份可恢复；随后才评估确定性重复 document 的物理清理。

### PHASE 4 — `knowledge/` 法规身份/版本 canonical 化 — PENDING

按真实法规身份、文号、发布机关、效力时间处理。同版本多来源归一 canonical version；真实不同版本分别保留；旧 ID 保留追溯。

### PHASE 5 — 2,014 knowledge 隐患实体 ↔ 1,929 目标集对账 — PENDING

逐项解释当前正式、当前候选、历史实体、合并别名、待判断，不靠总数猜重复。

### PHASE 6 — 512 条候选法规证据回绑与转正 — PENDING

按“法规身份 → 当前适用版本 → 条/款/项 → 官方原文 → 原始证据 → 适用性审核”处理；证据不足继续 candidate。

### PHASE 7 — publication / 官方来源 / 全文资料归整 — PENDING

publication 只挂来源；正式法规数由 knowledge 决定。

### PHASE 8 — 前端与本地私有版一致性验收 — PENDING

公网只显示正式数据；本地版加载私有全文；canonical 化不得导致全文链接或 archive_ref 失联。

### PHASE 9 — 全量验证与 Release Candidate — PENDING

至少运行：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
py -3 tools/build_local_release.py
```

### PHASE 10 — 合并 main、GitHub Pages 部署、线上验收 — PENDING

工作分支 PR → CI 全绿 → 合并 main → main Validate/Build/Deploy success → 线上抽检。

### PHASE 11 — 长期维护循环 — PENDING

新法规/版本先入私有证据层，核身份/版本/效力后更新 knowledge；SQLite 定期备份/integrity；每个实质阶段更新本文件。

---

## 6. CURRENT PHASE — 当前阶段

**PHASE 3 — 私有母库实际修复与确定性去重。**

当前只允许完成第一批 FTS 修复；**不要同时删除/合并 document，不要移动 archive 原件。**

---

## 7. NEXT ACTION — 下一动作

> **先确认本机没有程序正在写 `source/library/fulltext.sqlite3`。确认后，用 `tools/v4/private_library_maintenance.py` 在工作母库旁创建一致性备份，仅执行 FTS rebuild，再执行 post-audit；必须保持 170 documents、215,326 FTS rows 和全文内容摘要不变，并得到 `integrity_check=ok`。如果无法确认本机数据库未被占用，不得远程覆盖工作本体，只保留已验证的 repaired candidate，等待安全切换。**

完成后：

1. 把工作母库实跑结果写回本文件；
2. 做中文短词、标准号、条款关键词搜索抽检；
3. 确认 Drive 同步后的本体一致；
4. 然后继续 PHASE 3 的 alias/canonical mapping；
5. document 物理删除必须另开变更批次。

---

## 8. 写操作与风险边界

低风险可自主：只读审计、生成对账报告、在副本上验证、修改 Git 代码/测试/文档（走分支/PR/CI）。

高风险必须先备份和验证：写工作 SQLite、FTS rebuild 工作母库、删除/移动 archive、合并 documents、删除 knowledge 正式实体、改稳定 ID、大批量正式条款/关联修改。

出现以下任一条件立即停止并回滚/调查：

- documents 数变化；
- FTS 行数变化；
- `sum(paragraph_count)` 与 FTS 行数不一致；
- 全文内容摘要变化；
- 任一 document FTS 行数与 `paragraph_count` 不一致；
- rebuild 后 integrity 仍非 `ok`；
- 本地全文检索明显缺失；
- 新增 archive_ref 缺失或 SHA 不一致。

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
- 不创建 `final2/latest2` 等平行最终版。

---

## 10. Git 与跨窗口维护规则

涉及代码、架构、正式数据、候选策略、发布规则或接手状态：

1. 从最新 `main` 建分支；
2. 修改；
3. 跑测试/Gate/构建；
4. 开 PR；
5. CI 全绿再合并 `main`；
6. main Pages 成功后才算公开站变更完成。

每个实质阶段结束前必须更新：

- `LAST VERIFIED`；
- MASTER ROADMAP phase 状态；
- 当前已核事实；
- `CURRENT PHASE`；
- `NEXT ACTION`；
- 架构/口径变化同步 README；
- 人类交接发生重大变化同步 `docs/HANDOFF.md`。

`NEXT ACTION` 只是光标，`MASTER ROADMAP` 才是总任务。完成一个 NEXT ACTION 后不要停，除非遇到高风险写操作需要确认、本地进程状态无法验证、缺失证据或外部阻塞。