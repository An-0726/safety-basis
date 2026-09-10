# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮必须先读取本文件，再核对 GitHub 与 Google Drive 真实状态；冲突时以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 新窗口续接协议

每次新开窗口或重新接手本项目，必须按以下顺序判断真实断点，**不能只相信本文件里写的进度数字**：

1. 先读取 `docs/PROJECT_PLAYBOOK.md` 和 `docs/CHAT_HANDOFF.md`。
2. 读取 `chat-v4` 当前最新 HEAD。
3. 查询最近一次修改 `docs/CHAT_HANDOFF.md` 的 commit，并与当前 HEAD 比较提交时间和祖先关系。
4. 如果 HEAD 晚于 handoff commit，检查 handoff commit 之后的相关 commits，重点核对 `knowledge/manifest.json`、实际实体文件、review sidecar 和 evidence。
5. **实际 GitHub 文件状态和最新有效 commit 优先于 handoff 文本。** 实际进度更靠后时，以实际状态继续并在本轮结束前修正本文件。
6. 每个有效施工单元先提交 data/code 成果并校验，再单独更新本 handoff；记录最新 data commit、累计数量、未完成事项、风险和下一步。
7. 写入前再次读取 HEAD。若分支前移，重新基于最新 HEAD 判断差集；只允许非 force 安全前移，禁止旧 handoff/旧本地状态覆盖新成果。

判断链：**HEAD → handoff 最后 commit → 中间 commits → manifest/实际文件**。

## 当前总目标

在保留 Codex V3 的 Stable ID、法规身份/版本、条款、隐患、link、evidence、release、网站与审计历史基础上，迁移到 Git-first、Chat 可长期维护的 V4 / Chat-first 架构。优先保证法规版本、条款原文、隐患内容、适用性和隐私正确；降低 SQLite、dependency hash、本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— 完成
- Phase 2：V4 Chat-first 架构 —— 完成
- Phase 3：V4 门禁设计 —— 完成
- Phase 4：V3 → V4 数据映射 —— 完成
- Phase 5：只读迁移原型 —— 完成并验收
- Phase 6：迁移现有有效知识 —— **进行中：core-laws-001～008 完成；54/54 conservative verified clause 完成；130/642 conservative verified hazard 完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

本轮最新 data commit：`be45c0e57257ef864302b5300dc3ddf7ad58cff5`（`data: migrate Phase 6 hazards batch 006 (100)`）。本 handoff commit 位于其后；下一轮仍必须重新读取 `chat-v4` 的真实 HEAD。

关键提交：

- `dc53f388577ac112c97b2d6ec5a19f84226a486f` — clauses-004，54/54 conservative clause 完成
- `491c407672d64d149d5f90ed6d8c5d4dd29c7db6` — `docs/PROJECT_PLAYBOOK.md`
- `e12cfc39d8efccd4b9d52660cb2ebe199c492d55` — hazards-005，累计 30/642
- `373a9d9ccbfca0abce2e90d19ae5ab81310e0095` — 固化 HEAD-first 续接协议
- `be45c0e57257ef864302b5300dc3ddf7ad58cff5` — hazards-006，单批 100 条，累计 130/642

正式分支推进只允许 fast-forward。未挂到 `chat-v4` 的候选 tree/孤立 commit 不是项目真实基线。

### Google Drive / V3 冻结基线

工作面：`ESH_Codex/work/safety-basis`

`source/master/safety.sqlite3`：

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok
- counts：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4

`source/library/fulltext.sqlite3`：21,864,448 bytes；SHA-256 `8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`。

