# Safety Basis Chat 续接状态

> 最后更新：2026-09-10  
> 每轮必须先读本文件，再核对 GitHub 与 Google Drive 真实状态；发生冲突时，以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 Codex V3 有价值数据、Stable ID、法规版本关系、条款、隐患、link、evidence、release、网站与审计历史的基础上，逐步改造成更适合 Chat 长期维护的 V4 / Chat-first 架构。

目标不是从零重建，也不是追求复杂技术流程；优先保证隐患内容、法规版本、条款原文、适用性和隐私正确，同时降低 SQLite / dependency hash / 本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— **完成**
- Phase 2：V4 Chat-first 架构设计 —— **完成**
- Phase 3：V4 发布门禁设计 —— **完成**
- Phase 4：V3 → V4 字段映射设计 —— **完成**
- Phase 5：V4 只读迁移原型 —— **完成并通过原型验收**
- 当前下一阶段：**Phase 6：迁移现有有效知识**

不得跳到 Phase 9/10 提前实现 Validator/Gate；应继续按既定 Phase 顺序推进。

## 当前工作分支

`chat-v4`

禁止直接修改 `main`。

### 当前关键提交

- Phase 4：`11b6f65f7e8004a2fcdcde2ed7f506dcf929d38e` — `docs: define V3 to V4 field migration`
- Phase 5 迁移器：`b509db266864771cd2f707ea3da3b3f4ca11c041` — `feat: add read-only V3 to V4 migration prototype`
- Phase 5 验收报告：`15cd827fbbee11e7c9e3501ed9573942d89af2c3` — `docs: record Phase 5 migration prototype validation`

本文件更新提交位于上述提交之后；下一轮必须重新读取 `chat-v4` HEAD 获取实际最新 commit。

## 当前真实基线

### Google Drive 最新 V3 工作面

路径：`ESH_Codex/work/safety-basis`

Drive 最新 V3 Git 语义基线：

`data-verify-batch-003 @ ecd76fa521c7a3af8bf1341481bb6588dac1ef37`

GitHub 远端 V3 `data-verify-batch-003` 仍较旧；禁止用 GitHub 旧 V3 源码覆盖 Drive 最新成果。

### `source/master/safety.sqlite3`

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- `PRAGMA integrity_check = ok`
- schemaVersion：3

关键数量：

- laws：160
- law_versions：161
- clauses：2603
- hazards：1125
- links：2298
- evidence：1124
- verification：16159
- sources：24
- source_rows：6155
- law_successions：4

状态基线：

- hazards：已核验 662；待核验 461；待整理 2
- clauses：已核验 95；待核验 2508
- links：已核验 790；已失效 1502；待核验 6
- law_versions：现行有效 156；即将生效 2；待核验 3

### `source/library/fulltext.sqlite3`

- size：21,864,448 bytes
- SHA-256：`8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`
- `integrity_check = ok`
- documents：65
- FTS records：16,863

### 最新候选 release

`reviewed-20260909-r10`

- releaseHash：`dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`
- hazards：242
- laws：148
- law_versions：150
- clauses：52
- links：269

r8 是历史质量事故版本，不得恢复。r10 只是候选和迁移对比/佐证基线，不是 V4 事实源。

### 当前生产选择

`source/releases/site-selection.json` 仍指向：

`reviewed-20260909-r4`

**不得自行切 r10 或 V4。**

## Phase 2 / 3 / 4 已冻结设计

正式文件：

- `docs/ARCHITECTURE_V4_CHAT_FIRST.md`
- `docs/GATE_V4.md`
- `docs/MIGRATION_V3_TO_V4.md`

核心原则：

1. V4 日常维护源转为 Git-first `knowledge/`。
2. Stable ID 原样保留，不能给现有 1000+ hazard 批量改号。
3. SQLite 保留为 V3 冻结/迁移/分析资产，不再作为 V4 日常唯一写入口。
4. review 与 entity 分离，使用 `reviewedContentHash` 绑定实体内容。
5. link review 额外保存 hazard/clause `contextHashes`。
6. 不恢复 V3 通用 dependencyHash 全图级联。
7. evidence Tier A/B/C；完整全文不是可靠局部条款的统一发布前置条件。
8. Hard Gate 聚焦内容真实性、版本时效、link applicability、外键/重复/隐私。
9. evidence snapshot/hash/reviewDue 等非关键历史元数据默认降级为 Warning。
10. upcoming/repealed 不得错误支撑当前 hazard。
11. `primary`、候选角色不能自动映射 direct；不明确时迁为 `unclassified` + pending。
12. r10 只做对比/佐证，禁止反向覆盖 V3 SQLite。

