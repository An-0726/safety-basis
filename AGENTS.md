# AGENTS.md — PHASE 5 转手入口（2026-09-14）

> **这是本次转手专用入口。** 新总控先读完本文件，再读取远端 `main` 根目录的 `AGENT_EXECUTION_PROTOCOL.md`。不要依赖旧聊天，不要让本地 Luna 自行判断法规、隐患、canonical、candidate、发布或上线。

## 0. 一句话接手

> **接手 `An-0726/safety-basis`。当前正式主线是远端 `main`，PR #36 已合并；PHASE 0–4 已收口，正在做 PHASE 5：把新版 Excel 的 1,929 个唯一隐患 ID 与 `knowledge/hazards` 的 2,014 个实体做逐 ID 可复算对账。总控负责法规核验、隐患描述、证据链、knowledge/canonical、candidate、发布和上线判断；只有必须操作用户本机且当前工具做不到的步骤，才给 Luna 严格执行提示词。**

---

## 1. 转手时必须先纠正的 Git 状态

本 `agent-memory-handoff-20260914` 分支只是**转手记忆分支**，不是继续开发的代码基线。它历史上从较早提交分叉，不能拿它覆盖当前 `main`。

当前远端正式主线已核到：

- repository：`An-0726/safety-basis`
- default branch：`main`
- `main` 当前已包含 PR #36 的 merge commit：`0118a13a307309fcaf3a79ebf09475863774bf72`
- PR #36：`Phase 4: canonicalize private-library law gaps`
- PR #36 merged at：`2026-09-14T08:49:40Z`

**新总控开始实质工作前：**

1. 以远端 `main` 为代码/knowledge 唯一正式基线；
2. 读取 `main:AGENTS.md` 与 `main:AGENT_EXECUTION_PROTOCOL.md`；
3. 从最新 `main` 新建 PHASE 5 工作分支；
4. 不要把本 handoff 分支中较旧的 README/HANDOFF 内容反向覆盖 main。

如果本地 checkout 仍停在 `data-verify-batch-003`、`chat-v4` 或其他旧分支，先 fetch 远端并确认 `origin/main`，不要凭本地旧文件判断项目状态。

---

## 2. 总控 / Luna 边界

固定协作模式：

`总控判断与拆解 → 仅在必须本机操作时给 Luna 严格提示词 → Luna 执行 → 总控复核 → 更新 AGENTS.md → 推进 ROADMAP`

### 必须由总控完成

- 法规真实性、效力状态、发布/实施/废止日期核验；
- 官方原文、具体条/款/项和证据链核验；
- 隐患描述修订、风险含义、法规适用性；
- Excel 正式口径与 knowledge 回绑；
- law / lawVersion / clause / hazard / link canonical 设计；
- 同法规同版本去重、真实历史版本区分、alias 策略；
- candidate 是否转正；
- publication / Gate / Release Candidate / Pages 上线判断；
- PR 是否可合并、CI/Pages 是否最终 PASS；
- `AGENTS.md` 的 CURRENT PHASE / NEXT ACTION / ROADMAP 推进。

### Luna 只允许做

仅限当前工具无法完成、必须操作用户本机的动作，例如 Windows 本地 Git/worktree、文件锁、私有 SQLite 写入、本机脚本/构建、同步客户端状态等。Luna 不得自行决定删除/合并 document、法规版本、稳定 ID、隐患描述、正式法规依据或发布策略。

---

## 3. 已完成且不得倒退的阶段

### PHASE 0 — 发布边界收口 — DONE

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只是公开题录/官方入口/获准全文来源层；
- `source/library/` 是本地私有证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物；
- `proposed` 不进入公网；
- `upcoming` 未实施版本不得支撑当前正式隐患。

### PHASE 1 — 私有母库审计 — DONE

已核基线：

- `documents=170`
- `fulltext_fts=215,326`
- `documents` 唯一文件 SHA-256 = 166
- 4 组同一 SHA 双登记
- 同标题双记录 20 组，其中 2 组是真实不同版本
- inventory：144 原文件 / 138 唯一 SHA / 6 完全重复
- 38 条 legacy `evidence/...` 不得按标题猜迁移目标

### PHASE 3 — FTS 修复与 document mapping — DONE

FTS 本机修复已 PASS，且总控独立复核内容不变量：

- documents = 170
- ftsRows = 215,326
- paragraphCountSum = 215,326
- FK errors = 0
- mismatch = 0
- `ftsContentSha256=1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd`
- repaired DB SHA-256 = `7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`
- 项目实际本机运行时 `integrity=["ok"]`

170 documents mapping 已完成：

