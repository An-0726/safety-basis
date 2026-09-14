# AGENTS.md — 仓库长期接手记忆与总施工计划

> **这是 AI / Codex / 新维护者的唯一实时接手入口。**
> 本文件同时承担三件事：记录“现在做到哪”、规定“下一步做什么”、维护“从当前状态一路做到正式上线的完整路线”。
> 架构长期规则仍由 `README.md` 与 `docs/` 解释；法规事实必须回到正式知识链和原始证据，本文件不能替代法规原文。

## 0. 一句话接手

新窗口只需要收到这句话：

> **接手 `An-0726/safety-basis`，先读根目录 `AGENTS.md`，按 `CURRENT PHASE / NEXT ACTION / MASTER ROADMAP` 从当前状态继续；做完一个动作后自动进入下一个未完成阶段，不要停下来等用户重新解释；没有完成只读核验前不要改私有母库。**

接手后不要要求用户重新讲 1250 / 1929 / 2014 / publication / SQLite 的历史，也不要从旧聊天猜状态；以本文件和当前 `main` 为准。

---

## 1. ULTIMATE GOAL — 最终目标

最终目标不是“整理几个文件”或“做完一次去重”，而是形成一套可长期维护、可审计、可持续部署的安全隐患法规依据网站，并完成正式上线验收。

最终应同时满足：

1. **私有法规证据库清楚**：原始证据、历史版本、来源副本、OCR/文本派生物、全文检索数据库职责明确，不再互相冒充母库；
2. **正式结构化知识唯一**：`knowledge/` 是法规身份、真实版本、条款、隐患、关联和审核的唯一正式结构化来源；
3. **重复关系被正确处理**：完全重复文件、同版本多来源、真实历史版本、旧 ID/别名、候选记录均有明确归属，不靠标题模糊删除；
4. **法规引用可追溯**：正式隐患依据必须满足“法规身份 → 适用版本 → 条/款/项 → 逐字原文 → 官方/原始证据 → 适用性审核”；
5. **候选与正式彻底分层**：不能核实的记录继续保留为待核实/候选，但不得混进正式公共站；
6. **公开站只展示正式可用数据**：正式站不展示技术重复、无正式条款目录项、未实施版本作为当前依据或未核验候选；
7. **本地私有版可重建**：本地可以从当前仓库 + 私有 `source/library/` 重新生成 `dist/local/`，不依赖旧发布快照；
8. **GitHub Pages 正式部署成功**：`main` 的 Validate、Build、Pages Deploy 全部成功，线上站点完成抽样核验；
9. **仓库能被任意新窗口继续维护**：每一阶段完成后更新本文件，不依赖聊天上下文。

### 项目完成定义（Definition of Done）

只有以下条件全部满足，才能把“大阶段整改/清理”标记为完成：

- 私有母库已完成实体级盘点，并有明确重复/历史/派生物分类；
- 工作母库若发生修复/写入，已先备份、再验证、再记录变更；
- `knowledge/` 不存在未经解释的同身份同真实版本重复；
- 当前 1,929 目标隐患均有明确状态：正式、待核实、历史/合并，不允许“身份不明”；
- 所有正式记录均通过 Gate；
- `proposed` 不进入公开正式包；
- current 发布包由源码现场生成并通过验证，不提交为第二套旧快照；
- 本地私有版重建通过；
- GitHub Actions 全绿；
- GitHub Pages 部署成功；
- 上线后完成关键搜索、法规详情、条款、官方来源、候选隔离、移动端/桌面端基础抽检；
- `AGENTS.md`、必要时 `README.md` / `docs/HANDOFF.md` 已同步到最终状态。

---

## 2. 当前状态快照

**LAST VERIFIED：2026-09-14**

当前唯一 Git 主线：`main`。

2026-09-14 正式发布架构已完成收口（PR #29）：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担公开题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 是运行时生成物，Git 忽略；
- 正式站只发布当前日期 Gate 通过的已核验隐患；`proposed` 不进入公网；
- `upcoming` 尚未实施版本不能提前支撑当前正式隐患；
- main 的数据校验、正式站 build 和 GitHub Pages deploy 已通过。

