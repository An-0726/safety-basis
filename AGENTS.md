# AGENTS.md — 仓库长期接手记忆与总施工计划

> **这是 AI / Codex / 新维护者的唯一实时接手入口。**
> 新窗口先读本文件，再按 `CURRENT PHASE`、`NEXT ACTION` 和 `MASTER ROADMAP` 连续执行；做完一个动作后自动推进，不要停下来等用户重新解释。

## 0. 一句话接手

> **接手 `An-0726/safety-basis`，先读根目录 `AGENTS.md`，按 `CURRENT PHASE / NEXT ACTION / MASTER ROADMAP` 从当前状态继续；最终目标是通过 Gate、合并 main、GitHub Pages 部署并完成线上验收。没有备份和安全方案前不要写私有母库。**

---

## 1. ULTIMATE GOAL — 最终目标

形成一套可长期维护、可审计、可持续部署的安全隐患法规依据网站：

- 私有法规证据库清楚，原件、历史版本、来源副本、OCR/文本派生物、全文检索数据库职责分开；
- `knowledge/` 是唯一正式结构化法规/条款/隐患知识源；
- 同一法规同一真实版本只保留一个 canonical identity，多来源只作为来源；
- 正式引用链必须满足：`隐患 → 法规身份 → 适用版本 → 具体条/款/项 → 逐字原文 → 官方/原始证据 → 适用性审核`；
- `proposed` 候选不进入正式公共站；
- 本地私有版可从仓库 + `source/library/` 重建；
- `main` Validate / Build / Pages Deploy 全绿；
- 线上完成关键搜索、法规详情、来源链、候选隔离、移动端/桌面端抽检；
- 任意新窗口不依赖旧聊天即可继续。

---

## 2. 当前正式基线

**LAST VERIFIED：2026-09-14**

当前 Git 唯一主线：`main`。

已完成的公开发布架构收口：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物，不提交 Git；
- 正式站只发布 Gate 通过的已核验隐患；
- `proposed` 不进入公网；
- `upcoming` 尚未实施版本不能支撑当前正式隐患；
- main 的数据校验、正式站 build 和 Pages deploy 已成功。

当前正式发布基线：

- 1,409 条正式隐患；
- 55 个实际引用法规版本；
- 1,193 条正式条款；
- 1,524 个正式关联；
- 512 条 `proposed` 候选仅留 `knowledge/`，公网候选 0。

当前 knowledge 库存：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体、1,547 个关联。

新版 Excel 目标集是 1,929 个唯一隐患 ID（621 修订、1,308 保留），它不是正式发布数量。

---

## 3. 权威层级与硬规则

### 法规事实

正式法规事实必须回到官方原文/原始证据和 `knowledge/`；AI 摘要、搜索摘要、OCR、TXT、HTML、Excel“条款要点”只能用于定位，不能作为正式法规原文。

找不到准确法规原文或条款时标记“待核实 / 证据不足”，不得编造。

“最新发布”不等于“当前适用”。真实不同版本分别保留；尚未实施版本不得提前作为当前依据。

### 项目数据

- `knowledge/`：正式结构化法规身份、版本、条款、隐患、关联、审核；
- `source/library/archive/`：私有证据归档，默认不可变；
- `source/library/fulltext.sqlite3`：私有全文检索数据库，可维护索引，但不是最高法律证据；
- `source/library/incoming-*`：收件/暂存；
- `source/publication/`：公开来源资料层；
- `source/releases/current/`、`dist/`、网页索引：可重建成品，不得反向当母库。

禁止为了界面整洁重编号 `LF_* / LV_* / C_* / H_*` 稳定 ID；需要归并时优先 alias / canonical mapping。

---

## 4. 私有母库当前已核事实

本地工作仓库：

