# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮必须先读本文件，再核对 GitHub 与 Google Drive 真实状态；冲突时以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 Codex V3 的 Stable ID、法规身份/版本、条款、隐患、link、evidence、release、网站与审计历史基础上，迁移到 Git-first、Chat 可长期维护的 V4 / Chat-first 架构。优先保证法规版本、条款原文、隐患内容、适用性与隐私正确；降低 SQLite、dependency hash 和本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— 完成
- Phase 2：V4 Chat-first 架构设计 —— 完成
- Phase 3：V4 门禁设计 —— 完成
- Phase 4：V3 → V4 数据映射 —— 完成
- Phase 5：V4 只读迁移原型 —— 完成并验收
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001～008 完成；54/54 保守 verified clause 完成；verified hazard 已开始，当前 12/642**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

本轮最终 data baseline（handoff 更新前）：`b1f7de0792f2fb54e46969a9770a96ce82282dd4`（`data: migrate Phase 6 hazards batch 002`）。本 handoff 更新提交位于其后；下一轮第一步必须重新读取 `chat-v4` 获取真实最终 HEAD，不得仅使用聊天记录。

关键线性数据提交：

- `dc53f388577ac112c97b2d6ec5a19f84226a486f` — clauses-004，完成 54 条 clause
- `d72551be5e1555cc9251f5067f69b30425a59a21` — hazards-001
- `b1f7de0792f2fb54e46969a9770a96ce82282dd4` — hazards-002

本轮曾因并发施工产生若干未挂分支的孤立候选 commit；不得把它们当作真实基线，也不得 force 挂载。所有正式写入均使用 `force=false` fast-forward。

### Google Drive

工作面：`ESH_Codex/work/safety-basis`

冻结母库 `source/master/safety.sqlite3`：

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok
- counts：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4

全文库 `source/library/fulltext.sqlite3`：size 21,864,448 bytes；SHA-256 `8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`。