当前正式发布基线：

- 1,409 条正式隐患；
- 55 个实际引用法规版本；
- 1,193 条正式条款；
- 1,524 个正式关联；
- 512 条 `proposed` 候选仅留 `knowledge/`，正式公开 0 条候选。

当前 knowledge 库存基线：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体、1,547 个关联。

新版 Excel 目标集是 1,929 个唯一隐患 ID（621 修订、1,308 保留），它不是正式发布数量。

当前公开站已经在线，但**这不代表本轮整体整理工作已经结束**。现在是在已上线安全基线之上继续做“母库整理 → 数据归并 → 证据补齐 → 再发布”的 vNext 收口。

---

## 3. 接手后必须先读

在任何写操作前依次读：

1. `AGENTS.md`（本文件，实时进度、总路线、下一动作）；
2. `README.md`（唯一架构、数据口径、发布规则）；
3. `docs/HANDOFF.md`（人类交接摘要）；
4. `docs/ARCHITECTURE.md`；
5. `docs/MAINTENANCE.md`；
6. `docs/LEGAL_STATUS_POLICY.md`；
7. `docs/CANDIDATE_REVIEW.md`；
8. 涉及 source 时再读 `source/README.md` 与 `source/releases/README.md`。

如果文档与当前代码冲突，先核代码、CI 和当前数据，再修文档；不要让多份说明长期分叉。

---

## 4. 权威层级

### 4.1 法规证据

正式引用链固定为：

`隐患描述 → 法规身份 → 适用版本 → 具体条/款/项 → 逐字原文 → 官方来源/原始证据 → 适用性审核`

硬规则：

- AI 摘要、搜索摘要、OCR、TXT、HTML、Excel“条款要点”只能用于定位，不能充当正式法规原文；
- 找不到官方原文或准确条款时标记“待核实 / 证据不足”，不得编造；
- 修订/废止/尚未实施版本必须记录效力和适用日期；
- “最新发布”不等于“当前适用”；
- 同一法规、同一真实版本、不同来源 = 一个版本，多来源；
- 同一法规、真实不同版本 = 分别保留，不得为了去重合并。

### 4.2 项目数据

- `knowledge/`：正式结构化法规身份、版本、条款、隐患、关联、审核；
- `source/library/archive/`：私有原始证据归档，应尽量不可变、按 SHA 去重；
- `source/library/fulltext.sqlite3`：全文检索数据库，可以维护/重建索引，但不是最高法律证据；
- `source/library/incoming-*`：收件/暂存，不应长期被当成第二套母库；
- `source/publication/`：公开来源资料层；
- `source/releases/current/`、`dist/`、网页索引：可重建成品，不得反向当母库。

---

## 5. 私有母库当前已核事实

本地工作仓库约定：

