# Safety Basis Chat 续接状态

> 最后更新：2026-09-10  
> 每轮必须先读本文件，再核对 GitHub 与 Google Drive 真实状态；发生冲突时，以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 Codex V3 有价值数据、Stable ID、法规版本关系、条款、隐患、link、evidence、release、网站与审计历史的基础上，逐步改造成更适合 Chat 长期维护的 V4 / Chat-first 架构。

优先保证隐患内容、法规版本、条款原文、适用性和隐私正确，同时降低 SQLite / dependency hash / 本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— **完成**
- Phase 2：V4 Chat-first 架构设计 —— **完成**
- Phase 3：V4 发布门禁设计 —— **完成**
- Phase 4：V3 → V4 字段映射设计 —— **完成**
- Phase 5：V4 只读迁移原型 —— **完成并通过原型验收**
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001 已完成**

不得跳到 Phase 9/10 提前实现 Validator/Gate。

## 当前工作分支

`chat-v4`

禁止直接修改 `main`。

### 当前关键提交

- Phase 4：`11b6f65f7e8004a2fcdcde2ed7f506dcf929d38e`
- Phase 5 迁移器：`b509db266864771cd2f707ea3da3b3f4ca11c041`
- Phase 5 验收报告：`15cd827fbbee11e7c9e3501ed9573942d89af2c3`
- Phase 5 交接：`b2d0f4e0384f54a1c51342f4ae3a7683351e8c41`
- Phase 6 core-laws-001：`5cf400bae85a99e7d1edfb2c271c10f161e0495b` — `feat: seed Phase 6 V4 core law knowledge batch 001`

本文件更新提交位于 `5cf400b...` 之后；下一轮必须重新读取 `chat-v4` HEAD 获取实际最新 commit。

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

## Phase 2 / 3 / 4 冻结设计

正式文件：

- `docs/ARCHITECTURE_V4_CHAT_FIRST.md`
- `docs/GATE_V4.md`
- `docs/MIGRATION_V3_TO_V4.md`

核心原则：

1. V4 日常维护源转为 Git-first `knowledge/`。
2. Stable ID 原样保留。
3. SQLite 保留为 V3 冻结/迁移/分析资产，不再作为 V4 日常唯一写入口。
4. review 与 entity 分离，使用 `reviewedContentHash` 绑定实体内容。
5. link review 额外保存 hazard/clause `contextHashes`。
6. 不恢复 V3 通用 dependencyHash 全图级联。
7. evidence 使用公开分级；完整全文不是可靠局部条款的统一发布前置条件。
8. Hard Gate 聚焦内容真实性、版本时效、link applicability、外键/重复/隐私。
9. 非关键历史 snapshot/hash/reviewDue 默认降级为 Warning。
10. upcoming/repealed 不得错误支撑当前 hazard。
11. `primary`、候选角色不能自动映射 direct；不明确时保持 `unclassified` + pending。
12. r10 只做对比/佐证，禁止反向覆盖 V3 SQLite。

## Phase 5 原型结果

只读迁移原型以 SQLite `mode=ro` 打开冻结母库，不调用旧 V3 pipeline，不反写数据库。

全量迁出：160 laws、161 lawVersions、2603 clauses、1125 hazards、2298 links、1124 evidence、4 successions。

保守自动 verified candidate：

- law：148
- lawVersion：150
- clause：54
- hazard：642
- link：179

当前可形成 qualifying basis 的比较子集：148 laws、148 current lawVersions、54 clauses、179 links、158 hazards。

r10 比原型多出的 90 条 link 已解释为：84 `primary`、5 `候选直接依据`、1 `主要负责人职责`；这些不足以自动证明 V4 角色语义，因此不自动升级。

Quarantine：143 条 `ROLE_UNCLASSIFIED` active link + 11 个 `VERSION_EFFECTIVITY_UNCERTAIN` lawVersion。

## 本轮完成

本轮开始 Phase 6，并完成第一个可独立收口子批次 `core-laws-001`。

完成内容：

1. 重新读取 `docs/CHAT_HANDOFF.md`，确认 Phase 6 为当前阶段。
2. 核对 `chat-v4` 起始 HEAD：`b2d0f4e0384f54a1c51342f4ae3a7683351e8c41`。
3. 使用冻结 `safety.sqlite3` 与 r10 佐证数据，只读提取 Phase 6 核心法规子集。
4. 保持“一实体一 JSON”，正式建立 version-controlled `knowledge/` 工作面。
5. 优先纳入当前 r10 使用频率最高的两部法律：
   - `LF_L002`《中华人民共和国安全生产法》
   - `LF_L001`《中华人民共和国消防法》
6. 为保持 succession 外键闭合，额外纳入两组现行有效标准端点：
   - `L008` → `L007`：GB 50140-2005 与 GB 55036-2022 的部分替代关系
   - `L025` → `L029`：GB 50016-2014（2018年版）与 GB 55037-2022 的部分替代关系
7. 迁入对应 law/lawVersion review sidecar 与所需 public evidence projection。
8. V3 `verification` 实际无 `method` 字段；review sidecar 已按真实 schema 处理为“不生成该字段”，未伪造元数据。
9. 使用 Git Data tree + commit 一次性写入，未逐文件人工提交。

## 本轮新增/修改文件

新增 `knowledge/` 核心骨架，共 33 个 JSON：

