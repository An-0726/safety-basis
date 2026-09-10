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
- Phase 6：迁移现有有效知识 —— **进行中：core-laws-001～008 完成；54/54 conservative verified clause 完成；210/642 conservative verified hazard 完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

本轮接手时真实 HEAD：`4f1b2724aaa7f16fd247e56697fafb77529184dd`（`docs: hand off hazards batch 007b1`），对应 160/642。

本轮新增正式 data commits：

- `83a2065caad22b86002927434f6ed3dd2ab8f488` — `data: continue Phase 6 hazards batch 007b (161-170)`
- `ef4c1e8e18a885c0b7c93b31db304e76623adc63` — `data: continue Phase 6 hazards batch 007b (171-180)`
- `eadd5fc0fe8746da0fb826ae598c9523184a009b` — `data: continue Phase 6 hazards batch 007b (181-190)`
- `c4aafbddd8dc5f717c059e3ccc0dbde378944109` — `data: continue Phase 6 hazards batch 007b (191-200)`
- `5780b194fee12e6d699b0d7f9e60fa6d43d22812` — `data: continue Phase 6 hazards batch 007b (201-210)`
- `954aff57ea1b547010fce4e39b9e153b4ddf3947` — restore existing evidence formatting after batch tree writes; semantic evidence content unchanged
- `7fc272be0c9824e5772f709d669ed370c5b02beb` — `data: sync manifest after hazards batch 007b2`

正式分支推进仅使用 non-force fast-forward / GitHub contents API 正常提交。未修改 `main`。

### Google Drive / V3 冻结基线

工作面：`ESH_Codex/work/safety-basis`

`source/master/safety.sqlite3`：

- Drive file id：`1W1GnR53GGPC26dCOyRjmYdz1R2Zi8I8L`
- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok
- counts：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4

`source/library/fulltext.sqlite3`：21,864,448 bytes；SHA-256 `8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`。

最新可靠 V3 候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`。生产选择仍为 `reviewed-20260909-r4`，不得自行切换。

## 本轮完成

### 1. HEAD-first 恢复断点

启动时重新读取 `chat-v4` HEAD、`PROJECT_PLAYBOOK.md`、handoff、manifest，并重新定位冻结 V3 SQLite。确认没有并发前移，真实断点仍为 **160/642**，因此未重复已有批次。

### 2. 重新计算 conservative verified hazard 集合

从冻结 SQLite 只读重算，固定集合仍为 **642**，规则不变：

- `hazards.status=已核验`
- active，`merged_into` 为空
- 最新 `entity_type=hazard / check_type=content` verification=`passed`
- 对应 `verification_details.public_fields_reviewed=1`
- Stable ID 排序

本轮迁移固定排序第 **161～210 条，共50条**。首条：`H_366610E8AA084C77844EFFBAAD`；末条：`H_45A066D644BE4A0992ECC95E1B`。

### 3. 数据迁移

新增 50 个 hazard JSON、50 个 content review sidecar；按 review evidenceRefs 仅补齐缺失的公开 evidence。GitHub compare 从本轮基线 `4f1b2724...` 到最终 data commit `5780b194...` 显示新增 **37 个 evidence JSON**。

本轮批次标记：`hazards-007b2`。

历史 hazard `conditions`、`measures`、旧标准线索按 Phase 6 原则保真迁移；本轮只迁移已经通过 V3 content review 的 hazard 内容，不把 hazard content verified 扩大解释为法规条款或 link/applicability 已终审。

### 4. 重复 evidence 格式修复

批量 tree 中重复带入已存在的 `E_0d32c4cce961a92a4907df8e724d162ba60113e84300c1c90fd8b5e72104c0ab`，语义内容完全一致但格式由 pretty JSON 变为 compact JSON。GitHub compare 将其标记为 modified。已在 commit `954aff57...` 恢复为本轮基线原格式，因此该 evidence 不构成有效内容修改，也不计入 evidenceAdded。

## 本轮修改文件

- `knowledge/hazards/`：新增 50 个 hazard JSON
- `knowledge/reviews/hazards/`：新增 50 个 content review sidecar
- `knowledge/evidence/`：净新增 37 个 public evidence JSON
- `knowledge/manifest.json`：新增 `hazards-007b2`，累计更新为 hazards=210、evidence=145
- `docs/CHAT_HANDOFF.md`：本交接更新

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站/Pages 数据源。

## 本轮校验

- conservative hazard 集合重算：642，未扩大 verified 范围
- 本轮固定区间：161～210，共50条
- 50/50 active、non-merged、latest content review passed、`public_fields_reviewed=1`
- 50/50 title / description / measures 非空
- 50/50 `reviewedContentHash` 按 V4 canonical JSON 生成并绑定对应 hazard 内容
- review sidecar 未伪造 V3 不存在的 `method` 字段
- GitHub compare：50 个 hazard 新增、50 个 review 新增、37 个 evidence 净新增
- 重复 evidence 仅格式变化，已恢复为基线内容
- manifest 已同步为 batch=`hazards-007b2`、hazards=210、evidence=145
- 本轮 data branch 更新全部采用 `force=false`，未发生并发覆盖
- 冻结 V3 DB 未修改；生产 release / Pages 未切换

## 当前项目状态

`knowledge/` 当前累计：

- laws：43
- current verified lawVersions：43
- verified clauses：54 / 54 conservative set
- verified hazards：210 / 642 conservative set
- evidence：145
- successions：2
- verified links：0 / 179 conservative candidate，尚未开始正式迁入

Phase 5 conservative candidate 总量：law 148、current lawVersion 148、clause 54、hazard 642、link 179。

## 未完成事项

1. Phase 6：剩余 **432** 条 conservative verified hazard。
2. `hazards-007` 原定第131～230区间尚剩第 **211～230 条，共20条**。
3. Phase 6：179 条 conservative verified link；必须逐条做角色/适用性 review，禁止把 hazard 的确定性批迁策略用于 link。
4. Phase 6：按价值补充剩余 catalogue law/current version；不阻塞 hazard/link 主链。
5. Phase 6 完整校验后才能进入 Phase 7。

## 下一轮第一步

**先按 HEAD-first 协议核对 `chat-v4` HEAD、handoff、manifest 和实际文件。若真实断点仍为210/642，则先完成 hazards-007 剩余第211～230条共20条；完成后继续下一确定性 hazard 批次。生成 hazard JSON + content review sidecar，仅补缺失 public evidence；校验 reviewedContentHash、active/non-merged、必填字段、evidenceRefs、隐私扫描和 manifest。data/code 先提交，校验后再更新 handoff；写 Git 前再次读 HEAD，只允许 non-force fast-forward。**

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
- 历史 hazard `conditions`/`note` 中旧报告式依据文字、旧标准线索、粗糙整改表述：Phase 6 只保真迁移，不视为 link/applicability 已终审。

## 风险 / 阻塞

- r8 历史质量事故禁令持续有效：禁止批量假定 link/条款适用性正确。
- 大批量确定性迁移仅适用于 hazard content，不用于 link 适用性自动核验。
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