`D:\ESH\ESH_Codex\work\safety-basis\`

私有法规母库：

`D:\ESH\ESH_Codex\work\safety-basis\source\library\`

Google Drive for desktop 已把该项目同步到 **Computers / 我的笔记本电脑** 下。连接器的关键词搜索可能漏掉二进制 SQLite；**不能因为搜索返回 0 就判断文件不存在**。应直接读取已知 `source/library` 文件夹。

云盘目录直读已确认 `source/library/` 包含：

- `fulltext.sqlite3`；
- `archive/`；
- `incoming-20260910/`；
- `incoming-20260913/`；
- `inventory/`；
- `pending-originals/`；
- `pending-originals.json`。

`fulltext.sqlite3` 已分别从云盘本体和聊天上传副本核验，二进制一致。当前只读审计结果：

- 文件大小：106,958,848 bytes；
- `documents`：170；
- `fulltext_fts`：215,326；
- `documents` 中唯一文件 SHA-256：166；
- 同一 SHA 对应多条 document 的重复组：4 组；
- `PRAGMA integrity_check` 当前提示：`malformed inverted index for FTS5 table main.fulltext_fts`；
- 已在**副本**上测试 FTS rebuild，可恢复 integrity `ok`，且 documents / paragraphs 数量不减少；
- **尚未对工作母库执行 rebuild，也尚未删除/合并任何 document。**

`inventory/111-common-laws-20260913.md` 当前记录：144 个原文件、138 个唯一 SHA-256、6 个完全重复文件；并区分现行/历史版本、征求意见稿、指南工作资料、文件名内容不一致等类别。该统计是 inventory 记录，后续仍需与实际 archive / incoming / SQLite 全量对账。

---

## 6. MASTER ROADMAP — 从现在到正式上线的完整工作计划

状态约定：`DONE` 已完成并验证；`IN PROGRESS` 当前阶段；`PENDING` 未开始；`BLOCKED` 有明确阻塞。

### PHASE 0 — 架构与发布边界收口 — DONE

已完成：

- 正式站只发布 Gate 通过的正式隐患；
- `proposed` 退出正式公共包；
- 正式法规索引回归 `knowledge` 实际引用版本；
- `source/publication` 退回来源/题录/全文资料职责；
- `upcoming` 不再提前支撑当前正式隐患；
- `source/releases/current/` 改为现场生成，不再提交 Git；
- main CI / GitHub Pages 已成功。

完成证据：PR #29 及 main CI。

### PHASE 1 — 私有母库只读实体审计 — IN PROGRESS

目标：在不改任何原件和数据库的前提下，把母库里“到底有什么”彻底弄清楚。

任务：

- 全量枚举 `fulltext.sqlite3.documents`；
- 输出 4 组同 SHA 重复 document 的完整明细；
- 枚举 `archive/` 的实际 SHA 归档；
- 枚举 `incoming-20260910/`、`incoming-20260913/` 实际文件；
- 对照 `inventory/` 与 `pending-originals`；
- 建立 `SQLite document ↔ SHA ↔ archive ↔ incoming ↔ 文件类型` 映射；
- 初步关联 `knowledge` 的法规身份 / 版本。

分类必须分开：

- 完全相同文件；
- 同一法规 + 同一真实版本 + 多来源；
- 同一法规真实不同历史版本；
- OCR / clean.txt / HTML / 转换文本等派生物；
- 征求意见稿 / 编制说明 / 指南 / 手册 / 检查表；
- 文件名与内容不一致；
- 暂时无法判断。

**退出条件：**形成一份完整只读审计结果，所有疑似重复都有分类或“待人工判断”，未对工作母库做任何写操作。

### PHASE 2 — 母库整理方案与安全变更清单 — PENDING

目标：把 PHASE 1 的事实变成可执行的“保留/归并/清理”方案，但此阶段仍不直接破坏原始证据。

任务：

- 为每个 SHA / document 指定 canonical 原件；
- 明确哪些只是重复登记，哪些是来源别名，哪些是真实历史版本；
- 明确 incoming 中哪些已归档、哪些仍待处理；
- 明确 OCR/TXT 是否只作为派生物保留；
- 给出 SQLite 重复 document 的合并/别名方案；
- 给出 FTS5 rebuild 方案；
- 确认备份策略与回滚路径；
- 形成拟操作清单，逐项标注风险。

**退出条件：**用户可以清楚看到“会改什么 / 不会改什么 / 能否回滚”，并且高风险动作在执行前有备份。

### PHASE 3 — 私有母库实际修复与去重 — PENDING

前提：PHASE 2 方案已经审阅，且工作母库有可恢复备份。

目标：修复检索索引和确定性重复，不破坏证据链。

可能动作（以 PHASE 2 结果为准，不预设全部执行）：

- FTS5 索引 rebuild；
- 合并/标记同 SHA 重复 document；
- incoming 已归档文件退出“待处理”状态；
- 派生物与原件关系明确；
- 保留真实历史版本；
- archive 原件不因“标题相似”被删除；
- 更新 inventory / manifest 类记录。

**退出条件：**SQLite integrity `ok`；documents/paragraphs 变化有完整解释；原始证据可追溯；重复关系可审计；本地全文检索正常。

### PHASE 4 — `knowledge/` 法规身份与版本 canonical 化 — PENDING

目标：让正式结构化知识层不再存在“同一法规同一真实版本被多个内部记录重复表达”的问题。

任务：

- 对 `knowledge/laws` 做法规身份唯一性检查；
- 对 `knowledge/law-versions` 做 `lawId + versionKey` / 文号 / 发布机关 / 生效时间交叉核对；
- publication 记录只挂来源，不创造第二个正式法规身份；
- 同版本多来源归并到一个 canonical version；
- 真实不同版本分别保留并记录替代/失效关系；
- 旧 `LF/LV` 稳定 ID 不随意重编号，必要时采用 alias / canonical 指向；
- 检查 clauses 和 hazard links 是否仍指向正确版本。

**退出条件：**构建器不再发现未经解释的同身份同版本重复；所有归并都有证据和旧 ID 追溯路径。

### PHASE 5 — 隐患实体与 1,929 目标集全量对账 — PENDING

目标：把 `knowledge` 中 2,014 个隐患实体与新版 1,929 目标集的关系完全解释清楚。

任务：

- 当前目标隐患逐条匹配；
- 历史 / superseded / merged / alias 与当前项分开；
- 真正重复隐患只在证据充分时归并；
- 相似标题但场景、条款、整改要求不同的不得误合并；
- 旧 ID 保留追溯映射；
- 输出“当前正式 / 当前候选 / 历史实体 / 合并别名 / 待判断”分类。

**退出条件：**2,014 与 1,929 的差异可以逐项解释，不再靠总数猜测重复。

### PHASE 6 — 候选法规证据回绑与转正 — PENDING

当前基线：512 条 `proposed` 候选仅在 `knowledge` 后台。

目标：逐步把能证明的候选转成正式；证据不足的继续明确保留为候选，不为了“清零”而编造依据。

流程：

`隐患 → 法规身份 → 当前适用版本 → 具体条/款/项 → 官方原文 / 原始证据 → 原文逐字匹配 → 适用性审核 → 转正`

工作原则：

- 优先处理高频重复法规依据，复用已核验条款；
- 先清理错误版本、未来版本、标准/法律性质混用；
- 旧 Excel 中 AI 归纳的“条款要点”不转成正式原文；
- 外部工作簿如继续使用，必须先重新核实当前剩余数量，不直接沿用旧聊天中的阶段数字；
- 无证据项保留 `proposed` / 待核实。

**退出条件：**每个当前候选都有明确状态和原因；转正项全部通过 Gate；无法转正项有明确缺失证据。

### PHASE 7 — publication / 官方来源 / 全文资料归整 — PENDING

目标：让公开资料层“有用但不制造第二套法规库”。

任务：

- publication 题录与 canonical law/version 建立稳定映射；
- 官方入口 URL 去重、失效检查；
- 允许公开的全文与私有版权全文严格分开；
- 同一法规多个官方页面作为来源，不变成多个法规卡；
- `library.html` / 法规全文页继续承担资料浏览，不冒充正式引用层。

**退出条件：**正式法规数由 knowledge 决定，publication 只影响来源展示，不再改变法规身份数量。

### PHASE 8 — 前端与本地版一致性验收 — PENDING

目标：公开站和本地私有版都体现同一结构化规则。

检查：

- 公网只显示正式已核验隐患；
- 正式法规只显示实际正式条款引用版本；
- 技术 ID 不作为主要用户标签；
- upcoming / historical / candidate 标签准确；
- 条款、原文、官方来源跳转正确；
- 本地 `dist/local/` 能正常加载私有全文检索；
- 不因 canonical 化导致 SQLite 文档标签、全文链接或 archive_ref 失联；
- 桌面端与移动端基础交互可用。

**退出条件：**公开版和本地版的正式数据口径一致，私有全文仅本地可见。

### PHASE 9 — 全量验证与 Release Candidate — PENDING

必须运行：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
py -3 tools/build_local_release.py
```