## 本轮完成

本轮收口 Phase 5，并把此前已经运行通过但尚未写回 GitHub 的成果正式保存。

完成：

1. 重新读取 `docs/CHAT_HANDOFF.md`，发现其仍停在 Phase 3/“下一阶段 Phase 4”，与 GitHub 实际状态冲突。
2. 核对 `chat-v4`，确认 Phase 4 已在 `11b6f65...` 完成。
3. 核对 Drive `source/master/safety.sqlite3`，确认仍是冻结基线 110,002,176 bytes，没有被新旧备份替换。
4. 对 Phase 5 迁移器重新执行 Python 语法校验。
5. 重新核对 SQLite / fulltext SHA-256，与冻结值完全一致。
6. 正式提交 `tools/v4/migrate_v3.py`。
7. 正式提交 `docs/PHASE5_MIGRATION_PROTOTYPE_REPORT.md`。
8. 修正阶段顺序：Phase 6 为“迁移现有有效知识”；Validator/Gate 仍在 Phase 9/10。
9. 更新本 `CHAT_HANDOFF.md`。

## Phase 5 原型结果

迁移原型以 SQLite `mode=ro` 打开冻结母库，输出隔离候选树，不调用旧 V3 `tools/pipeline/`，不反写数据库。

### 全量迁出

- laws：160 / 160
- lawVersions：161 / 161
- clauses：2603 / 2603
- hazards：1125 / 1125
- links：2298 / 2298
- evidence：1124 / 1124
- successions：4 / 4

### 自动 verified candidate（保守提炼）

- law：148
- lawVersion：150
- clause：54
- hazard：642
- link：179

### 其余 review

- law：11 pending，1 superseded
- lawVersion：11 pending
- clause：2549 pending
- hazard：483 pending
- link：1502 superseded，617 pending

### 当前可形成 qualifying basis 的保守比较子集

- laws：148
- current law_versions：148
- clauses：54
- links：179
- hazards：158

该 158 **不是正式 V4 release 数量**，只是 Phase 5 原型在现有证据与保守角色映射下可形成完整链的比较子集。

### r10 差异已解释

r10 比 V4 原型多 90 条 link：

- `primary`：84
- `候选直接依据`：5
- `主要负责人职责`：1

这些历史角色不足以自动证明 direct/supporting/fallback 语义，因此保持 pending/unclassified；相应造成 84 个 r10 hazard 暂不能形成 V4 qualifying chain。

这是保守迁移差异，不是数据丢失。

### Quarantine

154 条：

- `ROLE_UNCLASSIFIED`：143
- `VERSION_EFFECTIVITY_UNCERTAIN`：11

不删除实体，不自动升级。

## 本轮修改文件

- 新增 `tools/v4/migrate_v3.py`
- 新增 `docs/PHASE5_MIGRATION_PROTOTYPE_REPORT.md`
- 更新 `docs/CHAT_HANDOFF.md`

未修改：

- `main`
- V3 SQLite
- fulltext SQLite
- `site-selection.json`
- production website
- 任何正式 release

## 本轮校验

- `python -m py_compile tools/v4/migrate_v3.py` 对本轮同一脚本内容通过。
- `safety.sqlite3` SHA-256：`7086d945...76bc8`，与冻结值一致。
- `fulltext.sqlite3` SHA-256：`8cedaf8f...b30e`，与冻结值一致。
- Phase 5 两次完全相同输入重跑：candidate tree hash 均为 `5545fcfbd43fdeac8d5cb9a7106b17639a5781237330fe40b1c7ff5b0542e07d`。
- 整个原型输出树两次 hash：`6e3bb90df7d9e2150e0d33a8f72a80005235db797fe7826953951c63951eb39c`。
- ID issue：0。
- broken FK：0。
- hazard tag 重复组合：0。
- law alias 重复组合：0。
- 公开 candidate 私有路径/Drive 私有 URL/`snapshot_ref`/`storage_ref`/`raw_payload`/`legacy_payload` 扫描命中：0。
- r8 已失效 link 没有复活。
- pending 没有因为追求数量批量升级 verified。

