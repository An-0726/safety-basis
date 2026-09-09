# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（Chat 自动续建第 1 轮）
> 本文件是后续 Chat 独立轮次的首要续接入口。每轮必须先读本文件，再核对 GitHub 与 Google Drive 的真实状态；发生冲突时，以真实最新文件为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 Codex V3 有价值数据、Stable ID、法规/版本/条款/隐患/关联、证据、release、网站前端与历史审计成果的基础上，逐步迁移到更适合 Chat 长期维护的 V4 / Chat-first 架构。

V4 的核心目标是减少对本地 Code Agent、本地 SQLite 日常事务、过度复杂 verification/hash 流程和完整全文强制要求的依赖，同时继续保证隐患内容、法规版本、条款原文、隐患—条款适用性、历史版本、可追溯性、隐私和发布可靠性。

## 当前 Phase

**Phase 1：建立续接系统并冻结 V3 基线 —— 已完成首轮冻结盘点。**

下一轮进入 **Phase 2：V4 Chat-first 架构设计**。Phase 2 只做设计，不大规模迁移正式数据。

## 当前工作分支

### Chat 后续工作分支

`chat-v4`

- 该分支由 GitHub 远端 `data-verify-batch-003` 创建。
- 创建时远端基线：`2b895ea961f771cb469a86ca0155c586edf4df52`。
- **重要：该分支目前只是 Chat 文档/规划工作面，不代表最新 V3 源码与数据内容。**

### Drive 中真实 V3 本地工作分支

`data-verify-batch-003`

Drive 本地 `.git/HEAD` 明确指向该分支；本地分支 ref 为：

`ecd76fa521c7a3af8bf1341481bb6588dac1ef37`

最新本地提交信息：

`新增门禁修改方案文档：分级门禁（一级硬门禁+二级软门禁）`

GitHub 远端同名分支当前仍为：

`2b895ea961f771cb469a86ca0155c586edf4df52`

因此 **Drive 本地存在尚未推送 GitHub 的后续提交**。已确认 GitHub 无法解析 `ecd76fa...`，不得用远端旧分支覆盖 Drive 本地工作副本。

Drive 本地在 `2b895ea...` 之后的已确认提交链包括：

- `eace7b9a...`：修复门禁并生成 r6
- `0f38e24d...`：r7 修复重复 clause、全文库核验与依赖刷新
- `e61343ab...`：r8 批量关联/核验（后续确认存在质量事故）
- `9c2c078e...`：r10 发布包、修复 evidence 哈希/clauses、生成待获取标准清单
- `87996340...`：新增完整交接文档
- `ecd76fa5...`：新增门禁修改方案文档

## 当前真实基线

### GitHub

仓库：`An-0726/safety-basis`

`main` 当前：

`11a98ca3fa379a9e8a92549ba94dcc074297be1f`

main 根目录公开数据 `data/manifest.json`：

- dataVersion：`2026.09.08.4`
- hazards：81
- laws：28
- clauses：80
- links：93
- verifiedHazards：32
- pendingHazards：49

**禁止直接修改 main。**

### Google Drive 项目根目录

`ESH_Codex/work/safety-basis`

Drive 工作副本明显比 GitHub main 和远端 `data-verify-batch-003` 更新，应优先保护。

### 最新 SQLite 母库

路径：`source/master/safety.sqlite3`

Drive 文件：

- 大小：110,002,176 bytes
- 修改时间：2026-09-09 15:19:03Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- `PRAGMA integrity_check`：`ok`

关键表统计：

- laws：160
- law_versions：161
- clauses：2603
- hazards：1125
- links：2298
- sources：24
- source_rows：6155
- verification：16159
- evidence：1124
- law_successions：4
- candidate_admissions：1428

状态分布：

- hazards：已核验 662；待核验 461；待整理 2
- clauses：已核验 95；待核验 2508
- links：已核验 790；已失效 1502；待核验 6
- law_versions：现行有效 156；即将生效 2；待核验 3

`db_meta`：

- schemaVersion：3
- datasetHash：`a0916d788944c186a1420e8b0882971df54c4ebb056132100a8f4e841fa6b195`
- sourceCommit：`d05ab35de238d255f2c244d0e7c2f58dbfa83509`
- parserVersion：`master-migration-v1`

注意：`db_meta.sourceCommit` 是母库迁移元数据，不等于当前 Drive Git HEAD。

