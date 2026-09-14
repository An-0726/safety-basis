# AGENTS.md — 仓库长期接手记忆与总施工计划

> **这是 AI / Codex / 新维护者的唯一实时接手入口。**
> 新窗口必须先读本文件，再读根目录 `AGENT_EXECUTION_PROTOCOL.md`，然后按 `CURRENT PHASE / NEXT ACTION / MASTER ROADMAP` 连续执行。完成一个动作后必须更新本文件并自动推进，不依赖旧聊天解释项目状态。

## 0. 一句话接手

> **接手 `An-0726/safety-basis`。先读 `AGENTS.md` 和 `AGENT_EXECUTION_PROTOCOL.md`；总控负责法规核验、隐患描述、证据链、knowledge/canonical、candidate、发布与上线判断；只有必须操作用户本机且当前工具做不到的步骤，才生成严格提示词交给本地 Luna 执行，回传后由总控复核。最终目标是数据 Gate 全绿、合并 `main`、GitHub Pages 部署成功并完成线上验收。**

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

当前 Git 唯一正式主线：`main`。

公开发布架构已收口：

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
- PR #34：新增 `AGENT_EXECUTION_PROTOCOL.md`，固化“总控判断、本地 Luna 只执行本机操作”的协作边界；
- PR #32 合并后 main 的 Validate / Build / Pages 已成功；PR #34 合并提交为 `55c641ee99eb2b1691f92b2fbe3c5a363831cb28`。

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

Google Drive for desktop 已同步项目。Drive 关键词搜索可能漏掉 `.sqlite3` 二进制文件；应直接读取已知 `source/library` 文件夹，不可因搜索 0 条判断不存在。

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
- `document_id` 同时存在 `LF_*`、`LV_*`、旧 `Lxxx`、标准号等命名，不能直接当 canonical law-version 主键。

详细规则：`docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`。

### PHASE 3 第一批：工作母库 FTS5 修复 — 本机 PASS，云盘已同步

本地 Luna 按总控提示词在实际工作库执行，未切分支、未 pull、未清理 worktree、未删除法规原件。

本机修复前：

- documents = 170；
- ftsRows = 215,326；
- paragraphCountSum = 215,326；
- foreignKeyErrors = 0；
- perDocumentParagraphMismatches = []；
- `ftsContentSha256 = 1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd`；
- `databaseFileSha256 = 0b76727d771c14acaa71d329a65c76518b0226be5e8ef81e7201e574bdce04ab`；
- **本机运行时修复前 `integrity=["ok"]`**。

本机创建的一致性备份：

`D:\ESH\ESH_Codex\work\safety-basis\source\library\backups\fulltext.sqlite3.bak-20260914-155510+0800`

本机仅执行 FTS rebuild 后：

- documents = 170；
- ftsRows = 215,326；
- paragraphCountSum = 215,326；
- foreignKeyErrors = 0；
- perDocumentParagraphMismatches = []；
- `ftsContentSha256` 与修复前完全相同：`1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd`；
- `databaseFileSha256 = 7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`；
- `integrity=["ok"]`；
- `invariantErrors=[]`；
- `manualRestoreRequired=false`；
- documents 未修改，法规原件未删除，不需要回滚。

本机搜索抽检：

- `洗眼器`：15 条；
- `危险化学品`：13,864 条；
- `GB 55036`：707 条。

总控已从 Google Drive 重新下载同一 `fulltext.sqlite3` 独立复核：

- Drive 文件修改时间已更新为 2026-09-14 07:55:35Z；
- 大小仍为 106,958,848 bytes；
- 文件 SHA-256 **与本机修复后完全一致**：`7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`；
- documents = 170；ftsRows = 215,326；paragraphCountSum = 215,326；逐 document mismatch = 0；foreign key errors = 0；
- `ftsContentSha256` **与本机报告完全一致**：`1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd`；
- 总控环境查询同样得到 `洗眼器=15`、`危险化学品=13,864`、`GB 55036=707`。

#### 重要兼容性备注：FTS5 integrity_check 存在运行时差异

总控当前 Linux/Python 环境使用 SQLite **3.46.1**。对云盘中与本机修复后 SHA 完全相同的数据库，`PRAGMA integrity_check` 仍返回：

`malformed inverted index for FTS5 table main.fulltext_fts`

而本机 Luna 对修复前和修复后数据库均返回 `integrity=["ok"]`。由于**同一字节文件**在两个 SQLite 运行时得到不同 integrity 结果，同时行数、全文摘要、外键和实际 FTS 查询结果全部一致，因此目前将其记录为 **SQLite/FTS5 运行时兼容性差异待解释**，不能据此判断正文或云盘文件损坏。

后续若再次做 FTS 维护，应先记录本机 `sqlite3.sqlite_version`，并优先以项目实际本机运行时 + 内容不变量 + 搜索抽检联合验收；不要仅凭不同运行时的一次 `PRAGMA integrity_check` 自动覆盖数据库。

### PHASE 3 第二批：170 documents canonical / alias 只读映射 — 总控 PASS

完整映射见 `docs/PRIVATE_LIBRARY_DOCUMENT_MAPPING_20260914.md`。本批未写 SQLite、未删 document/FTS、未移动 archive、未改稳定 ID。

已核结论：

