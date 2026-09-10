# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮必须先读取本文件，再核对 GitHub 与 Google Drive 真实状态；冲突时以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 新窗口续接协议

每次新开窗口或重新接手本项目，必须按以下顺序判断真实断点，**不能只相信本文件里写的进度数字**：

1. 先读取 `docs/PROJECT_PLAYBOOK.md` 和 `docs/CHAT_HANDOFF.md`。
2. 读取 `chat-v4` 当前最新 HEAD。
3. 查询最近一次修改 `docs/CHAT_HANDOFF.md` 的 commit，并与当前 HEAD 比较提交时间和祖先关系。
4. 如果 HEAD 晚于 handoff commit，必须检查 handoff commit 之后的全部相关 commit，重点核对 `knowledge/manifest.json`、实际实体文件、review sidecar 和其他真实落盘成果。
5. **实际 GitHub 文件状态和最新有效 commit 优先于 handoff 文本。** 如果实际进度更靠后，先以实际状态继续工作，并在本轮结束前修正本文件。
6. 每个有效施工单元应先提交 data/code 成果并完成校验，再单独更新本 handoff；handoff 必须写明本轮最新 data commit、当前累计数量、未完成事项、风险和下一步。
7. 写入前再次读取 HEAD。若并发前移，重新基于最新 HEAD 判断差集；只允许非 force 的安全前移，禁止用旧 handoff 或旧本地状态覆盖新成果。

因此，“handoff 文件看起来更新”本身不代表它一定是最新事实；必须先完成 **HEAD → handoff 最后 commit → 中间 commits → manifest/实际文件** 的比较链。

## 当前总目标

在保留 Codex V3 的 Stable ID、法规身份/版本、条款、隐患、link、evidence、release、网站与审计历史基础上，迁移到 Git-first、Chat 可长期维护的 V4 / Chat-first 架构。优先保证法规版本、条款原文、隐患内容、适用性和隐私正确；降低 SQLite、dependency hash、本地 Code Agent 对日常维护的强依赖。

## 当前 Phase

- Phase 1：V3 基线冻结 —— 完成
- Phase 2：V4 Chat-first 架构 —— 完成
- Phase 3：V4 门禁设计 —— 完成
- Phase 4：V3 → V4 数据映射 —— 完成
- Phase 5：只读迁移原型 —— 完成并验收
- Phase 6：迁移现有有效知识 —— **进行中：core-laws-001～008 完成；54/54 conservative verified clause 完成；30/642 conservative verified hazard 完成**

不得提前进入 Phase 7～10。

## 当前工作分支

`chat-v4`。禁止直接修改 `main`。

## 当前真实基线

### GitHub

本轮确认的最新 data commit：`e12cfc39d8efccd4b9d52660cb2ebe199c492d55`（`data: migrate Phase 6 hazards batch 005`）。本 handoff 更新 commit 位于其后；下一轮必须重新读取 `chat-v4` 获取真实最终 HEAD。

本轮关键提交：

- `dc53f388577ac112c97b2d6ec5a19f84226a486f` — clauses-004，完成全部 54 条 conservative clause
- `491c407672d64d149d5f90ed6d8c5d4dd29c7db6` — docs: add Safety Basis project playbook
- `d72551be5e1555cc9251f5067f69b30425a59a21` — hazards-001
- `b1f7de0792f2fb54e46969a9770a96ce82282dd4` — hazards-002
- `0e7a2ea582c795e909b8544e7e7dbc6980c2c0ce` — hazards-003
- `013c2b7fbae5ac9ae196e1113cdd5cb0e71f51e7` — hazards-004
- `e12cfc39d8efccd4b9d52660cb2ebe199c492d55` — hazards-005

所有正式分支推进均只允许 fast-forward；施工中生成但未挂到 `chat-v4` 的孤立候选 commit 不得视为真实基线。

### Google Drive

工作面：`ESH_Codex/work/safety-basis`

冻结母库 `source/master/safety.sqlite3`：

- size：110,002,176 bytes
- modified：2026-09-09T15:19:03.068Z
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- schemaVersion：3
- integrity_check：ok
- counts：laws 160；law_versions 161；clauses 2603；hazards 1125；links 2298；evidence 1124；verification 16159；law_successions 4

全文库 `source/library/fulltext.sqlite3`：21,864,448 bytes；SHA-256 `8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`。

最新候选 release：`reviewed-20260909-r10`，releaseHash `dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`；hazards 242、laws 148、law_versions 150、clauses 52、links 269。r10 只作迁移佐证/差异对比，不是 V4 事实源。生产选择仍为 `reviewed-20260909-r4`，不得自行切换。

本轮重新确认 Drive `safety-basis` 工作目录存在，源码、data、docs、source、tests、tools 等工作树仍在；未发现需要覆盖冻结母库或生产选择的事项。

## 本轮完成

### Conservative verified clause 主链闭合

从冻结母库按 Phase 5 保守规则重新筛出 54 条：`status=已核验 + identity_status=confirmed_locator + 最新 text review=passed + authoritative-public evidence + locator 非空`。分 `clauses-001～004` 完成 15+15+15+9 条迁移，共 54/54；父 lawVersion 断链 0，Stable ID 未重编。