最新可靠 V3 候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`；hazards 242、laws 148、law_versions 150、clauses 52、links 269。r10 仅作迁移佐证/差异比较，不是 V4 事实源。生产选择仍为 `reviewed-20260909-r4`，不得自行切换。

## 本轮完成

完成 `hazards-006` 大批次迁移。冻结母库按既定 conservative hazard 规则重算候选仍为 642 条：

- `hazards.status=已核验`
- lifecycle active 且 `merged_into` 为空
- 最新 `entity_type=hazard/check_type=content` review=`passed`
- `verification_details.public_fields_reviewed=1`

本批固定取 Stable-ID 排序后的 **第 31～130 条，共 100 条**；首条 `H051`，末条 `H_22D804731C0D4F90A6BF2A83CD`。迁移保持 V3 Stable ID 和既定公开字段，不在 Phase 6 顺手改写历史 hazard 文本或把 content verified 扩大解释为 basis/link verified。

本批 100 条共引用 39 个 evidence ID，其中 2 个复用现有 evidence，37 个为当前 V4 缺失的 public evidence 并补入 `knowledge/evidence/`；新增 37 个 evidence 均为 authoritative-public 投影，不包含 V3 私有 `snapshot_ref`。

## 本轮修改文件

本轮 data commit 共 238 个预期路径变化：

- `knowledge/hazards/`：新增 100 个 hazard JSON
- `knowledge/reviews/hazards/`：新增 100 个 content review sidecar
- `knowledge/evidence/`：新增 37 个 public evidence JSON
- `knowledge/manifest.json`：更新 1 个
- `docs/CHAT_HANDOFF.md`：本交接 commit 单独更新

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站/Pages 数据源。

## 本轮校验

- 本批候选数量：100；固定区间：31～130 / 642
- 首尾 Stable ID：`H051` → `H_22D804731C0D4F90A6BF2A83CD`
- 100/100 hazard 满足 conservative 候选规则
- 100/100 `reviewedContentHash` 按 V4 canonical JSON 重算匹配
- title / description / measures 必填检查通过
- active / non-merged 检查通过
- batch evidenceRefs：39 个；复用 2；新增 37
- 新增 evidence public 投影私有字段扫描：`snapshot_ref`、`storage_ref`、`legacy_payload`、`raw_payload`、`../archive`、`ESH_Codex`、Drive 私有路径均 0 命中
- SQLite SHA-256 与冻结基线一致；`integrity_check=ok`
- data commit 与父提交比较：ahead_by=1、behind_by=0
- data commit 变更路径仅限 hazard/review/evidence/manifest
- `knowledge/manifest.json` 回读：batch=`hazards-006`；hazards=130；evidence=91
- 首条与末条 hazard 已从 `chat-v4` 回读确认落盘
- 曾有一次错误的 handoff update 请求因 SHA 不匹配返回 409，被 GitHub 拒绝，未产生任何仓库修改；随后按正确流程继续

## 当前项目状态

`knowledge/` 当前累计：

- laws：43
- current verified lawVersions：43
- verified clauses：54 / 54 conservative set
- verified hazards：130 / 642 conservative set
- evidence：91
- successions：2
- verified links：0 / 179 conservative candidate，尚未开始正式迁入

Phase 5 conservative candidate 总量：law 148、current lawVersion 148、clause 54、hazard 642、link 179。

## 未完成事项

1. Phase 6：剩余 512 条 conservative verified hazard 继续大批次迁移。
2. Phase 6：179 条 conservative verified link；必须逐条保留角色/适用性 review，`ROLE_UNCLASSIFIED` 不得自动通过。
3. Phase 6：按实际价值补充剩余约 105 组 catalogue law/current version；不阻塞 hazard/link 主链。
4. Phase 6 完整校验后才能进入 Phase 7。

## 下一轮第一步

**执行 `hazards-007`：按照新窗口续接协议先比较 HEAD / handoff commit / manifest / 实际文件；若真实断点仍为 130/642，则从冻结 SQLite 按同一 conservative 规则重算固定 642 条候选，取 Stable-ID 排序第 131～230 条，共 100 条。生成 100 hazard JSON + 100 content review sidecar，仅补缺失 public evidence；校验 reviewedContentHash、active/non-merged、必填字段、evidenceRefs、私有字段泄漏和 manifest 计数。data/code 先提交并复核，再单独更新 handoff。写 Git 前必须再次读取 HEAD，只允许非 force fast-forward。**

## 后续任务

1. `hazards-007` 起继续以 100 条/批为默认机械迁移粒度；最后余数单独收口。
2. 完成全部 642 conservative verified hazard。
3. 迁移/复核 179 条 conservative verified link；link 属于高风险语义适用性，不沿用 100 条机械批量自动通过策略。
4. 按价值补 catalogue law/current version。
5. Phase 7 法规与标准核验框架。
6. Phase 8 历史报告条款重审。
7. Phase 9 Validator；Phase 10 Gate。
8. Phase 11～16 网站构建、V4 candidate release、V3/V4 对比、差异修复和最终验收。
9. Phase 17 仅经用户明确批准后切生产。

## 法规/标准待核验队列

- 2026 年新《中华人民共和国危险化学品安全法》生效后与既有危化框架法规的继续适用/替代边界：Phase 7 用当前官方来源专项核验。
- conservative 642 中存在少量 secondary evidence 对象：进入发布链前按 V4 evidence/gate 规则补强或保留 review requirement。
- 部分历史 hazard 的 `conditions`/`note` 仍含旧报告式依据文字、旧标准线索或粗糙表述。本 Phase 仅保真迁移，不代表这些依据已获得 V4 link/applicability 终审；后续 link/gate 必须阻断未终审依据。

## 风险 / 阻塞

- r8 历史质量事故禁令持续有效：禁止批量假定 link/条款适用性正确。
- 100 条大批量仅用于确定性的 hazard content 迁移；不能将同一规模直接套用于 link 适用性核验。
- `tools/v4/migrate_v3.py` 仍有读取不存在 V3 verification `method` 字段的代码风险；正式迁移不伪造该字段，后续独立代码单元修复。
- 当前无需要用户决策的真实阻塞。

## 用户待决策事项

无。尚未进入生产切换阶段。

## 明确禁止事项

- 不修改 `main`
- 不正式切换生产网站/Pages 数据源
- 不覆盖冻结 V3 SQLite、fulltext、正式 release
- 不恢复 r8 错误关联
- 不批量把 pending/rejected/merged/invalid 自动改为 verified
- 不因关键词相似自动核验 link 适用性
- 不把 hazard content verified 等同于 basis/link verified
- 不伪造法规、版本、条款、原文、时效、证据等级或 review 元数据
- 不公开 Drive 私有路径、`snapshot_ref`、legacy payload
- 不 force 推进 `chat-v4`