### 最新全文库

路径：`source/library/fulltext.sqlite3`

- 大小：21,864,448 bytes
- 修改时间：2026-09-09 11:04:10Z
- SHA-256：`8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`
- `PRAGMA integrity_check`：`ok`
- documents：65
- FTS 内容记录：16,863

### 最新候选 release

`source/releases/reviewed-20260909-r10/`

release.json：

- formatVersion：`safety-release-v2`
- asOf：`2026-09-09`
- dataVersion：`2026.09.09.2d38b8b8b576`
- releaseHash：`dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`
- sourceStateHash：`2d38b8b8b576446a34f48d3c98f7598ac44c2917c7208872031f9a2fb8b8e889`
- 发布 graph：hazards 242；laws 148；law_versions 150；clauses 52；links 269
- evidence：574
- proofs：861

r8 是历史质量事故版本，不可作为可靠发布基线。r9 为回滚后基线；r10 为当前最新候选。

### 当前网站/CI 选择

`source/releases/site-selection.json` 仍指向：

`reviewed-20260909-r4`

releaseHash：`67617524f24ae494a76993b434f414faf0675cc7d4466b3715bbabf982ffb5f2`

因此：**r10 尚未正式切换为生产/CI 选包，不能自行切换。**

### 最新 exchange / proposals / reports

- 最新 exchange 主目录：`source/exchange/continuation-20260909/`，Drive 修改时间约 2026-09-09 14:39Z。
- 其中存在 `reverify-batch/`、门禁修复/核验脚本、待获取专项标准清单等后续成果。
- `source/proposals/` 当前仅见 `acceptance-exchange-v1.json` 与 `acceptance-exchange-final.json`，修改时间停在 2026-09-08。
- `source/exchange/overnight-20260909/reports/` 存在历史验收/CI/工作簿报告，最新约 2026-09-08 19:34Z；它们早于 continuation-20260909 与 r10，不得覆盖后续成果。

### 最新重要文档

Drive 项目内：

- `docs/COMPLETE_HANDOVER_20260909.md`
- `docs/GATE_MODIFICATION_PROPOSAL_20260909.md`
- `docs/DATA_ARCHITECTURE_V3.md`
- `docs/VERIFICATION_PUBLISH.md`
- `docs/FULLTEXT_LIBRARY.md`
- `docs/WORKFLOW.md`

Drive 中另有更新更晚的外部设计参考：

- `safety-basis_完整架构与设计书_20260909.md`，更新时间约 2026-09-09 16:03Z，明确记录本地提交 `ecd76fa`、r10、当前 V3 分层架构等。

该文档是 Phase 2 的重要输入，但不能直接替代本轮用户给出的 V4 Chat-first 目标和施工顺序。

## 本轮完成

1. 建立真实续接现场，不依赖旧聊天判断项目状态。
2. 核对 GitHub 仓库、main、远端 `data-verify-batch-003`。
3. 核对 Drive 本地 `.git` HEAD、分支 ref 与 reflog，确认 Drive 比 GitHub 远端更新。
4. 找到并只读校验最新 `safety.sqlite3` 与 `fulltext.sqlite3`。
5. 核对 V3 核心表数量、状态分布、数据库完整性和 SHA-256。
6. 找到并核对最新候选 release r10 的真实统计与 releaseHash。
7. 核对当前 `site-selection.json` 仍为 r4，确认生产/CI 未切 r10。
8. 盘点 exchange、proposals、reports 和最新重要文档。
9. 新建 GitHub `chat-v4` 分支，作为后续 Chat 的独立 V4 工作面。
10. 创建本文件 `docs/CHAT_HANDOFF.md`。

## 本轮修改文件

GitHub `chat-v4`：

- 新增：`docs/CHAT_HANDOFF.md`

未修改：

- `main`
- Drive 中 V3 正式数据库
- fulltext 数据库
- release
- `site-selection.json`
- 生产网站

## 本轮校验

- `safety.sqlite3`：`PRAGMA integrity_check = ok`
- `fulltext.sqlite3`：`PRAGMA integrity_check = ok`
- SQLite 表数量与 2026-09-09 完整交接文档核心统计一致
- r10 `release.json` JSON 可正常解析
- r10 graph 数量与交接文档一致：242 / 150 / 52 / 269（hazard / law_version / clause / link）
- GitHub main 与 Drive 本地 commit 已明确区分
- 已确认 GitHub 当前不存在 `ecd76fa...` commit，因此禁止把 GitHub 旧状态当作 Drive 最新状态