### Conservative verified hazard 主链继续推进

固定 conservative hazard 候选总量仍为 642，筛选规则：

- `hazards.status=已核验`
- active、`merged_into` 为空
- 最新 `entity_type=hazard/check_type=content` review = `passed`
- `verification_details.public_fields_reviewed=1`

已完成：

- hazards-001：H002、H005、H013、H015、H016、H017
- hazards-002：H018、H019、H021、H022、H024、H025
- hazards-003：H033、H034、H035、H036、H037、H038
- hazards-004：H039、H040、H041、H042、H043、H044
- hazards-005：H045、H046、H047、H048、H049、H050

累计 30/642。`hazards-005` 的真实提交只新增 6 个 hazard JSON、6 个 hazard review sidecar，并更新 `knowledge/manifest.json`；相对父提交 `62e08f6482348188ec2d133b837a10b48da0ff09` 为 ahead 1 / behind 0，无无关路径夹带。

hazard content verified 仍不得等同于 link applicability verified；记录中已有“依据未终审/核验完成前不得进入公开运行库”等限制的，必须继续由后续 link/gate 阻断。

## 本轮修改文件

- `knowledge/hazards/H045.json`～`H050.json`
- `knowledge/reviews/hazards/H045.json`～`H050.json`
- `knowledge/manifest.json`
- `docs/CHAT_HANDOFF.md`

未修改：`main`、V3 SQLite、fulltext、任何 V3 release、`site-selection.json`、生产网站。

## 本轮校验

- `chat-v4` 写前 HEAD 复核为 `e12cfc39d8efccd4b9d52660cb2ebe199c492d55`
- `hazards-005` compare：ahead_by=1、behind_by=0
- 变更路径恰为 6 hazard + 6 review + manifest，共 13 个预期路径
- `knowledge/manifest.json` 当前 batch=`hazards-005`
- manifest counts：laws 43；lawVersions 43；clauses 54；hazards 30；evidence 54；successions 2
- manifest scope 明确为 first 30 of 642 conservative verified hazards；links 继续 deferred
- 冻结 SQLite SHA-256 基线未改
- 未修改 `main`、生产网站或生产 release 选择

## 当前项目状态

`knowledge/` 当前累计：

- laws：43
- current verified lawVersions：43
- verified clauses：54 / 54 conservative set
- verified hazards：30 / 642 conservative set
- evidence：54
- successions：2
- verified links：0 / 179 conservative candidate，尚未开始正式迁入

Phase 5 保守 candidate 总量：law 148、current lawVersion 148、clause 54、hazard 642、link 179。

## 未完成事项

1. Phase 6：剩余 612 条 conservative verified hazard 分批迁移。
2. Phase 6：179 条 conservative verified link；必须逐条保持角色/适用性 review，`ROLE_UNCLASSIFIED` 不得自动通过。
3. Phase 6：按价值补充剩余约 105 组 catalogue law/current version，不阻塞 hazard/link 主链。
4. 完成 Phase 6 校验后才进入 Phase 7。

## 下一轮第一步

**执行 `hazards-006`：先按照“新窗口续接协议”比较当前 HEAD、`CHAT_HANDOFF.md` 最后修改 commit、其后的中间 commits 与 `knowledge/manifest.json`/实际文件状态；确认真实断点后，再从冻结 SQLite immutable 只读连接按既定 642 条规则重算候选，排除 `knowledge/hazards/` 已有 Stable ID，从剩余集合按 Stable ID 顺序取下一批。生成 hazard JSON + content review sidecar，仅补缺失 evidence；迁移前检查 active、非 merge、title/description/measures 非空、latest review=passed、public_fields_reviewed=1；迁移后检查重复 ID、review/evidence 引用、私有字段泄漏和 manifest 计数。写 Git 前再次读取 `chat-v4` HEAD，只允许非 force 的安全前移。**

## 后续任务

1. 持续完成 verified hazard 主链。
2. 迁移 conservative verified link。
3. 补充 catalogue law/current version。
4. Phase 7 法规与标准核验框架。
5. Phase 8 历史报告条款重审。
6. Phase 9 Validator；Phase 10 Gate。
7. Phase 11～16 网站构建、候选 release、V3/V4 对比、差异修复、最终验收。
8. Phase 17 仅在用户明确批准后生产切换。

## 法规/标准待核验队列

- 2026 年新《中华人民共和国危险化学品安全法》生效后与既有危化框架法规的继续适用/替代边界：Phase 7 用当前官方来源专项核验。
- 6 条 hazard 的现有迁移 evidence tier 为 secondary：进入发布链前按 V4 evidence/gate 规则评估是否补强。
- hazard note 中明确“依据未终审”的对象：只迁 content，不视为依据/link 已核验。

## 风险 / 阻塞

- r8 历史质量事故禁令持续有效，禁止批量假定 link/条款适用性正确。
- 已再次观察到并发分支前移；继续采用每次写前重读 HEAD、绝不 force。
- `tools/v4/migrate_v3.py` 仍存在读取不存在的 V3 verification `method` 字段的代码风险；正式手工迁移不写该字段。应在合适的独立代码单元修复，不得伪造字段。
- 当前无需要用户决策的阻塞。

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