- `GB/T 12801-2008`、`GB 55036-2022`：raw SHA + extracted-text SHA 均相同，未来可列独立高风险物理去重候选；
- `HJ 2025-2012`、`GB 15603-2022`：raw SHA 相同但历史抽取不同，只做 alias，不能直接删旧 FTS；
- 18 组同真实版本双身份已分类；
- 2 组真实不同版本禁止合并：`AQ 4228-2012 / AQ 4228-2025`、`GB/T 13869-2017 / GB/T 13869-2026`；
- 38 条 legacy 引用里仅 `HJ 2025-2012` 有同 SHA current archive 目标，其余继续保留 provenance；
- 当前没有做 document 物理 DELETE / archive 移动。

### PHASE 4 — 六个 canonical gaps — DONE

PR #36 已合并到 main。新增并核验：

- `危险化学品目录（2015版）`：同一 law identity 下建 2015 base → 2023 柴油调整后 → 2026 新增 5 种化学品后三个版本状态；
- `各类监控化学品名录`（工业和信息化部令第52号）；
- `GB 17914-2013`；
- `GB 17915-2013`；
- `GB 17916-2013`；
- `特种设备安全监察条例（2009修订）`。

新增合计：6 laws、8 lawVersions、8 authoritative evidence、6 law reviews、8 lawVersion reviews、2 successions。

PHASE 4 后 manifest 已记录：

- 102 laws
- 105 lawVersions
- 2,843 clauses
- 2,014 hazards
- 1,547 links
- 1,114 evidence
- 28 successions
- 75 requirements

private `source/library/document-aliases.json` 已回填 6 个 `canonicalVersionId`，`knowledgeUnmappedTitles=[]`；未写 SQLite/FTS/archive。

PR #36 合并前核心 CI：

- `Validate safety data` — success
- `Build current verified website` — success

---

## 4. CURRENT PHASE — PHASE 5 隐患 1,929 ↔ 2,014 对账 — IN PROGRESS

### 已核目标集

目标工作簿：

`隐患库_1929条_新版口径全部整改完成_20260914.xlsx`

已确认其 `隐患明细_修订后` 为正式对账目标表：

- 1,929 行隐患数据；
- 1,929 个唯一 ID；
- 重复 ID = 0；
- 621 修订；
- 1,308 保留；
- 说明页口径：已合并（superseded）及未达发布标准条目不导出，因此 **1,929 是目标集，不等于当前正式发布数**。

knowledge 当前有 **2,014 个 hazard 实体**。

### 重要未决点：84 / 85 不得猜

历史回灌记录曾写“额外保留 84”，但单纯数量差是：

`2,014 - 1,929 = 85`

因此旧“84”只能视为待核历史统计，**不得直接继承**。必须用实际 ID 集合重新计算：

- `target_only = ExcelIDs - KnowledgeIDs`
- `knowledge_only = KnowledgeIDs - ExcelIDs`
- `intersection = ExcelIDs ∩ KnowledgeIDs`

只有集合结果出来后，才能解释 84/85 的差异；不得先假设 1,929 一定是 2,014 的真子集。

### 前一窗口做到哪里

已经：

- 定位并读取了 1,929 工作簿；
- 确认目标 sheet 和 1,929 唯一 ID；
- 定位了 GitHub `knowledge/hazards` 子树，确认库存为 2,014；
- 尝试从 GitHub connector 的超长 tree JSON 全量抽文件名，但返回体过长/截断，不适合继续靠逐行远程解析。

**尚未完成：**

- 2,014 个实际 hazard ID 的完整集合抽取；
- 精确 `target_only / knowledge_only / intersection`；
- 差异项逐 ID lifecycle / alias / mergedInto / Gate / candidate 分类；
- PHASE 5 对账报告；
- 任何针对差异项的正式 knowledge 修改。

所以当前不能声称“85 条已经解释”，也不能按旧汇总直接改数据。

---

## 5. NEXT ACTION — 新总控从这里直接继续

### A. 先做纯集合对账，不改数据

从最新 `main` 工作树直接枚举：

`knowledge/hazards/*.json`

用文件名/JSON `id` 形成 2,014 个 `KnowledgeIDs`。同时读取目标工作簿 `隐患明细_修订后` 的 ID 列形成 `ExcelIDs`。

优先在可完整访问仓库文件的环境用脚本一次性计算，不要再通过超长 GitHub tree 响应逐项人工截取。若当前总控环境拿不到本机工作簿文件，才给 Luna 一条严格的“只读导出 ID 列”提示词；Luna 不做分类判断。

第一批输出必须至少包含：

1. `len(ExcelIDs)`、`len(KnowledgeIDs)`、各自重复数；
2. `target_only` 精确 ID 列表；
3. `knowledge_only` 精确 ID 列表；
4. `intersection` 数量；
5. 是否满足 `ExcelIDs ⊆ KnowledgeIDs`；
6. 对任何 ID 格式异常/空值单列。