## 当前项目状态

V3 核心资产完整存在；最新 SQLite 与全文库完整性检查通过；r10 候选 release 存在且数据可读；生产/CI 仍保持旧选择，没有切换。

当前最重要的版本安全事实是：

**Drive 本地 V3 = `ecd76fa...`，GitHub 远端 `data-verify-batch-003` = `2b895ea...`，GitHub main = `11a98ca...`。Drive 更新，禁止反向覆盖。**

Phase 1 的目的已经达到：真实 V3 基线已冻结并写入续接文件。

## 未完成事项

- 尚未完成 V4 Chat-first 正式架构设计。
- 尚未完成 V4 Gate 正式设计。
- 尚未完成 V3 → V4 字段映射。
- 尚未建立 V4 knowledge 原型。
- 尚未迁移正式数据。
- 尚未实现 V4 validator / gate / release / website pipeline。
- 尚未做 V3/V4 对比验收。
- 尚未处理生产切换；生产切换必须用户批准。
- Drive 本地 6 个后续 commit 尚未推送 GitHub；本轮不擅自重写或重建该历史。

## 下一轮第一步

**创建并完成 `docs/ARCHITECTURE_V4_CHAT_FIRST.md` 的 Phase 2 初稿。**

开始前必须再次读取本文件，并核对 GitHub `chat-v4`、Drive 本地 `data-verify-batch-003` HEAD、最新数据库和最新重要设计文档是否发生变化。

Phase 2 要以本轮用户给出的 V4 Chat-first 目标为最高项目要求，同时吸收现有 V3 架构中仍有价值的 Stable ID、版本模型、证据、release、网站和追溯设计；不得直接大规模迁移数据。

## 后续任务

1. Phase 2：`docs/ARCHITECTURE_V4_CHAT_FIRST.md`
2. Phase 3：`docs/GATE_V4.md`
3. Phase 4：V3 → V4 数据字段映射设计
4. Phase 5：只读迁移原型
5. 其余 Phase 按用户规定顺序推进

## 法规/标准待核验队列

本轮只冻结基线，不启动大批量法规核验。

已知后续队列包括：

- 461 个待核验 hazard 所缺专项依据
- 2508 个待核验 clause
- continuation-20260909 生成的“待获取专项标准清单”（125 项）

在 V4 架构与门禁未确定前，不按旧 V3 流程全量处理这些队列。

## 风险 / 阻塞

### 1. Drive / GitHub 历史分叉

这是当前首要风险。

Drive 本地分支包含 GitHub 尚不存在的 commit。`chat-v4` 分支只是从远端旧基线建立的 Chat 文档工作面，因此后续在 `chat-v4` 上不得直接进行依赖最新 V3 源码内容的大规模代码修改，除非先完成安全的历史同步/对账。

Phase 2/3/4 以文档和只读分析为主，可继续进行。

### 2. r8 历史质量事故

禁止恢复或复用 r8 的批量核验结论作为真值。无法确认的内容保持 pending。

### 3. 生产仍为旧选择

r10 是候选，不是生产。不得修改 `site-selection.json` 指向 r10，不得切 GitHub Pages。

## 用户待决策事项

当前无必须立即由用户决策的问题。

若后续需要把 Drive 本地未推送 commit 与 GitHub 正式同步，必须先做差异核对，并采用不会覆盖 Drive 最新成果的方式。

## 明确禁止事项

- 不得直接修改 `main`
- 不得正式切换生产网站或 GitHub Pages
- 不得用 GitHub 旧状态覆盖 Drive 最新成果
- 不得用旧 release 覆盖 r10 或未来更新版本
- 不得用旧数据库覆盖当前 `safety.sqlite3`
- 不得把 r8 批量核验结果恢复为可靠真值
- 不得在 V4 架构确定前优先修 124 个旧 gate failure
- 不得在 V4 架构确定前全量核验 2508 个 clause
- 不得在 V4 架构确定前优先清理 1502 个历史失效 link
- 不得批量假定隐患—条款关联正确
- 不得编造法规、标准、条款、版本、日期、效力或适用范围
- 不得因为缺少完整标准全文就否定已可靠局部核验的具体条款
- 不得公开私有报告、标准原件、内部来源、企业信息或其他非公开资料
