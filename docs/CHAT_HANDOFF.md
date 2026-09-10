# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮必须先读取本文件，再核对 GitHub 与 Google Drive 真实状态；冲突时以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 新窗口续接协议

每次接手必须按以下顺序恢复真实断点：

1. 读取 `docs/PROJECT_PLAYBOOK.md` 和本文件。
2. 读取 `chat-v4` 当前 HEAD。
3. 比较本文件最近修改 commit 与 HEAD 的祖先关系和后续 commits。
4. 核对 `knowledge/manifest.json`、实际实体文件、review sidecar、evidence。
5. **实际 GitHub 文件状态与最新有效 commit 优先于 handoff 文本。**
6. data/code 先提交并校验，再单独更新 handoff。
7. 写入前再次读取 HEAD；分支前移时重算差集，只允许非 force fast-forward。

判断链：**HEAD → handoff 最后 commit → 中间 commits → manifest/实际文件**。

## 当前总目标

在保留 Codex V3 的 Stable ID、法规身份/版本、条款、隐患、link、evidence、release、网站与审计历史基础上，迁移到 Git-first、Chat 可长期维护的 V4 / Chat-first 架构。优先保证法规版本、条款原文、隐患内容、适用性和隐私正确；降低 SQLite、dependency hash、本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— 完成
- Phase 2：V4 Chat-first 架构 —— 完成
- Phase 3：V4 门禁设计 —— 完成
- Phase 4：V3 → V4 数据映射 —— 完成
- Phase 5：只读迁移原型 —— 完成并验收
- Phase 6：迁移现有有效知识 —— **进行中：core-laws-001～008 完成；54/54 conservative verified clause 完成；150/642 conservative verified hazard 完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

本轮新增 hazard data commit：`4b636ccc160bf4596ee81bbe5a28e77a2d4ed428`（`data: migrate Phase 6 hazards batch 007a (20)`）。

本轮 manifest sync commit：`8e9a81a1e654295e0de9ca5157dc2182f3066d14`（`data: sync manifest after hazards batch 007a`）。

前一完整大批次：`be45c0e57257ef864302b5300dc3ddf7ad58cff5`（hazards-006，固定候选第31～130条，共100条）；其 handoff commit 为 `37814e7221da355b1d15ae34fe23099afc30c878`。

正式分支推进只允许 fast-forward。未挂到 `chat-v4` 的候选 tree/孤立 commit 不属于真实基线。本轮曾因并发前移产生孤立候选 commit `00fe2817bb0f3e34b265a02c7b4d85d26aa1e065`，非 fast-forward 更新被 GitHub 422 拒绝，该 commit 未进入 `chat-v4`，不得作为后续基线。

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