- `knowledge/manifest.json`：1
- `knowledge/laws/*.json`：6
- `knowledge/law-versions/*.json`：6
- `knowledge/reviews/laws/*.json`：6
- `knowledge/reviews/law-versions/*.json`：6
- `knowledge/evidence/*.json`：6
- `knowledge/successions/*.json`：2

本轮另更新：

- `docs/CHAT_HANDOFF.md`

未修改：

- `main`
- V3 SQLite
- fulltext SQLite
- `site-selection.json`
- production website
- 任何正式 V3 release

## Phase 6 core-laws-001 数据状态

`knowledge/manifest.json`：

- formatVersion：`4.0-alpha`
- batch：`core-laws-001`
- asOf：`2026-09-09`
- laws：6
- lawVersions：6
- successions：2
- evidence：6
- source SQLite SHA：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`

当前迁入 law IDs：

- `LF_L001`
- `LF_L002`
- `LF_L007`
- `LF_L008`
- `LF_L025`
- `LF_L029`

当前迁入 lawVersion IDs：

- `L001`
- `L002`
- `L007`
- `L008`
- `L025`
- `L029`

当前 succession：

- `LS_e7516d229b6de451e0fa1fb6`：`L008` → `L007`，`partially_replaces`
- `LS_75abaaec337577b1f419a8d8`：`L025` → `L029`，`partially_replaces`

尚未迁入 upcoming succession 端点；不得为了追求完整 succession 数量把 upcoming 当 active 当前依据。

## 本轮校验

本地生成阶段：

- JSON 可解析：通过
- selected laws：6
- selected current verified lawVersions：6
- successions：2
- public evidence：6
- entity/review 外键问题：0
- succession 端点断链：0
- duplicate entity ID：0
- 私有字段/路径扫描：0
- pending/upcoming 未被批量升级

提交前额外纠正：

- 删除不存在的 V3 `verification.method` 空字段，不向 V4 伪造元数据。

GitHub 保存：

- knowledge commit：`5cf400bae85a99e7d1edfb2c271c10f161e0495b`
- knowledge tree：`18a57b584aa2ad7d53d78df0274206ab86e447f7`
- branch update：fast-forward，未 force
- `knowledge/manifest.json` 已回读成功
- `knowledge/reviews/laws/LF_L002.json` 已回读成功，review/evidence/hash 字段完整且无 `method:null`

## 当前项目状态

Phase 1～5 已完成。

Phase 6 已正式建立 Git 版本控制的 `knowledge/` 维护面，但目前仅完成 `core-laws-001`；它不是完整 V4 knowledge，也不是 release。

当前不应修 V3 旧 gate failure，不应提前实现 Validator/Gate，也不应切生产。

## 未完成事项

### Phase 6 — 法规身份/版本继续迁移

Phase 5 共有 148 verified law、148 current verified lawVersion 可作为保守 current candidate；当前仅迁入 6/148。

后续应继续按可收口批次迁入剩余 verified law/current lawVersion 及 public evidence/review。

### Phase 6 — clause / hazard / link

法规基础批次完成后，再依次迁入：

- verified clause
- verified hazard
- verified、角色明确且适用性有佐证的 link
- 必需 public evidence
- review sidecar

必须保留 pending / superseded / inactive / r8 历史错误 / unclassified link / 效力不明 version，不为完成率强行升级。

## 下一轮第一步

**继续 Phase 6 `core-laws-002`：从尚未迁入的 verified law + current verified lawVersion 中，按当前 r10 使用频率优先选择下一批，并补齐对应 review/evidence；不得覆盖 `core-laws-001` 已有实体。**

下一轮完成该批次后必须：

1. 将 `knowledge/manifest.json` 改为累计数量，并记录新增 batch 信息；
2. 校验新旧 Stable ID 无重复/覆盖冲突；
3. 检查 lawVersion → law FK；
4. 扫描私有字段；
5. fast-forward 提交到 `chat-v4`；
6. 更新本 handoff；
7. 在法规核心批次尚未基本完成前，不提前吞 clause/hazard/link。

## 后续任务

- Phase 6：完成法规身份/版本核心迁移，再迁 clause → hazard → link
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

## 法规/标准待核验队列

当前不启动全量法规核验。Phase 6 后重点处理：

- 143 条 `ROLE_UNCLASSIFIED` active link 的逐条适用性与角色复核
- 11 个 `VERSION_EFFECTIVITY_UNCERTAIN` lawVersion 的版本/效力/日期补证
- 当前网站高频依据优先核验
- upcoming 版本只能进入法规知识，不得支撑当前 asOf hazard

## 风险 / 阻塞

1. Drive 最新 V3 Git 历史仍比 GitHub 远端 `data-verify-batch-003` 新；禁止从 GitHub 旧 V3 pipeline 直接重构生产代码。
2. 独立只读迁移器已绕过上述源码分叉，当前迁移数据本身不因此阻塞。
3. 143 条 active link 角色不明确，不得批量猜成 direct。
4. 11 个 lawVersion 效力/日期不足，保持 pending/quarantine。
5. r10 只能作对比/佐证，不能作为 V4 事实源。
6. 当前 `knowledge/` 仅为 Phase 6 部分迁移，不能作为正式 release 或生产数据源。
7. 当前无需要用户决策的不可逆问题。

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