## 当前项目状态

Phase 1～5 已形成可续接的文档 + 代码基线。

V4 还没有正式 `knowledge/` 发布工作面，也没有正式 V4 release，更没有切生产。

当前最重要的下一步不是修 V3 旧 gate failure，也不是提前写 Gate V4，而是按 Phase 6 把“现有有效知识”从 Phase 5 隔离 candidate 中安全纳入版本控制的 V4 工作面。

## 未完成事项

### Phase 6

迁移现有有效知识，优先：

- verified law
- verified / current lawVersion
- verified clause
- verified hazard
- verified、角色明确且适用性有佐证的 link
- 必需 evidence public projection
- succession
- review sidecar

必须继续保留：

- pending
- superseded / inactive
- r8 历史错误
- `unclassified` active link
- 效力不明 lawVersion

但这些内容可继续留在迁移输出/隔离区，不得为了“全量进 knowledge”强行升级。

### 后续 Phase

- Phase 7：法规与标准核验框架
- Phase 8：历史报告条款重新审阅
- Phase 9：实现 V4 Validator
- Phase 10：实现 V4 Gate
- Phase 11：V4 网站构建
- Phase 12：V4 候选 release
- Phase 13：V3/V4 对比验收
- Phase 14：真实差异修复
- Phase 15：法规核验持续工作
- Phase 16：最终验收
- Phase 17：生产切换（必须用户明确批准）

## 下一轮第一步

**开始 Phase 6 的第一个可独立收口批次：先建立 version-controlled `knowledge/` 最小核心骨架，并迁入 verified law + current verified lawVersion + succession + 对应 review/evidence public projection；使用 Git tree/commit 批量写入，不逐文件人工修改。**

完成该批次后必须：

1. 核对迁入 ID 与 Phase 5 candidate 一致；
2. 检查外键和重复；
3. 扫描私有字段；
4. 记录批次数量和 tree/commit；
5. 更新本 handoff；
6. 下一轮再继续 clause/hazard/link，不在同一轮强行吞完整 1.3 万文件。

## 法规/标准待核验队列

当前不启动全量法规核验。Phase 6 后仍需重点处理：

- 143 条 `ROLE_UNCLASSIFIED` active link 的逐条适用性与角色复核；
- 11 个 `VERSION_EFFECTIVITY_UNCERTAIN` lawVersion 的版本/效力/日期补证；
- 当前网站高频依据优先核验；
- upcoming 版本只能进入法规知识，不得支撑当前 asOf hazard。

## 风险 / 阻塞

1. Drive 最新 V3 Git 历史仍比 GitHub 远端 `data-verify-batch-003` 新；因此禁止从 GitHub 旧 V3 pipeline 直接重构生产代码。
2. Phase 5 通过独立只读迁移器绕过了这一源码分叉，当前迁移数据本身不再因此阻塞。
3. 143 条 active link 角色不明确，是 Phase 6/后续核验的重要质量风险；不得批量猜成 direct。
4. 11 个 lawVersion 效力/日期不足，保持 pending/quarantine。
5. r10 不能作为 V4 事实源，只能作对比/佐证。
6. 当前没有需要用户决策的不可逆问题。

## 用户待决策事项

当前无。

正式生产切换仍必须等用户以后明确批准。

## 明确禁止事项

- 不直接修改 `main`
- 不切生产/GitHub Pages
- 不自行修改 `site-selection.json`
- 不用 GitHub 旧状态覆盖 Drive 最新 V3
- 不恢复 r8
- 不把 pending 批量升级 verified
- 不把 `primary` / 候选角色机械映射为 direct
- 不编造法规/标准/条款/版本/效力
- 不把旧版条文当新版
- 不把 upcoming 当 active 当前依据
- 不因完整全文缺失否定已可靠核验的具体条款
- 不公开企业资料、内部路径、私有报告、私有原件、受限全文、账号/token
- 不用旧 release 覆盖新 release
- 不反写或覆盖冻结 V3 SQLite
