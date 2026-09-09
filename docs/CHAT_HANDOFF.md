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
- Phase 6：迁移现有有效知识 —— **进行中；core-laws-001～008 已完成，已满足 verified clause 父链覆盖条件，开始 clause 迁移**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

- 本轮起始 HEAD：`3fe47ab2fcd8a9e9e5c4de11342beed607383dcb`
- core-laws-006 最终线性应用 commit：`816c486a645c38963cd05a9198470447f13111c9`
- core-laws-007 data commit：`81a7ea6aee8febd2b566b561bfd0c01088a2a7d3`
- core-laws-008 data commit：`089258489829f2ec1cfa932f0f3b68fe101a15e4`
- core-laws-008 data tree：`e133d6c86e35a3de5ab2c4590a11715210e198cf`
- 本 handoff 更新提交位于 `089258489829f2ec1cfa932f0f3b68fe101a15e4` 之后；下一轮必须重新读取 `chat-v4` HEAD 获取最终 SHA。
- `3c50604454bf68afc6ffd7afb9eb71ec33346323` 是 core-laws-006 施工中生成但未挂到 `chat-v4` 的孤立 data commit；其内容已由 `816c486a645c38963cd05a9198470447f13111c9` 无 force、线性重新应用。不得把孤立 commit 当当前分支基线。
- core-laws-005 data commit：`3c64a3e4577687c0dc3dcfa810c8028961d57a83`
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

### core-laws-006

迁入 6 组高价值特种设备、职业卫生、电气防爆、粉尘防爆法规/标准。施工中出现一次提交顺序分叉：先生成孤立 data commit `3c506044...`，随后 handoff 更新占用分支 HEAD。已通过新线性 commit `816c486a...` 将完整 data tree 应用到当前分支，再 fast-forward；未 force、未丢数据、未改 main。

### core-laws-007

迁入 6 组：

- 《职业健康监护技术规范》GBZ 188—2025
- 《工业企业设计卫生标准》GBZ 1-2010
- 《安全色和安全标志》GB 2894-2025
- 《锻压机械 安全技术规范》GB 17120-2025
- 《有限空间作业安全技术规范》GB 46768-2025
- 《粉尘爆炸危险场所用除尘系统安全技术规范》AQ 4273-2016

新增 6 law、6 current lawVersion、12 review sidecar、6 public evidence。commit：`81a7ea6aee8febd2b566b561bfd0c01088a2a7d3`。

### core-laws-008

迁入 6 组：

- 《防止静电事故通用要求》GB 12158-2024
- 《金属切削机床 安全防护通用技术规范》GB 15760-2025
- 《焊接与切割安全》GB 9448-2025
- 《生产设备安全卫生设计总则》GB 5083-2023
- 《个体防护装备配备规范 第1部分：总则》GB 39800.1-2020
- 《气瓶安全技术规程》TSG 23—2021

新增 6 law、6 current lawVersion、12 review sidecar、6 public evidence。commit：`089258489829f2ec1cfa932f0f3b68fe101a15e4`。

### clause 父链覆盖核对

按 Phase 5 保守规则重新从冻结 V3 母库筛选：

- verified clause：54
- 唯一父 lawVersion：6
  - `L002`《中华人民共和国安全生产法》：31 条
  - `L023`《危险废物贮存污染控制标准》：13 条
  - `L001`《中华人民共和国消防法（2021修正）》：7 条
  - `L014`《中华人民共和国特种设备安全法》：1 条
  - `L020`《江苏省安全生产条例》：1 条
  - `LV_META_8982B9B15AF4365DE59CDFCE`《易制毒化学品管理条例》：1 条
- 上述 6 个父 lawVersion 均已存在于当前 `knowledge/law-versions/`，父链闭合。

因此不再以“先迁完 148 个 catalogue law”作为进入 clause 的前置条件；剩余 catalogue law 可在 Phase 6 后续按价值继续补充，但 verified clause 已可安全迁移。

## 本轮修改文件

新增：

- `knowledge/laws/`：core-laws-007/008 共 12 个 law 文件
- `knowledge/law-versions/`：共 12 个 current version 文件
- `knowledge/reviews/laws/`：共 12 个 review sidecar
- `knowledge/reviews/law-versions/`：共 12 个 review sidecar
- `knowledge/evidence/`：共 12 个 public evidence 文件

修改：

- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

未修改：`main`、V3 SQLite、fulltext SQLite、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- Drive 母库 size/modified 与冻结基线一致，无漂移
- SQLite SHA-256 复算：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- SQLite `integrity_check=ok`
- 本轮曾出现一次旧长只读连接 `database disk image is malformed`；重新以 immutable 只读连接打开后 SHA 未变、`integrity_check=ok`、laws=160、law_versions=161，确认属于连接级读取异常，不是文件损坏
- core-laws-007：相对前一 HEAD ahead_by=1、behind_by=0，恰好 31 个预期路径变化（30 新增 + manifest）
- core-laws-008：相对前一 HEAD ahead_by=1、behind_by=0，恰好 31 个预期路径变化（30 新增 + manifest）
- core-laws-007/008 所有目标 law：identity_status=confirmed、最新 identity review=passed
- 所有目标 lawVersion：现行有效、已核验、有 effectiveDate、最新 version review=passed
- 所有新增 evidence：authoritative-public；未迁入私有 `snapshot_ref`
- 所有 Stable ID 沿用 V3 原 ID，无重新编号
- verified clause 父链检查：54 条 clause 对应 6 个父 lawVersion，当前 knowledge 全部存在

## 当前项目状态

`knowledge/` 当前累计：

- laws：43
- current verified lawVersions：43
- public evidence：47
- successions：2
- verified clauses：准备开始正式迁入（V3 保守候选 54）
- hazards/links：尚未开始正式 Phase 6 迁入

Phase 5 保守 candidate 总量：law 148、current lawVersion 148、clause 54、hazard 642、link 179。

核心法规阶段已形成足以支撑全部 54 条 verified clause 的父链闭环。剩余约 105 组 verified law/current lawVersion 主要作为独立法规目录扩充，不再阻塞 clause/hazard/link 主链迁移。

## 未完成事项

### Phase 6 — verified clause

54 条保守 verified clause 待分批迁移。必须保留原 clause Stable ID、父 lawVersion、articlePath、quote、sourceUrl、最新 text review、evidence；不得因批量迁移重新判断或扩大 verified 集合。

### Phase 6 — verified hazard

Phase 5 保守候选 642 条。待 clause 迁移闭合后开始。

### Phase 6 — verified link

Phase 5 保守候选 179 条。必须保持 r8 禁令，只有角色明确且适用性有佐证的 link 才可进入 verified；`ROLE_UNCLASSIFIED` 保持 pending。

### Phase 6 — catalogue law/current version

仍有约 105 组 verified/current lawVersion 未迁入，可在主链迁移间隙按高价值场景补充；不阻塞 verified clause。

## 下一轮第一步

**继续 Phase 6 `clauses-001`：从冻结 V3 母库的 54 条保守 verified clause 中按 Stable ID 稳定排序，先迁入首批 12～15 条；每条同时迁入 clause JSON、text review sidecar 和所需 public evidence。仅使用 `status=已核验 + identity_status=confirmed_locator + 最新 text review=passed + authoritative public evidence + locator 非空` 的既有候选，不扩大集合。迁移后检查父 lawVersion 闭合、articlePath 唯一性、quote 非空、evidence 引用存在、reviewedContentHash 正确，再 fast-forward。**

## 后续任务

1. Phase 6：分批完成 54 条 verified clause。
2. Phase 6：分批迁移 642 条 verified hazard。
3. Phase 6：迁移 verified 且角色明确/适用性有佐证的 link。
4. Phase 6：按价值补充剩余 catalogue law/current version。
5. Phase 7：法规与标准核验框架。
6. Phase 8：历史报告条款重新审阅。
7. Phase 9：V4 Validator。
8. Phase 10：V4 Gate。
9. Phase 11～16：网站构建、候选 release、V3/V4 对比、差异修复、最终验收。
10. Phase 17：仅在用户明确批准后生产切换。

## 法规/标准待核验队列

- 2026 年新《中华人民共和国危险化学品安全法》生效后，对《危险化学品安全管理条例》等既有危化框架法规的继续适用/替代边界，留待 Phase 7 使用当前官方来源专项核验；在此之前不把这类存在替代敏感性的对象作为 Phase 6 自动迁移优先项。
- Phase 6 当前以已通过 V3 严格核验、证据为 authoritative-public 的资产迁移为主，不启动无差别全库新核验。

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
