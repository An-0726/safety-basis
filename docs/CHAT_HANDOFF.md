# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮必须先读本文件，再核对 GitHub 与 Google Drive 真实状态；冲突时以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 Codex V3 的 Stable ID、法规身份/版本、条款、隐患、link、evidence、release、网站与审计历史的基础上，迁移到 Git-first、Chat 可长期维护的 V4 / Chat-first 架构。优先保证法规版本、条款原文、隐患内容、适用性与隐私正确；降低 SQLite、dependency hash 和本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— 完成
- Phase 2：V4 Chat-first 架构设计 —— 完成
- Phase 3：V4 门禁设计 —— 完成
- Phase 4：V3 → V4 数据映射 —— 完成
- Phase 5：V4 只读迁移原型 —— 完成并验收
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001、core-laws-002 已完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`

禁止直接修改 `main`。

## 当前真实基线

### GitHub

- 本轮起始 HEAD：`53699fd84ad54654a1b62ac904a16912f1c7e87b`
- Phase 6 core-laws-002 data commit：`2180f07fd3abe54ac5d366b8d2f5eb600f314301`
- 本 handoff 更新提交位于该 commit 之后；下一轮必须重新读取 `chat-v4` HEAD 获取最终 SHA。

重要历史提交：

- Phase 4：`11b6f65f7e8004a2fcdcde2ed7f506dcf929d38e`
- Phase 5 迁移器：`b509db266864771cd2f707ea3da3b3f4ca11c041`
- Phase 5 验收报告：`15cd827fbbee11e7c9e3501ed9573942d89af2c3`
- Phase 5 交接：`b2d0f4e0384f54a1c51342f4ae3a7683351e8c41`
- Phase 6 core-laws-001：`5cf400bae85a99e7d1edfb2c271c10f161e0495b`

### Google Drive

工作面：`ESH_Codex/work/safety-basis`

最新冻结母库仍为：`source/master/safety.sqlite3`

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok（Phase 5 已确认）

关键数量：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4。

状态：hazards 已核验 662；clauses 已核验 95；links 已核验 790 / 已失效 1502；law_versions 现行有效 156 / 即将生效 2 / 待核验 3。

全文库：`source/library/fulltext.sqlite3`

- size：21,864,448 bytes
- SHA-256：`8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`
- documents：65；FTS records：16,863

最新候选 release：`reviewed-20260909-r10`

- releaseHash：`dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`
- hazards 242；laws 148；law_versions 150；clauses 52；links 269

r10 只作迁移佐证/对比，不是 V4 事实源。r8 为历史质量事故版本，不得恢复。

当前生产选择仍为 `reviewed-20260909-r4`；不得自行切换。

## 架构冻结原则

正式设计文件：

- `docs/ARCHITECTURE_V4_CHAT_FIRST.md`
- `docs/GATE_V4.md`
- `docs/MIGRATION_V3_TO_V4.md`

长期规则：Stable ID 原样保留；V4 日常维护源为 Git `knowledge/`；SQLite 保留为 V3 冻结/迁移/分析资产；review sidecar 使用 `reviewedContentHash`；link review 保留 context hash；不恢复通用 dependencyHash 全图级联；upcoming/repealed 不得支撑当前 hazard；`primary`/候选角色不得自动映射 direct；私有 snapshot 路径不得进入公开 knowledge。

## 本轮完成

完成 Phase 6 `core-laws-002`：

1. 从 `docs/CHAT_HANDOFF.md` 恢复现场并核对 GitHub/Drive。
2. 确认 `chat-v4` 起始 HEAD 与 handoff 一致，Drive `safety.sqlite3` 大小/修改时间未变化。
3. 只读冻结 SQLite，并以 r10 当前 link 使用频率排序尚未迁入法规。
4. 排除 core-laws-001 后，r10 中剩余仍有正使用频率的 law 恰好 4 部：
   - `LF_L023`《危险废物贮存污染控制标准》：30 个 r10 link
   - `LF_L014`《中华人民共和国特种设备安全法》：9
   - `LF_META_0C856E722AF7822CA5E9415D`《易制毒化学品管理条例》：1
   - `LF_L020`《江苏省安全生产条例》：1
5. 四部法规身份及对应 current lawVersion 均确认存在最新 `passed` identity/version review，并绑定官方 public evidence；未混入 upcoming/unknown。
6. 新增 4 law、4 current lawVersion、8 review sidecar、4 public evidence；累计更新 manifest。
7. 使用 Git Data tree 生成单一数据提交并 fast-forward `chat-v4`，未 force。

## 本轮修改文件

新增：

- `knowledge/laws/LF_L023.json`
- `knowledge/laws/LF_L014.json`
- `knowledge/laws/LF_META_0C856E722AF7822CA5E9415D.json`
- `knowledge/laws/LF_L020.json`
- `knowledge/law-versions/L023.json`
- `knowledge/law-versions/L014.json`
- `knowledge/law-versions/LV_META_8982B9B15AF4365DE59CDFCE.json`
- `knowledge/law-versions/L020.json`
- 对应 `knowledge/reviews/laws/` 4 个文件
- 对应 `knowledge/reviews/law-versions/` 4 个文件
- 对应 `knowledge/evidence/` 4 个文件

修改：

- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- 目标 law 均为 identity_status=confirmed 且最新 identity review=passed：通过
- 目标 lawVersion 均为现行有效、已核验、有 effectiveDate、最新 version review=passed：通过
- lawVersion → law FK：0 断链
- Stable ID 与 core-laws-001：0 冲突/覆盖
- 新增 evidence：4 个唯一 ID
- 所有新增 JSON：可解析
- `reviewedContentHash`：按 V4 canonical JSON 重新计算并写入
- 私有字段/路径扫描：0 命中（无 snapshot_ref、legacy_payload、raw_payload、`../archive`、Drive 私有路径）
- Git tree：`a689c5d93bb35168d1a2ce72e02d432ea1c02873`
- data commit：`2180f07fd3abe54ac5d366b8d2f5eb600f314301`
- branch update：fast-forward，force=false
- `knowledge/manifest.json` 回读成功：batch=`core-laws-002`，累计 laws=10、lawVersions=10、evidence=10、successions=2

## 当前项目状态

`knowledge/` 当前累计：

- laws：10
- current verified lawVersions：10
- public evidence：10
- successions：2
- clauses/hazards/links：尚未开始正式 Phase 6 迁入

Phase 5 的保守 candidate 总量仍为 law 148、current lawVersion 148、clause 54、hazard 642、link 179。当前 laws/lawVersions 仅完成 10/148；不能视为 Phase 6 完成。

## 未完成事项

### Phase 6 — 法规身份/版本

剩余约 138 个 verified law/current lawVersion 尚未进入正式 `knowledge/`。r10 中“正 link 使用频率”的剩余集合已在 core-laws-002 后耗尽，因此后续批次需采用稳定、可解释的次级排序，不能为了数量随意挑选。

### Phase 6 — clause / hazard / link

法规基础批次达到可接受覆盖后，再依次迁入 verified clause → verified hazard → 角色明确且适用性有佐证的 verified link。pending / superseded / inactive / r8 错误 / unclassified role / 效力不明 version 均不得强行升级。

## 下一轮第一步

**继续 Phase 6 `core-laws-003`：在剩余 r10 verified/current lawVersion 中建立次级优先级排序（优先：被 r10 clause 引用但当前无 surviving link，其次按法规层级与用户常见 EHS 场景价值，再以 Stable ID 作为确定性 tie-break），选择一个可在单轮安全收口的批次，迁入 law + current lawVersion + review + public evidence。**

下一轮必须先重新核对 `chat-v4` 最终 HEAD 与 Drive 母库是否变化；如真实状态变化，以真实文件为准。

## 后续任务

1. Phase 6：继续 core law/current version 批次迁移。
2. Phase 6：verified clause。
3. Phase 6：verified hazard。
4. Phase 6：verified 且角色明确/适用性有佐证的 link。
5. Phase 7：法规与标准核验框架。
6. Phase 8：历史报告条款重新审阅。
7. Phase 9：V4 Validator。
8. Phase 10：V4 Gate。
9. Phase 11～16：网站构建、候选 release、V3/V4 对比、差异修复、最终验收。
10. Phase 17：仅在用户明确批准后生产切换。

## 法规/标准待核验队列

当前 Phase 6 不启动大规模新联网核验。待后续 Phase 7/8 按优先级处理：当前网站依赖、高频共享条款、高风险设备标准、江苏/南京常用规定、pending hazard 缺失的专项依据。

## 风险 / 阻塞

- r8 历史批量核验事故：长期禁令，禁止复用其批量通过逻辑。
- r10 中有 90 条 link 角色不足以自动证明 V4 direct/fallback/supporting（84 `primary`、5 `候选直接依据`、1 `主要负责人职责`）。
- 143 条 active link 在 Phase 5 原型中为 `ROLE_UNCLASSIFIED`；保持 pending。
- 11 个 lawVersion 效力/日期不足；保持 quarantine/pending。
- Drive V3 源码语义基线可能比 GitHub 旧 V3 分支更新，禁止 GitHub 旧 V3 回灌 Drive。
- 当前无阻塞 Phase 6 的重大用户决策事项。

## 用户待决策事项

无。生产切换仍需未来用户明确批准。

## 明确禁止事项

- 不直接修改 `main`。
- 不正式切换 GitHub Pages / 生产数据源。
- 不覆盖最新 V3 SQLite、fulltext、release 或 Drive 最新成果。
- 不用 r10 反向覆盖 SQLite；不恢复 r8。
- 不重新编号 Stable ID。
- 不把 upcoming/repealed/unknown version 当当前依据。
- 不因关键词相似、任务完成率或同一证据而批量通过 clause/link。
- 不把 `primary`、候选角色自动升级成 direct。
- 不公开 snapshot_ref、私有 Drive 路径、企业私有原件或 legacy payload。
- 在 Phase 6 未完成前不跳到 Validator/Gate/生产发布。