### B. 只深读差异项

集合锁定后，只读取 `target_only + knowledge_only` 以及必要的 alias/mergedInto/review/link/candidate 记录。每个差异 ID 必须分到明确类别，例如：

- active 且应在目标集；
- proposed / 未达发布 Gate；
- superseded / mergedInto；
- 历史 alias；
- Excel 修订后新 ID；
- knowledge 保留的历史实体；
- 真正缺失/错误；
- 仍需人工核验。

不得因为标题相似或描述相近自动合并稳定 `H_*` ID。

### C. 生成 PHASE 5 可复算报告

建议新增：

`docs/PHASE5_HAZARD_RECONCILIATION_20260914.md`

报告必须能让下一窗口复算，至少记录：

- 输入文件与基线 commit；
- ID 提取规则；
- 三个集合的数量与差异 ID；
- 每个差异项分类、原因、关联证据；
- 哪些只是状态解释，哪些需要后续写操作；
- 对旧“84”统计的最终解释；
- 不得发布的 proposed / superseded 边界。

在报告完成并由总控验收前，**不要批量修改 hazards / links / candidate / publication**。

---

## 6. PHASE 5 EXIT CRITERIA

PHASE 5 只有以下全部满足才算 DONE：

1. 1,929 个目标 ID 全部有唯一明确去向；
2. 2,014 knowledge hazards 与目标集差异全部逐 ID 解释；
3. 旧“84 vs 85”统计矛盾被实际集合数据解释；
4. superseded / mergedInto / alias / proposed / active 不混淆；
5. 不为追求数量一致而删除历史实体或重编号稳定 ID；
6. 若需要修正式数据，先形成最小修改批次并经过 Gate；
7. `proposed` 仍不得进入正式公网；
8. 对账报告进入 Git 分支，并更新主线 `AGENTS.md` 的 CURRENT PHASE / NEXT ACTION。

---

## 7. 后续 MASTER ROADMAP

- **PHASE 0** — 架构与发布边界：DONE
- **PHASE 1** — 私有母库实体审计：DONE
- **PHASE 2** — 私有母库关系/修复准备：DONE
- **PHASE 3** — FTS 修复 + 170 documents canonical/alias mapping：DONE
- **PHASE 4** — private canonical gaps → knowledge：DONE
- **PHASE 5** — 1,929 target hazards ↔ 2,014 knowledge hazards：IN PROGRESS
- **PHASE 6** — 差异项对应的 evidence / clause / link / candidate 修复与 Gate：PENDING
- **PHASE 7** — publication/current 私有重建、正式 Release Candidate 全量验收：PENDING
- **PHASE 8** — PR 合并 main、GitHub Actions / Pages deploy、线上桌面/移动端抽检：PENDING
- **PHASE 9** — README / HANDOFF / AGENTS 最终一致性收口：PENDING

---

## 8. 不可违反的硬规则

- 法规事实必须回到官方原文/原始证据；AI 摘要、搜索摘要、OCR、Excel 摘要只用于定位；
- 找不到准确原文或条款时写“待核实 / 证据不足”，不得编造；
- “最新发布”不等于“当前适用”；历史与 upcoming 版本分别建模；
- `knowledge/` 是正式结构化知识源；网页、Excel、OCR、旧发布包不得反向覆盖；
- 不把私有 PDF、SQLite、OCR、企业资料提交 GitHub；
- 不直接编辑 `source/releases/current/` 或把生成包当母库；
- 不重编号 `LF_* / LV_* / C_* / H_*` 稳定 ID；
- 不按标题相似删除/合并法规或隐患；
- 不把同名不同真实版本合并；
- 不把 upcoming 作为当前正式依据；
- 不为了“清零 candidate”生成或臆造证据；
- 不在未完成只读对账前批量改 2,014 hazard 实体；
- 私有 SQLite 任何写操作必须先有备份、允许动作清单、停止条件和验收标准。

---

## 9. Git 工作方式

PHASE 5 实质改动必须从**最新远端 main**建新分支，不从本 handoff 分支继续开发。

推荐流程：

`fetch origin/main → 新建 phase5 工作分支 → 只读对账 → 写报告 → 总控验收 → 必要的数据最小修复 → tests/Gate/build → PR → CI 全绿 → merge main → Pages deploy/线上验收`

本 handoff 分支仅用于帮助旧本地 checkout 找到当前接手状态。

---

## 10. LAST VERIFIED

`2026-09-14 18:25 +08:00`

远端已确认事实：PR #36 已 merged，merge commit 为 `0118a13a307309fcaf3a79ebf09475863774bf72`。当前真正未完成的工作从 **PHASE 5 集合级逐 ID 对账**开始。