同时核对：

- 正式隐患数；
- 实际引用法规版本数；
- 正式条款数；
- 正式关联数；
- proposed 数；
- upcoming / historical 是否未错误进入当前正式依据；
- current 包是否可从空生成目录确定性重建；
- validators 是否不修改 governed source data。

**退出条件：**所有 blocker 为 0；测试全绿；本地构建成功；数字和 README / HANDOFF / AGENTS 一致。

### PHASE 10 — 正式合并、GitHub Pages 部署与上线验收 — PENDING

目标：把本轮最终整理结果真正部署上线，而不是停在本地或 PR。

流程：

- 从工作分支开 PR；
- PR CI 全绿；
- 合并 `main`；
- main `Validate safety data` 成功；
- main `Build current verified website` 成功；
- GitHub Pages `deploy` 成功；
- 打开线上站进行抽样验收。

线上至少抽检：

- 首页/隐患检索；
- 法规检索；
- 隐患详情 → 条款 → 法规来源链；
- 若干高频法规；
- 一个历史/即将实施版本场景；
- 候选不在正式站出现；
- 页面无重复法规卡、无明显技术 ID 污染；
- 手机宽度与桌面宽度基础可用。

**退出条件：**Pages deploy success + 线上抽检通过 + 文档已记录本次发布基线。