最新可靠 V3 候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`。生产选择仍为 `reviewed-20260909-r4`，不得自行切换。

## 本轮完成

### 1. 恢复并核对真实状态

启动时 handoff 一度仍写 30/642，但实际 `chat-v4` 已被并发施工推进。按 HEAD-first 规则核对后，确认真实正式状态已由 hazards-006 推进到 **130/642**，manifest 与 handoff 均已同步；未重复覆盖该成果。

### 2. 继续 Phase 6：hazards-007a

从冻结 SQLite immutable/只读重算 conservative verified hazard 集合，总量仍为 642，规则不变：

- `hazards.status=已核验`
- active，`merged_into` 为空
- 最新 `entity_type=hazard / check_type=content` review=`passed`
- `verification_details.public_fields_reviewed=1`

本轮固定迁移排序第 **131～150 条，共20条**，作为 `hazards-007a` 独立可恢复单元。首条：`H_2303005CE94D49BD88F75C7DC7`；末条：`H_311325FC449A451C8D1255AD60`。

迁移 20 个 hazard JSON、20 个 content review sidecar；本批引用 14 个 evidence ID，其中 `E_0d32c4cce961a92a4907df8e724d162ba60113e84300c1c90fd8b5e72104c0ab` 已存在，新增 13 个 public evidence。新增 evidence 均按 V4 public projection 生成，不公开 V3 `snapshot_ref`。

本批只迁 hazard content 已核验事实，不代表历史 `conditions` 中写到的法规/标准依据已经完成 V4 link/applicability 终审。历史粗糙表述、旧标准线索在 Phase 6 保真迁移，后续 link/gate 必须独立判断。

## 本轮修改文件

- `knowledge/hazards/`：新增 20 个 hazard JSON
- `knowledge/reviews/hazards/`：新增 20 个 content review sidecar
- `knowledge/evidence/`：新增 13 个 public evidence JSON
- `knowledge/manifest.json`：新增 `hazards-007a` 批次，累计计数更新
- `docs/CHAT_HANDOFF.md`：本交接更新

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站/Pages 数据源。

## 本轮校验

- conservative hazard 总量重算：642，未扩大 verified 集合
- hazards-001～006 已有前130条与冻结排序一致
- hazards-007a 固定区间：131～150，共20条
- 20/20 active、non-merged、latest content review passed、`public_fields_reviewed=1`
- 20/20 title / description / measures 非空
- 20/20 `reviewedContentHash` 按 V4 canonical JSON 重算匹配
- evidenceRefs 共14个；复用1，新增13
- 新增13个 evidence 均为 authoritative-public 投影
- 私有字段/路径扫描：`snapshot_ref`、`storage_ref`、`legacy_payload`、`raw_payload`、`ESH_Codex`、`../archive` 等 0 命中
- SQLite `integrity_check=ok`，冻结母库文件未修改
- hazard data commit 通过 `force=false` fast-forward 写入 `chat-v4`
- `knowledge/manifest.json` 已同步为 batch=`hazards-007a`，hazards=150，evidence=104
- 并发前移时一次旧基线 update_ref 被 GitHub 422 拒绝，未覆盖任何正式成果；随后按最新 HEAD 续接

## 当前项目状态

`knowledge/` 当前累计：

- laws：43
- current verified lawVersions：43
- verified clauses：54 / 54 conservative set
- verified hazards：150 / 642 conservative set
- evidence：104
- successions：2
- verified links：0 / 179 conservative candidate，尚未开始正式迁入

Phase 5 conservative candidate 总量：law 148、current lawVersion 148、clause 54、hazard 642、link 179。

## 未完成事项

1. Phase 6：剩余 **492** 条 conservative verified hazard。
2. `hazards-007` 尚未完成其原定第131～230区间；本轮只完成 `007a` 第131～150条，剩余第151～230条共80条。
3. Phase 6：179 条 conservative verified link；必须逐条保持角色/适用性 review，禁止沿用 hazard 机械批量自动通过策略。
4. Phase 6：按价值补充剩余约105组 catalogue law/current version；不阻塞 hazard/link 主链。
5. Phase 6 完整校验后才能进入 Phase 7。

## 下一轮第一步

**先按 HEAD-first 协议核对 `chat-v4` HEAD、handoff、manifest 和实际文件。若真实断点仍为150/642，则继续 `hazards-007b`：从固定642候选排序第151条开始，优先完成第151～230条剩余80条；生成 hazard JSON + content review sidecar，仅补缺失 public evidence，并按同样规则校验 hash、active/non-merged、必填字段、evidenceRefs、隐私扫描和 manifest。data/code 先提交，校验后再更新 handoff；写 Git 前再次读 HEAD，只允许非 force fast-forward。**

## 后续任务

1. 完成全部642 conservative verified hazard。
2. 迁移/复核179条 conservative verified link；适用性逐条判断。
3. 按价值补 catalogue law/current version。
4. Phase 7 法规与标准核验框架。
5. Phase 8 历史报告条款重审。
6. Phase 9 Validator；Phase 10 Gate。
7. Phase 11～16 网站构建、候选 release、V3/V4 对比、差异修复和最终验收。
8. Phase 17 仅经用户明确批准后切生产。

## 法规/标准待核验队列

- 2026年新《中华人民共和国危险化学品安全法》生效后与既有危化框架法规的继续适用/替代边界：Phase 7 用当前官方来源专项核验。
- conservative 642 中少量 secondary evidence：进入发布链前按 V4 evidence/gate 规则补强或保留 review requirement。
- 历史 hazard `conditions`/`note` 中的旧报告式依据文字、旧标准线索、粗糙整改表述：本 Phase 只保真迁移，不视为 link/applicability 已终审。

## 风险 / 阻塞

- r8 历史质量事故禁令持续有效：禁止批量假定 link/条款适用性正确。
- 100条级批量只适用于确定性 hazard content 迁移，不用于 link 适用性自动核验。
- `tools/v4/migrate_v3.py` 仍存在读取 V3 verification 不存在的 `method` 字段风险；正式迁移不伪造该字段，后续独立代码单元修复。
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
