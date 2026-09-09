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
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001～005 已完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

- 本轮起始 HEAD：`4bdbf1a3aacdbb85341cc0b4fcba1b3390c8a822`
- Phase 6 core-laws-005 data commit：`3c64a3e4577687c0dc3dcfa810c8028961d57a83`
- data tree：`c52a436dc7d1ac19cd45afa1ea1ad000fcbcb1ae`
- 本 handoff 更新提交位于该 data commit 之后；下一轮必须重新读取 `chat-v4` HEAD 获取最终 SHA。
- core-laws-004 data commit：`c42bd8dd062514a5432df2439ed3686d23e04547`
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

完成 Phase 6 `core-laws-005`：

1. 重新读取 handoff，并核对 `chat-v4` 实际 HEAD、Drive 工作目录和冻结 SQLite，确认无版本漂移。
2. 从冻结 V3 母库中按“confirmed law + 已核验 current lawVersion + 最新 passed review + 公开 evidence”筛选本批对象。
3. 本批迁入 6 组当前高价值 EHS 法规/安全技术规范：
   - `LF_NPC_ff808181864a5d91018653f61bbd4f61`《江苏省消防条例》 / `LV_NPC_ff808181864a5d91018653f61bbd4f61`
   - `LF_NPC_ff80818188c8b06b018929165ced45c4`《南京市安全生产条例》 / `LV_NPC_ff80818188c8b06b018929165ced45c4`
   - `LF_NPC_ff808181905e69170190729eeef53bcc`《江苏省生产经营单位安全风险管理条例》 / `LV_NPC_ff808181905e69170190729eeef53bcc`
   - `LF_NPC_ff80818194a5cf29019541042f6d1cdc`《南京市消防条例》 / `LV_NPC_ff80818194a5cf29019541042f6d1cdc`
   - `LF_STD_6E8536FD29C1696E35CF4A1D`《承压类特种设备安全附件安全技术规程》 / `LV_STD_AC9450848A37DC769475CCCC`（TSG 92—2026，2026-07-01 实施）
   - `LF_STD_7850A7B209AB5AD548EBECB2`《特种设备使用管理规则》 / `LV_STD_E10C40D4BD9D8DB74D518B2A`（TSG 08—2026，2026-05-01 实施）
4. 新增 6 law、6 current lawVersion、12 review sidecar、9 public evidence，并更新 `knowledge/manifest.json`。
5. 危化领域 2026 新法可能影响的旧框架性法规继续留待 Phase 7 时效专项核验，本批未直接迁入。
6. 使用单一 Git tree 形成 data commit，并 fast-forward `chat-v4`，未 force。

## 本轮修改文件

新增：

- `knowledge/laws/`：6 个 law 文件
- `knowledge/law-versions/`：6 个 current version 文件
- `knowledge/reviews/laws/`：6 个 review sidecar
- `knowledge/reviews/law-versions/`：6 个 review sidecar
- `knowledge/evidence/`：9 个 public evidence 文件

修改：

- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- Drive 母库 size/modified 与冻结基线一致，无漂移
- 下载后重新计算 SQLite SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`，与冻结基线完全一致
- SQLite `integrity_check=ok`
- 6 个目标 law：identity_status=confirmed，最新 identity review=passed
- 6 个目标 lawVersion：现行有效、已核验、有 effectiveDate，最新 version review=passed
- 两个 2026 TSG 的 effectiveDate 均早于当前日期 2026-09-10，不属于 upcoming
- lawVersion → law：本批全部闭合，不新增断链
- Stable ID：全部沿用 V3 原 ID；没有重新编号
- 新增 evidence：9 个唯一 ID，均为国家法律法规数据库、南京人大、国家市场监督管理总局等公开官方 URL
- V3 私有 `snapshot_ref` 未迁入；public evidence 只保留公开 URL、retrievedAt、locator/page 与 snapshot SHA
- `reviewedContentHash`：按 V4 canonical JSON 计算并写入 sidecar
- 私有字段/路径生成检查：未写入 `snapshot_ref`、`legacy_payload`、`raw_payload`、Drive 私有路径或 `../archive`
- data tree：`c52a436dc7d1ac19cd45afa1ea1ad000fcbcb1ae`
- data commit：`3c64a3e4577687c0dc3dcfa810c8028961d57a83`
- compare：相对起始 HEAD ahead_by=1、behind_by=0；恰好 34 个预期文件变化（33 新增 + manifest），无无关文件
- branch update：fast-forward，force=false
- manifest 回读：batch=`core-laws-005`，累计 laws=25、lawVersions=25、evidence=29、successions=2

## 当前项目状态

`knowledge/` 当前累计：

- laws：25
- current verified lawVersions：25
- public evidence：29
- successions：2
- clauses/hazards/links：尚未开始正式 Phase 6 迁入

Phase 5 保守 candidate 总量仍为 law 148、current lawVersion 148、clause 54、hazard 642、link 179。当前 laws/lawVersions 为 25/148；约剩余 123 组 law/current lawVersion，Phase 6 未完成。

## 未完成事项

### Phase 6 — 法规身份/版本

剩余约 123 个 verified law/current lawVersion 尚未进入正式 `knowledge/`。继续按高价值 EHS 场景、法规/标准效力、江苏/南京地域价值和 Stable ID 做稳定排序；不为追求数量迁入存在时效疑义的对象。

### Phase 6 — clause / hazard / link

法规基础批次达到可接受覆盖后，再依次迁入 verified clause → verified hazard → 角色明确且适用性有佐证的 verified link。pending / superseded / inactive / r8 错误 / unclassified role / 效力不明 version 均不得强行升级。

## 下一轮第一步

**继续 Phase 6 `core-laws-006`：重新核对 `chat-v4` HEAD 与 Drive 母库后，在剩余 confirmed + verified/current 对象中优先选择特种设备、职业卫生、电气、防火及通用 EHS 高价值法规/标准，例如特种设备使用单位主体责任、特种设备重大事故隐患判定、工作场所职业卫生管理/职业接触限值、防爆电气等；仍避开需要 Phase 7 重新判定替代边界的危化框架法规。形成一个可单轮收口的 law + current lawVersion + review + public evidence 批次。**

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

- 2026 年新《中华人民共和国危险化学品安全法》生效后，对《危险化学品安全管理条例》等既有危化框架法规的继续适用/替代边界，留待 Phase 7 使用当前官方来源专项核验；在此之前不把这类存在替代敏感性的对象作为 Phase 6 自动迁移优先项。
- 本轮未启动大规模新联网法规核验；Phase 6 继续以 V3 已通过核验且当前效力明确的资产迁移为主。

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