### PHASE 11 — 进入长期维护循环 — PENDING

正式上线后不是“项目结束不管”，而是进入稳定维护：

- 新法规/新版本 → 先入私有证据层 → 核身份/版本/效力 → 更新 knowledge → Gate → 部署；
- 新隐患/新 Excel → 先去重 → 候选 → 证据回绑 → 审核 → 转正；
- 失效/修订法规 → 保留历史版本并调整适用区间，不删除证据；
- 定期检查官方 URL、upcoming 生效、失效版本、候选积压；
- 私有 SQLite 定期备份并做 integrity 检查；
- 每次实质变更都更新 `AGENTS.md`；架构/口径变化同步 README。

**长期目标：**任何时候 `main` 都是可部署的当前正式版本，私有母库可恢复，候选不会污染公网，下一位维护者无需旧聊天即可继续。

---

## 7. CURRENT PHASE — 当前阶段

**PHASE 1 — 私有母库只读实体审计。**

当前不要转去大量法规回绑，也不要先修数据库；先把母库重复关系和证据关系搞清楚。

### 当前阶段任务队列

1. 全量枚举 `fulltext.sqlite3.documents`；
2. 输出 4 组同 SHA 重复 document 的完整明细；
3. 把这 4 个 SHA 与云盘 `archive/`、`incoming-*` 对上；
4. 判断是同一原件重复登记、来源别名、历史版本误挂还是其他原因；
5. 扩展到全部 170 documents 与 archive/incoming/knowledge 的映射；
6. 输出 PHASE 1 只读审计报告；
7. 更新本文件，把 PHASE 1 标为 DONE、PHASE 2 标为 IN PROGRESS，并写新的 NEXT ACTION。

---

## 8. NEXT ACTION — 下一动作

> **只读分析 `source/library/fulltext.sqlite3` 的 170 条 documents，先输出 4 组同 SHA 重复 document 的明细；再把这些 SHA 与云盘 `archive/` 和 `incoming-*` 对上，判断它们是同一原件重复登记、来源别名还是版本关系。不要写数据库。**

### 做完 NEXT ACTION 以后怎么办

**不要停。** 按下面规则继续：

1. 把结果写回本文件的“当前已核事实”；
2. 更新当前 PHASE 的任务队列；
3. 如果 PHASE 1 退出条件已满足，把 PHASE 1 改为 `DONE`；
4. 把 PHASE 2 改为 `IN PROGRESS`；
5. 从 MASTER ROADMAP 中取 PHASE 2 的第一个未完成任务作为新的 `NEXT ACTION`；
6. 继续执行，直到遇到需要用户批准的高风险写操作、缺失证据或外部阻塞。

**原则：`NEXT ACTION` 是光标，不是终点；`MASTER ROADMAP` 才是总任务。**

---

## 9. 写操作与风险边界

### 可以自主做的低风险工作

