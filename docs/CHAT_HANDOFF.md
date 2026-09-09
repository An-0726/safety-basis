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
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001～004 已完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

- 本轮起始 HEAD：`fa6d1438076ebe85eda9d9e2b3c632cd3c9d430e`
- Phase 6 core-laws-004 data commit：`c42bd8dd062514a5432df2439ed3686d23e04547`
- 本 handoff 更新提交位于该 commit 之后；下一轮必须重新读取 `chat-v4` HEAD 获取最终 SHA。
- core-laws-003 data commit：`252a98bacdd0c193c0bbeb513b5340111467608b`
- core-laws-002 data commit：`2180f07fd3abe54ac5d366b8d2f5eb600f314301`
- core-laws-001 data commit：`5cf400bae85a99e7d1edfb2c271c10f161e0495b`

### Google Drive

工作面：`ESH_Codex/work/safety-basis`

最新冻结母库仍为 `source/master/safety.sqlite3`：

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok

关键数量：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4。

全文库：`source/library/fulltext.sqlite3`，size 21,864,448 bytes，SHA-256 `8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`。

最新候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`；hazards 242；laws 148；law_versions 150；clauses 52；links 269。r10 只作迁移佐证/对比，不是 V4 事实源。r8 为历史质量事故版本，不得恢复。

当前生产选择仍为 `reviewed-20260909-r4`；不得自行切换。

## 本轮完成

完成 Phase 6 `core-laws-004`：

1. 重新读取 handoff，核对 `chat-v4` HEAD 与 Drive 冻结 SQLite，确认无版本漂移。
2. 从剩余 verified/current lawVersion 中选取 3 个高价值 EHS 对象，并避开可能受 2026 年新法替代关系影响、需要重新判定的危化框架性法规。
3. 本批迁入：
   - `LF_L012`《危险化学品仓库储存通则》 / `L012`（GB 15603-2022）
   - `LF_STD_6294CCA2BE20A4078E76A41B`《国家电气设备安全技术规范》 / `LV_STD_9F0C49F748552F616764E7E8`（GB 19517-2023）
   - `LF_NPC_ff8080816f135f46016f212ea20a17f8`《中华人民共和国职业病防治法》 / `LV_NPC_ff8080816f135f46016f212ea20a17f8`
4. 新增 3 law、3 current lawVersion、6 review sidecar、4 public evidence，并更新 `knowledge/manifest.json`。
5. 职业病防治法的 law identity 与 lawVersion 使用不同的最新官方 evidence，均保留其真实 evidence ID，不强行合并。
6. 使用单一 Git tree 形成 data commit，并 fast-forward `chat-v4`，未 force。

## 本轮修改文件

新增：

- `knowledge/laws/`：3 个 law 文件
- `knowledge/law-versions/`：3 个 current version 文件
- `knowledge/reviews/laws/`：3 个 review sidecar
- `knowledge/reviews/law-versions/`：3 个 review sidecar
- `knowledge/evidence/`：4 个 public evidence 文件

修改：

- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- Drive 母库 size/modified 与冻结基线一致，无漂移
- SQLite `integrity_check=ok`
- 3 个目标 law：identity_status=confirmed，最新 identity review=passed
- 3 个目标 lawVersion：现行有效、已核验、有 effectiveDate，最新 version review=passed
- lawVersion → law FK：0 断链
- Stable ID：均沿用 V3 原 ID；没有重新编号
- 新增 evidence：4 个唯一 ID，全部为官方公开 URL
- `reviewedContentHash`：按 V4 canonical JSON 重新计算
- 私有字段/路径扫描：0 命中；未写入 `snapshot_ref`、`legacy_payload`、`raw_payload`、Drive 私有路径或 `../archive`
- data Git tree：`a167f65be42f62fc2c5d166f7383de7f942c5492`
- data commit：`c42bd8dd062514a5432df2439ed3686d23e04547`
- compare：相对起始 HEAD ahead_by=1、behind_by=0；恰好 17 个预期文件变化（16 新增 + manifest）
- branch update：fast-forward，force=false
- manifest 回读：batch=`core-laws-004`，累计 laws=19、lawVersions=19、evidence=20、successions=2

## 当前项目状态

`knowledge/` 当前累计：

- laws：19
- current verified lawVersions：19
- public evidence：20
- successions：2
- clauses/hazards/links：尚未开始正式 Phase 6 迁入

Phase 5 保守 candidate 总量仍为 law 148、current lawVersion 148、clause 54、hazard 642、link 179。当前 laws/lawVersions 为 19/148；Phase 6 未完成。

## 未完成事项

### Phase 6 — 法规身份/版本

剩余约 129 个 verified law/current lawVersion 尚未进入正式 `knowledge/`。后续继续按强制性法规/标准、常见 EHS 场景价值、江苏/南京地域价值和 Stable ID 做稳定排序。

### Phase 6 — clause / hazard / link

法规基础批次达到可接受覆盖后，再依次迁入 verified clause → verified hazard → 角色明确且适用性有佐证的 verified link。pending / superseded / inactive / r8 错误 / unclassified role / 效力不明 version 均不得强行升级。

## 下一轮第一步

**继续 Phase 6 `core-laws-005`：重新核对 `chat-v4` HEAD 与 Drive 母库后，在剩余 verified/current lawVersion 中优先选择消防、特种设备、职业卫生、江苏/南京地方规则中的高价值对象，形成一个可单轮收口的 law + current lawVersion + review + public evidence 批次；对 2026 年新法可能影响效力关系的危化框架法规先保留待 Phase 7 时效复核，不直接迁入。**

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

- 2026 年新《中华人民共和国危险化学品安全法》已生效后，对《危险化学品安全管理条例》等既有危化框架法规的继续适用/替代边界，留待 Phase 7 使用当前官方来源专项核验；在此之前不把这类存在替代敏感性的对象作为 Phase 6 自动迁移优先项。
- 其余当前 Phase 6 不启动大规模新联网核验。

## 风险 / 阻塞

- r8 历史批量核验事故：长期禁令，禁止复用其批量通过逻辑。
- r10 中有 90 条 link 角色不足以自动证明 V4 direct/fallback/supporting（84 `primary`、5 `候选直接依据`、1 `主要负责人职责`）。
- 143 条 active link 在 Phase 5 原型中为 `ROLE_UNCLASSIFIED`；保持 pending。
- 11 个 lawVersion 效力/日期不足；保持 quarantine/pending。
- 2026 年危化领域存在新法生效后的框架衔接风险；相关旧法规不在 Phase 6 无复核前自动优先迁入。
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