`D:\ESH\ESH_Codex\work\safety-basis\`

私有法规母库：

`D:\ESH\ESH_Codex\work\safety-basis\source\library\`

Google Drive for desktop 已同步项目。Drive 关键词搜索可能漏掉二进制 `.sqlite3`；不能用“搜索 0 条”判断不存在，应直接读取已知 `source/library` 文件夹。

`source/library/` 已确认包含：

- `fulltext.sqlite3`；
- `archive/`；
- `incoming-20260910/`；
- `incoming-20260913/`；
- `inventory/`；
- `pending-originals/`；
- `pending-originals.json`。

### PHASE 1 最终只读审计结果

- SQLite 大小：106,958,848 bytes；
- `documents`：170；
- `fulltext_fts`：215,326；
- 唯一文件 SHA-256：166；
- 同一 SHA 对应多条 document：4 组，共 8 行；
- `sum(documents.paragraph_count) = count(fulltext_fts) = 215,326`；
- 每个 document 的 FTS 行数都与 `paragraph_count` 一致；
- 同标题双记录共 20 组，其中 2 组是真实不同版本，其余属于同一真实版本的旧身份/再导入身份/多载体表达；
- 明确真实不同版本至少包括：`AQ 4228-2012 / AQ 4228-2025`、`GB/T 13869-2017 / GB/T 13869-2026`；
- current `archive/` 有 136 个 SHA：129 个被当前 `archive_ref` 直接引用，另 7 个是 2026-09-11 已存在的历史纯文本派生物，不是 7 部漏入全文库的法规；
- 38 行旧 `evidence/...` 引用仍存在，不能按标题猜目标文件；
- inventory 记录 144 个原文件 / 138 个唯一 SHA / 6 个完全重复；inventory-only 文件不能批量自动导入；
- `pending-originals` 中 TSG 08-2026、TSG 92-2026 的历史待 OCR 载体不能直接再次导入，须先核版本和来源关系；
- `document_id` 同时存在 `LF_*`、`LV_*`、旧 `Lxxx`、标准号等命名，不能直接当 canonical law-version 主键；
- `PRAGMA integrity_check` 当前报：`malformed inverted index for FTS5 table main.fulltext_fts`；
- 已在**副本**上测试 FTS rebuild，可把 integrity 恢复为 `ok`，且 170 documents、215,326 段及全文内容摘要不变；
- PHASE 1 全程**未写工作母库、未 rebuild 工作 FTS、未删除/移动 archive 原件**。

详细安全处理规则：`docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`。

---

## 5. MASTER ROADMAP

状态约定：`DONE` 已完成并验证；`IN PROGRESS` 当前阶段；`PENDING` 未开始；`BLOCKED` 有明确阻塞。

### PHASE 0 — 架构与发布边界收口 — DONE

公开站已收口为 knowledge 主导、候选不发布、upcoming 不提前支撑、current 现场生成，main CI / Pages 已成功。

### PHASE 1 — 私有母库只读实体审计 — DONE

已完成 170 documents、archive、incoming、inventory、pending、knowledge 初步身份映射；重复、真实历史版本、派生物、legacy 引用均已分类。工作母库未发生写操作。

### PHASE 2 — 母库整理方案与安全变更清单 — IN PROGRESS

已完成：

- 明确 **FTS 索引修复** 与 **法规身份去重** 必须分批执行；
- 明确 4 组同 SHA 重复不能统一“直接 DELETE”；
- 明确真实历史版本继续保留；
- 明确 7 个 archive-only 文本派生物不作为独立法规，也不在本轮删除；
- 明确旧 `evidence/...`、pending、inventory-only 的处理门禁；
- 明确备份、前后强一致性指标、回滚条件；
- 已新增 `docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`；
- 已新增 `tools/v4/private_library_maintenance.py`；
- 已新增 `tools/pipeline/tests/test_private_library_maintenance.py`；
- 合成库已验证 `audit → SQLite Backup API → FTS rebuild → post-audit` 流程成功。

当前只差：

1. GitHub CI 对新工具/测试独立验证；
2. CI 全绿后将 PHASE 2 标记 `DONE`；
3. 再进入 PHASE 3，在**本机工作母库**上先做一致性备份，再执行“仅 FTS rebuild”。

### PHASE 3 — 私有母库实际修复与确定性去重 — PENDING

第一批只允许：备份 → audit → FTS rebuild → audit → 搜索抽检。

**不得把 document 合并/删除与 FTS rebuild 放在同一批次。**

FTS 修复稳定后，再做 alias/canonical mapping；只有文本完全相同、引用已核清的重复 document 才能进入后续物理删除评估。

退出条件：SQLite integrity `ok`；documents/paragraphs/全文内容摘要变化有完整解释；原始证据可追溯；本地检索正常。

### PHASE 4 — `knowledge/` 法规身份/版本 canonical 化 — PENDING

检查法规身份、真实版本、文号、发布机关、效力时间；同版本多来源归一个 canonical version，真实不同版本分别保留；旧 ID 保留追溯。

### PHASE 5 — 2,014 knowledge 隐患实体 ↔ 1,929 目标集全量对账 — PENDING

逐项解释当前正式、当前候选、历史实体、合并别名、待判断，不靠总数猜重复。

### PHASE 6 — 512 条候选法规证据回绑与转正 — PENDING

按“法规身份 → 当前适用版本 → 条/款/项 → 官方原文 → 原始证据 → 适用性审核”处理。证据不足继续保留 candidate，不能为了清零编造。

### PHASE 7 — publication / 官方来源 / 全文资料归整 — PENDING

publication 只挂来源；正式法规数由 knowledge 决定。

### PHASE 8 — 前端与本地私有版一致性验收 — PENDING

公网只显示正式数据；本地版能加载私有全文；canonical 化不能导致全文链接或 archive_ref 失联。

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

退出条件：所有 blocker 为 0，测试全绿，本地版构建成功，数字与文档一致。

### PHASE 10 — 合并 main、GitHub Pages 部署、线上验收 — PENDING

工作分支 PR → CI 全绿 → 合并 main → main Validate/Build/Deploy success → 线上抽检关键搜索、法规详情、来源链、候选隔离、历史/upcoming 场景、桌面/移动端。

### PHASE 11 — 长期维护循环 — PENDING

新法规/版本先入私有证据层，再核身份/版本/效力，更新 knowledge，过 Gate 后部署；SQLite 定期备份和 integrity 检查；每次实质阶段更新本文件。

---

## 6. CURRENT PHASE — 当前阶段

**PHASE 2 — 母库整理方案与安全变更清单。**

PHASE 1 已完成。当前不要写工作母库；先让安全维护工具通过仓库 CI。

---

## 7. NEXT ACTION — 下一动作

> **检查工作分支 `phase1-audit-progress-20260914` 中 `docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`、`tools/v4/private_library_maintenance.py`、`tools/pipeline/tests/test_private_library_maintenance.py`，开 PR 跑 CI；CI 全绿后把 PHASE 2 标记 DONE，并进入 PHASE 3。PHASE 3 第一批只做工作母库一致性备份 + FTS rebuild + 强一致性审计，不合并或删除任何 document。**

完成 NEXT ACTION 后不要停：更新本文件，推进到下一个未完成阶段。

---

## 8. PHASE 3 第一批写操作安全门槛

在工作 `fulltext.sqlite3` 上执行任何写入前必须满足：

- 没有其他进程正在写数据库；
- 先运行只读 audit；
- 使用 SQLite Backup API 创建一致性备份；
- 记录变更前 documents、FTS 行数、paragraph_count 总和、逐 document 行数、全文内容 SHA-256；
- rebuild 后必须 `integrity_check = ok`；
- documents、FTS 行数、paragraph_count、逐 document 行数、全文内容 SHA-256 均不得变化；
- 搜索抽检通过；
- 任一强一致性指标变化立即停止并回滚；
- document 物理合并/删除必须另开独立阶段。

---

## 9. 绝对禁止事项

- 不把私有 PDF、SQLite、OCR、企业资料提交 GitHub；
- 不直接编辑生成的 `source/releases/current/`；
- 不按标题相似直接删除法规或隐患；
- 不把同名不同真实版本合并；
- 不把 publication 多来源当多个法规身份；
- 不把 upcoming 版本作为当前正式依据；
- 不把 OCR/TXT/HTML/Excel 摘要当正式法规原文；
- 不先修/删工作母库再补备份；
- 不为了候选清零而捏造依据；
- 不新增 `final2`、`latest2`、日期版 handoff、平行 current 等第二套“最终版”。

---

## 10. Git 修改流程

代码、架构、正式数据、发布规则、长期记忆变化：

1. 从最新 `main` 建工作分支；
2. 修改；
3. 跑测试/Gate/构建验证；
4. 开 PR；
5. CI 全绿后合并 `main`；
6. main Pages build/deploy 成功后才算公开变更完成。

私有母库本身不提交 Git，但私有维护结果、规则、下一步必须写回 `AGENTS.md`；架构/口径变化同步 README/HANDOFF。

---

## 11. 每次会话结束前必须更新

- `LAST VERIFIED`；
- MASTER ROADMAP 的 PHASE 状态；
- 当前已核事实；
- `CURRENT PHASE`；
- `NEXT ACTION`；
- 架构/数据口径变化时同步 README；
- 人类交接状态重大变化时同步 `docs/HANDOFF.md`；
- 不新增平行“最终版”文档，历史交给 Git。