- 只读审计；
- 生成对账表/报告；
- 修改 Git 中的文档、构建逻辑、测试（走分支/PR/CI）；
- 在副本上验证 SQLite 修复方案；
- 构建可重建发布物；
- 对公开来源做核对。

### 必须先有备份/方案再做的高风险工作

- 写入工作 `fulltext.sqlite3`；
- 删除或移动 archive 原件；
- 合并 SQLite documents；
- FTS rebuild 工作母库；
- 删除 knowledge 正式实体；
- 改稳定 ID；
- 大批量修改正式法规条款/关联。

高风险动作前必须满足：明确原因、备份可恢复、拟操作清单、影响范围、验证方案。

---

## 10. 绝对禁止事项

- 不把私有 PDF、SQLite、OCR、企业资料提交 GitHub；
- 不直接编辑 `source/releases/current/` 或把生成包重新提交 Git；
- 不为了界面整洁重编号 `LF_* / LV_* / C_* / H_*` 稳定 ID；
- 不按标题相似直接删除法规或隐患；
- 不把同名不同真实版本合并；
- 不把 publication 的多个来源当成多个法规身份；
- 不把尚未实施的 upcoming 版本作为当前正式依据；
- 不从旧 Excel、旧发布包、网页成品、OCR/TXT/HTML 反向覆盖正式知识源；
- 不在 SQLite 正在被使用/写入时做文件级替换或复制；
- 不先修/删工作母库再补备份和记录；
- 不为了“候选清零”而捏造法规条款或错误转正；
- 不新建 `final2`、`latest2`、日期版 handoff、平行 current 等第二套“最终版”。

---

## 11. Git 修改流程

涉及代码、架构、正式数据、候选策略、发布规则或接手状态：

1. 从最新 `main` 建工作分支；
2. 修改；
3. 运行项目现有测试、Gate、构建验证；
4. 开 PR；
5. CI 全绿后合并 `main`；
6. main 的 Pages build/deploy 成功后才算公开站变更完成。

不要直接在 main 上做高风险数据改动。

纯私有母库动作不提交私有文件到 Git，但必须把**结果、规则变化、下一步**写回 `AGENTS.md`；若影响架构/口径则同步 README/HANDOFF。

---

## 12. 每次会话结束前必须更新

把仓库当作跨窗口长期记忆，**不能只在聊天里说“做到这里”**。

每个实质阶段结束前：

- 更新 `LAST VERIFIED`；
- 更新 MASTER ROADMAP 每个 PHASE 的状态；
- 更新“当前已核事实”；
- 更新 `CURRENT PHASE`；
- 更新 `NEXT ACTION`；
- 架构/数据口径/发布规则变化时同步更新根 `README.md`；
- 人类接手状态有重大变化时同步更新 `docs/HANDOFF.md`；
- 提交/PR 说明写清：改了什么、为什么、影响哪些数据、是否需要重新审核/重建；
- 不新增平行“最终版”文档；历史交给 Git。

### 新发现如何加入计划

MASTER ROADMAP 是活计划，不是假装永远不会变化。如果审计出现新问题：

- 不另建第二份路线图；
- 把新任务插入最合理的 PHASE；
- 如会阻塞后续阶段，标为 `BLOCKED` 并说明解除条件；
- 解决后恢复 `IN PROGRESS / DONE`；
- 始终保证从 CURRENT PHASE 可以一路追到 PHASE 10 正式部署和 PHASE 11 长期维护。

---

## 13. 快速接手检查

新 agent / 新窗口开始工作前，快速确认：

- 当前分支是不是 `main` 或明确工作分支；
- `AGENTS.md` 的 `LAST VERIFIED / CURRENT PHASE / NEXT ACTION` 是否一致；
- 公开站当前是否有已知失败 CI；
- 私有母库动作是否仍处于只读阶段；
- 是否有待合并 PR；
- 当前动作完成后属于哪个 PHASE、退出条件是什么；
- 最终目标仍然是 **通过 Gate → 合并 main → GitHub Pages 部署 → 线上验收**，不是停在中间报告。