最新候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`；hazards 242、laws 148、law_versions 150、clauses 52、links 269。r10 只作迁移佐证/对比，不是 V4 事实源。

当前生产选择仍为 `reviewed-20260909-r4`；不得自行切换。

## 本轮完成

### 1. 完成 conservative verified clause 主链

按照 Phase 5 既定保守规则，从冻结 V3 母库重新得到 54 条 clause 候选：`status=已核验 + identity_status=confirmed_locator + 最新 text review=passed + authoritative-public evidence + locator 非空`。按 Stable ID 分 4 批迁入：

- clauses-001：15 条
- clauses-002：15 条
- clauses-003：15 条
- clauses-004：9 条

合计 54/54。父 lawVersion 仅 6 个，均已存在；未扩张 verified 集合。条款 migration 完成后 manifest 为 clauses=54。

### 2. 开始 conservative verified hazard 主链

重新从 immutable 只读 SQLite 计算 hazard 候选，严格得到 642 条，条件为：

- V3 `hazards.status=已核验`
- `merged_into` 为空 / active lifecycle
- 最新 `entity_type=hazard, check_type=content` review = passed
- `verification_details.public_fields_reviewed=1`

证据分布：636 条对应 authoritative-public evidence，6 条对应 secondary evidence。不得把 secondary evidence 自动升级为 authoritative-public；是否需要更高证据等级留给后续核验/门禁处理，不因迁移本身改变 V3 内容 review 决策。

已迁：

- hazards-001：H002、H005、H013、H015、H016、H017
- hazards-002：H018、H019、H021、H022、H024、H025

共 12/642。每条均保留原 Stable ID、title、description、measures、category、conditions、note、mode、aliases、places、keywords；生成 content review sidecar，`reviewedContentHash` 使用 V4 canonical JSON 算法；`migratedFromV3Verification` 只保留真实存在的 id/reviewedAt/reviewer，不伪造 `method` 字段。

两批所需 evidence 均已在 `knowledge/evidence/`，未重复写入。

## 本轮修改文件

新增/修改包括：

- `knowledge/clauses/`：完成剩余 clause 批次至 54 条
- `knowledge/reviews/clauses/`：对应 54 条 clause review 完整闭合
- `knowledge/evidence/`：条款阶段仅补缺失 public evidence；当前累计 54
- `knowledge/hazards/`：新增 12 条 verified hazard
- `knowledge/reviews/hazards/`：新增 12 条 content review sidecar
- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

另有 `docs/PROJECT_PLAYBOOK.md` 在本轮并发施工中以独立 commit 添加；已保留，不覆盖。

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- Drive 母库 size/modified 与冻结基线一致，无版本漂移
- SQLite SHA-256 与冻结值一致；`integrity_check=ok`
- 54 条 clause 候选重新计算并与迁移结果数量闭合
- clause parent lawVersion 断链：0
- clause Stable ID 重新编号：0
- hazard 保守候选重新计算：642
- hazard evidence tier：authoritative-public 636；secondary 6
- hazards-001/002：title、description、measures 均非空；lifecycle active；无 merged hazard
- hazard review 均来自最新 passed content review；`public_fields_reviewed=1`
- 所有正式 Git 写入均 fast-forward、`force=false`
- 未迁入私有 `snapshot_ref` / legacy payload 等字段

## 当前项目状态

`knowledge/` 当前正式累计：

- laws：43
- current verified lawVersions：43
- verified clauses：54 / 54 conservative clause set
- verified hazards：12 / 642 conservative hazard set
- public/structured evidence：54
- successions：2
- verified links：尚未开始正式 Phase 6 迁入

Phase 5 保守 candidate 总量仍为：law 148、current lawVersion 148、clause 54、hazard 642、link 179。

剩余约 105 组 catalogue law/current lawVersion 不再阻塞 clause/hazard/link 主链；可在 Phase 6 后续按价值补充。

## 未完成事项

### Phase 6 — verified hazard

剩余 630 条 conservative verified hazard。必须保持同一筛选规则按 Stable ID 稳定排序分批迁移，不得为提高完成率扩大 verified 集合。注意 6 条 secondary-evidence hazard：迁移时如按 Phase 5 content review 规则保留 verified，必须原样记录 evidence tier，禁止升级证据等级。

### Phase 6 — verified link

Phase 5 conservative candidate 179 条。必须保持 r8 禁令：仅角色明确、适用性 review 通过并有 r10 佐证的 link 才可进入 verified；`ROLE_UNCLASSIFIED` 保持 pending。

### Phase 6 — catalogue law/current version

仍有约 105 组 verified/current lawVersion 未迁入，可在主链迁移间隙按高价值场景补充，不阻塞 hazard/link 主链。

## 下一轮第一步

**继续 Phase 6 `hazards-003`：重新打开冻结 SQLite 的 immutable 只读连接，按与本文件完全相同的 642 条 conservative hazard 规则重算候选；排除 `knowledge/hazards/` 已存在的 12 个 Stable ID，从剩余集合按 Stable ID 取下一批。每条生成 hazard JSON + content review sidecar，只补缺失 evidence；迁移前检查 title/description/measures 非空、active lifecycle、review=passed、public_fields_reviewed=1，迁移后检查重复 ID、公开字段泄漏、hash 和 manifest 计数。Git 写入必须在最新 HEAD 上 `force=false` fast-forward；若分支并发前移，重新读真实 HEAD 后重建，绝不 force。**

## 后续任务

1. Phase 6：分批完成剩余 630 条 verified hazard。
2. Phase 6：迁移 179 条 conservative verified link。
3. Phase 6：按价值补充剩余 catalogue law/current version。
4. Phase 7：法规与标准核验框架。
5. Phase 8：历史报告条款重新审阅。
6. Phase 9：V4 Validator。
7. Phase 10：V4 Gate。
8. Phase 11～16：网站构建、候选 release、V3/V4 对比、差异修复、最终验收。
9. Phase 17：仅在用户明确批准后生产切换。

## 法规/标准待核验队列

- 2026 年新《中华人民共和国危险化学品安全法》生效后，对既有危化框架法规的继续适用/替代边界，留待 Phase 7 用当前官方来源专项核验。
- 6 条 hazard 的迁移 evidence 为 secondary；后续在进入发布链前按 V4 evidence/gate 规则评估是否需要补强证据。
- Phase 6 当前只迁移 V3 已核验资产，不启动无差别全库新核验。

## 风险 / 阻塞

- r8 历史质量事故禁令持续有效：禁止批量假定 link/条款适用性正确。
- 本轮出现多次并发分支前移；已通过每次写入前重读 HEAD、只允许 fast-forward、绝不 force 的方式避免覆盖。下一轮继续执行同一并发安全策略。
- `tools/v4/migrate_v3.py` 当前 review 生成代码中仍可见对 V3 verification `method` 字段的引用，但实际 V3 verification schema没有 `method` 列；手工正式迁移继续不写该字段。此代码问题留待合适的独立代码修复单元处理，不能伪造数据绕过。
- 当前无需要用户决策的阻塞。

## 用户待决策事项

无。生产切换尚未到阶段，不能自行执行。

## 明确禁止事项

- 不修改 `main`
- 不正式切换生产网站/Pages 数据源
- 不覆盖冻结 V3 SQLite、fulltext、正式 release
- 不恢复 r8 错误关联
- 不批量把 pending/rejected/merged/invalid 自动改为 verified
- 不因关键词相似自动核验 link 适用性
- 不伪造法规、版本、条款、原文、时效、证据等级或 review 元数据
- 不因缺完整标准全文阻断已可靠核验的局部条款
- 不公开 Drive 私有路径、`snapshot_ref`、legacy payload 或其他私有资料
- 不 force 推进 `chat-v4`；并发冲突时必须重新基于真实 HEAD 构建