- 4 组 exact-SHA 中，`GB/T 12801-2008` 与 `GB 55036-2022` 同时满足 raw SHA 与 extracted-text SHA 相同，可列为后续“确定性重复”候选；
- `HJ 2025-2012` 与 `GB 15603-2022` 虽 raw SHA 相同，但历史 extracted-text SHA / paragraph count 不同，只做 alias，不得直接物理删旧 FTS；
- 18 组同真实版本双身份已经全部归类：12 组已对齐现有 `knowledge` canonical，6 组确认是当前 `knowledge` canonical gap；
- 6 个 canonical gap 的法规身份和效力已由总控回到官方来源核验，其中 `危险化学品目录（2015版）` 还必须在 PHASE 4 显式表达 2022 柴油调整和 2026 新增 5 种化学品，不能把 2015 静态原文直接冒充 2026-09-14 的完整现行目录；
- 2 组同标题真实不同版本明确禁止合并：`AQ 4228-2012 / AQ 4228-2025`、`GB/T 13869-2017 / GB/T 13869-2026`；
- 38 条 legacy `evidence/...` 中只有 `LF_L027 / HJ 2025-2012` 的 raw SHA 在 current `archive/` 有完全相同目标，可安全重绑 `archive/0a78de.../original`；其余 37 条没有同 SHA current archive 目标，继续保留 legacy provenance，禁止按标题猜路径；
- 7 个 archive-only 历史纯文本派生物继续只作为派生载体，不生成独立法规身份。

本批已经满足 PHASE 3 的 mapping 与回滚前置要求。**不需要为了结束 PHASE 3 立即做 document 物理 DELETE。**后续若要压缩 SQLite，只允许另开独立高风险批次，并先做一致性备份、引用扫描、搜索不变量与回滚验证。

---

## 5. MASTER ROADMAP

状态：`DONE` / `IN PROGRESS` / `PENDING` / `BLOCKED`。

### PHASE 0 — 架构与发布边界收口 — DONE

knowledge 主导；candidate 不发布；upcoming 不提前支撑；current 现场生成；main CI / Pages 已成功。

### PHASE 1 — 私有母库只读实体审计 — DONE

170 documents、archive、incoming、inventory、pending、knowledge 初步身份映射已完成；重复、历史版本、派生物、legacy 引用已分类。

### PHASE 2 — 母库整理方案与安全变更清单 — DONE

FTS 修复与身份归并分批、备份/回滚门禁、私有母库维护脚本和测试已建立，PR #32 已合并并通过 CI。

### PHASE 3 — 私有母库实际修复与确定性去重 — DONE

FTS rebuild 已由本机执行并由总控以云盘同字节文件独立复核；170 documents 的 exact-SHA、same-real-version alias、真实不同版本、knowledge gaps、38 条 legacy `evidence/...` 迁移矩阵已经完成并落入 `docs/PRIVATE_LIBRARY_DOCUMENT_MAPPING_20260914.md`。

当前选择是**先不做物理 DELETE / archive 移动**：身份层已经可确定性解释，物理压缩不是进入 PHASE 4 的前置条件。任何后续 SQLite 物理去重仍须另开高风险批次。

### PHASE 4 — `knowledge/` 法规身份/版本 canonical 化 — IN PROGRESS

按真实法规身份、文号、发布机关、效力时间处理。同版本多来源归一 canonical version；真实不同版本分别保留；旧 ID 保留追溯。

当前优先补齐 PHASE 3 已确认的 6 个 canonical gaps，并先处理 `危险化学品目录（2015版）` 的 2015 base + 2022/2026 调整关系，避免把历史静态文本误标为当前完整版本。

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

**PHASE 4 — `knowledge/` 法规身份/版本 canonical 化。**

PHASE 3 的只读 document mapping 已闭环；当前不需要 Luna。总控直接继续做法规身份、版本、修订/替代关系、官方来源与 `knowledge` canonical 设计。

---

## 7. NEXT ACTION — 下一动作

> **总控先补齐 PHASE 3 确认的 6 个 `knowledge` canonical gaps：`危险化学品目录（2015版）`、`各类监控化学品名录`、`GB 17914-2013`、`GB 17915-2013`、`GB 17916-2013`、`特种设备安全监察条例（2009修订）`。逐个先查重现有 `knowledge`，再按现有 schema 建/复用 law identity、law version、官方 source/evidence 与必要 succession；其中危险化学品目录必须按 2015 base + 2022/2026 调整建模。完成后运行 knowledge/全量 Gate，并把 6 个 private alias group 回填到正式 canonical ID。暂不做 SQLite 物理 DELETE，不动 candidate 发布边界。**

执行顺序：

1. 逐项扫描现有 `knowledge/laws`、`law-versions`、`evidence`、`successions`，确认无同一真实版本的隐藏重复；
2. 先建 5 个直接 canonical gap（监控化学品名录、GB 17914/17915/17916、特种设备安全监察条例）；
3. 单独设计并核验 `危险化学品目录（2015版）` 的修订链，至少覆盖 2015年第5号、2022年第8号、2026年第3号；
4. 回填/更新 private alias mapping 的 canonicalVersionId，仅在 identity 确认后写；
5. 运行 validators / strict audit / relevant unit tests；
6. 更新本文件并自动推进到 PHASE 5，除非 Gate、证据或版本关系出现阻塞。

---

## 8. 写操作与风险边界

低风险可自主：法规核验、隐患描述、证据链分析、只读审计、生成 mapping/对账报告、在副本上验证、修改 Git 代码/测试/文档（走分支/PR/CI）。

高风险必须先备份和验证：写工作 SQLite、删除/移动 archive、合并 documents、删除 knowledge 正式实体、改稳定 ID、大批量正式条款/关联修改。

出现以下任一条件立即停止并回滚/调查：

- documents 数意外变化；
- FTS 行数或 paragraphCountSum 意外变化；
- 全文内容摘要变化；
- 任一 document FTS 行数与 `paragraph_count` 不一致；
- 本地全文检索明显缺失；
- archive_ref 缺失或 SHA 不一致；
- canonical 合并会丢失法规版本、来源或证据链。

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