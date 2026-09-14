# AGENTS.md — 仓库长期接手记忆

> **这是 AI / Codex / 新维护者的唯一接手入口。**
> 本文件记录“现在做到哪、下一步做什么、哪些绝对不能做”。架构和长期规则仍由 `README.md` 与 `docs/` 解释；法规事实必须回到正式知识链和原始证据，不以本文件代替法规原文。

## 0. 一句话接手

新窗口只需要收到这句话：

> **接手 `An-0726/safety-basis`，先读根目录 `AGENTS.md`，再按其中 `CURRENT MISSION` 从当前状态继续；没有完成只读核验前不要改私有母库。**

接手后不要要求用户重新讲 1250 / 1929 / 2014 / publication / SQLite 的历史，也不要从旧聊天猜状态；以本文件和当前 `main` 为准。

## 1. 当前状态快照

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

当前 knowledge 库存基线：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体、1,547 个关联。新版 Excel 目标集是 1,929 个唯一隐患 ID（621 修订、1,308 保留），它不是正式发布数量。

## 2. 接手后必须先读

在任何写操作前依次读：

1. `AGENTS.md`（本文件，当前任务与状态）；
2. `README.md`（唯一架构、数据口径、发布规则）；
3. `docs/HANDOFF.md`（人类交接摘要）；
4. `docs/ARCHITECTURE.md`；
5. `docs/MAINTENANCE.md`；
6. `docs/LEGAL_STATUS_POLICY.md`；
7. `docs/CANDIDATE_REVIEW.md`；
8. 涉及 source 时再读 `source/README.md` 与 `source/releases/README.md`。

如果文档与当前代码冲突，先核代码、CI 和当前数据，再修文档；不要让多份说明长期分叉。

## 3. 权威层级

### 法规证据

正式引用链固定为：

`隐患描述 → 法规身份 → 适用版本 → 具体条/款/项 → 逐字原文 → 官方来源/原始证据 → 适用性审核`

硬规则：

- AI 摘要、搜索摘要、OCR、TXT、HTML、Excel“条款要点”只能用于定位，不能充当正式法规原文；
- 找不到官方原文或准确条款时标记“待核实 / 证据不足”，不得编造；
- 修订/废止/尚未实施版本必须记录效力和适用日期；
- “最新发布”不等于“当前适用”。

### 项目数据

- `knowledge/`：正式结构化法规身份、版本、条款、隐患、关联、审核；
- `source/library/archive/`：私有原始证据归档，应尽量不可变、按 SHA 去重；
- `source/library/fulltext.sqlite3`：全文检索数据库，可以维护/重建索引，但不是最高法律证据；
- `source/library/incoming-*`：收件/暂存，不应长期被当成第二套母库；
- `source/publication/`：公开来源资料层；
- `source/releases/current/`、`dist/`、网页索引：可重建成品，不得反向当母库。

## 4. 私有母库当前已核事实

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

## 5. CURRENT MISSION — 当前正在做什么

**当前任务：本地私有法规母库的实体级只读体检与去重设计。**

在修改任何私有原件或 SQLite 前，完成：

1. 全量枚举 `fulltext.sqlite3.documents`，识别 4 组同 SHA 重复 document；
2. 对 `archive/`、`incoming-20260910/`、`incoming-20260913/`、`inventory/` 做实际文件/SHA 对账；
3. 建立映射：`SQLite document ↔ archive SHA ↔ incoming 原件 ↔ knowledge 法规身份 / 法规版本`；
4. 对每个疑似重复分类，不混为一种“重复”：
   - 完全相同文件；
   - 同一法规 + 同一真实版本 + 多个来源；
   - 同一法规的真实不同历史版本；
   - OCR / clean.txt / HTML 等派生物；
   - 征求意见稿 / 编制说明 / 指南 / 手册 / 检查表；
   - knowledge 内重复法规身份或重复 version；
5. 形成“保留 / 合并关系 / 可删除生成物 / 必须保留历史证据 / 待人工判断”清单；
6. **先给出审计结果和拟操作清单，再对工作母库做任何删除、改名、SQLite 写入或 FTS rebuild。**

当前不要转去继续大量法规回绑，先把母库与实体重复关系整理清楚。

## 6. 绝对禁止事项

- 不把私有 PDF、SQLite、OCR、企业资料提交 GitHub；
- 不直接编辑 `source/releases/current/` 或把生成包重新提交 Git；
- 不为了界面整洁重编号 `LF_* / LV_* / C_* / H_*` 稳定 ID；
- 不按标题相似直接删除法规或隐患；
- 不把同名不同真实版本合并；
- 不把 publication 的多个来源当成多个法规身份；
- 不把尚未实施的 upcoming 版本作为当前正式依据；
- 不从旧 Excel、旧发布包、网页成品、OCR/TXT/HTML 反向覆盖正式知识源；
- 不在 SQLite 正在被使用/写入时做文件级替换或复制；
- 不先修/删工作母库再补备份和记录。

## 7. Git 修改流程

涉及代码、架构、正式数据、候选策略、发布规则或接手状态：

1. 从最新 `main` 建工作分支；
2. 修改；
3. 运行项目现有测试、Gate、构建验证；
4. 开 PR；
5. CI 全绿后合并 `main`；
6. main 的 Pages build/deploy 成功后才算公开站变更完成。

不要直接在 main 上做高风险数据改动。

## 8. 每次会话结束前必须更新

把仓库当作跨窗口长期记忆，**不能只在聊天里说“做到这里”**。

每个实质阶段结束前：

- 更新本 `AGENTS.md` 的 `LAST VERIFIED`、`CURRENT MISSION`、已完成事实和明确的 `NEXT ACTION`；
- 架构/数据口径/发布规则变化时同步更新根 `README.md`；
- 人类接手状态有重大变化时同步更新 `docs/HANDOFF.md`；
- 提交/PR 说明写清：改了什么、为什么、影响哪些数据、是否需要重新审核/重建；
- 不新增 `final2`、`latest`、日期版 handoff、`docs/history/` 等平行“最终版”。历史交给 Git。

## 9. NEXT ACTION

新窗口从这里直接继续：

> **只读分析 `source/library/fulltext.sqlite3` 的 170 条 documents，先输出 4 组同 SHA 重复 document 的明细；再把这些 SHA 与云盘 `archive/` 和 `incoming-*` 对上，判断它们是同一原件重复登记、来源别名还是版本关系。不要写数据库。**

完成这一小步后，立刻更新本文件的结果与下一步，再继续下一批。
