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
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001～003 已完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

- 本轮起始 HEAD：`0482761f3fd0d73f1eb20e71265c35b03fa36e25`
- Phase 6 core-laws-003 data commit：`252a98bacdd0c193c0bbeb513b5340111467608b`
- 本 handoff 更新提交位于该 commit 之后；下一轮必须重新读取 `chat-v4` HEAD 获取最终 SHA。
- core-laws-002 data commit：`2180f07fd3abe54ac5d366b8d2f5eb600f314301`
- core-laws-001 data commit：`5cf400bae85a99e7d1edfb2c271c10f161e0495b`
- Phase 5 交接：`b2d0f4e0384f54a1c51342f4ae3a7683351e8c41`

### Google Drive

工作面：`ESH_Codex/work/safety-basis`

最新冻结母库仍为 `source/master/safety.sqlite3`：

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok（Phase 5 已确认）

关键数量：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4。

全文库：`source/library/fulltext.sqlite3`，size 21,864,448 bytes，SHA-256 `8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`。

最新候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`；hazards 242；laws 148；law_versions 150；clauses 52；links 269。r10 只作迁移佐证/对比，不是 V4 事实源。r8 为历史质量事故版本，不得恢复。

当前生产选择仍为 `reviewed-20260909-r4`；不得自行切换。

## 本轮完成

完成 Phase 6 `core-laws-003`：

1. 重新读取 handoff、核对 `chat-v4` HEAD，并确认 Drive 冻结 SQLite 大小/修改时间无漂移。
2. 检查 r10：52 个 clause 全部归属于 core-laws-001/002 已迁入的 10 部 law，因此“r10 clause 有引用但无 surviving link”的第一层候选已耗尽。
3. 按第二层规则选取全国性、现行、用户常见 EHS 高频场景法规，并以 Stable ID 保持确定性排序。
4. 逐项确认以下 6 部 law identity 与 current lawVersion 均有最新 `passed` review，且绑定公开政府/应急管理部 evidence：
   - `LF_L006`《工贸企业粉尘防爆安全规定》 / `L006`
   - `LF_L019`《工贸企业重大事故隐患判定标准》 / `L019`
   - `LF_L028`《生产安全事故应急预案管理办法》 / `L028`
   - `LF_META_0D5F9837A143A44F8CFFFC22`《工贸企业有限空间作业安全规定》 / `LV_META_48B66BAC1B312A800DF12324`
   - `LF_META_4F092633FE829F7B5912FC84`《安全生产事故隐患排查治理暂行规定》 / `LV_META_2259E8BA24A8A00716CBA72B`
   - `LF_META_0182C4B5B82C30063464A4B4`《危险化学品重大危险源监督管理暂行规定》 / `LV_META_5324ABD427408BD8393075AC`
5. 新增 6 law、6 current lawVersion、12 review sidecar、6 public evidence，并更新 `knowledge/manifest.json`。
6. 使用 Git tree 形成单一 data commit，并 fast-forward `chat-v4`，未 force。

## 本轮修改文件

新增：

- `knowledge/laws/`：上述 6 个 law 文件
- `knowledge/law-versions/`：上述 6 个 current version 文件
- `knowledge/reviews/laws/`：6 个 review sidecar
- `knowledge/reviews/law-versions/`：6 个 review sidecar
- `knowledge/evidence/`：6 个 public evidence 文件

修改：

- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- 6 个目标 law：identity_status=confirmed，最新 identity review=passed
- 6 个目标 lawVersion：现行有效、已核验、有 effectiveDate，最新 version review=passed
- lawVersion → law FK：0 断链
- Stable ID 与既有 knowledge：0 覆盖
- 新增 evidence：6 个唯一 ID，均为公开 URL；未公开 snapshot_ref
- `reviewedContentHash`：按 V4 canonical JSON 重新计算
- 私有字段/路径：未写入 snapshot_ref、legacy_payload、raw_payload、Drive 私有路径
- Git tree：`92acd92ae4eade7881fbf4cc9e0f37c2a73a4f26`
- data commit：`252a98bacdd0c193c0bbeb513b5340111467608b`
- compare：相对起始 HEAD ahead_by=1、behind_by=0；恰好 31 个预期文件变化（30 新增 + manifest）
- branch update：fast-forward，force=false
- manifest 回读：batch=`core-laws-003`，累计 laws=16、lawVersions=16、evidence=16、successions=2

## 当前项目状态

`knowledge/` 当前累计：

- laws：16
- current verified lawVersions：16
- public evidence：16
- successions：2
- clauses/hazards/links：尚未开始正式 Phase 6 迁入

Phase 5 保守 candidate 总量仍为 law 148、current lawVersion 148、clause 54、hazard 642、link 179。当前 laws/lawVersions 为 16/148；Phase 6 未完成。

## 未完成事项

### Phase 6 — 法规身份/版本

剩余约 132 个 verified law/current lawVersion 尚未进入正式 `knowledge/`。r10 正 link 使用频率集合和 r10 clause 集合都已被前三批覆盖，后续继续按法规层级、常见 EHS 场景价值、地域价值（江苏/南京优先）和 Stable ID 做稳定排序。

### Phase 6 — clause / hazard / link

法规基础批次达到可接受覆盖后，再依次迁入 verified clause → verified hazard → 角色明确且适用性有佐证的 verified link。pending / superseded / inactive / r8 错误 / unclassified role / 效力不明 version 均不得强行升级。

## 下一轮第一步

**继续 Phase 6 `core-laws-004`：先重新核对 `chat-v4` 最终 HEAD 与 Drive 母库；随后在剩余 verified/current lawVersion 中按“强制性法规/标准与部门规章优先 → 用户常见 EHS 场景（危化、消防、电气、特种设备、职业健康、江苏地方规则）→ Stable ID”选择一个可单轮收口的批次，迁入 law + current lawVersion + review + public evidence。**

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

当前 Phase 6 不启动大规模新联网核验。后续 Phase 7/8 优先处理当前网站依赖、高频共享条款、高风险设备标准、江苏/南京常用规定、pending hazard 缺失的专项依据。

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
