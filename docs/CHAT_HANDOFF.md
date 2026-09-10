# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮先读取 `docs/PROJECT_PLAYBOOK.md`、本文件、`knowledge/manifest.json`，再读取 `chat-v4` 最新 HEAD。若文本与实际 Git 状态不一致，以实际 HEAD/文件为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 有价值资产、Stable ID、已确认法规/版本/条款、已核验隐患和可靠证据的基础上，建设更适合 Chat 长期维护的 V4 / Chat-first 安全隐患整改依据知识库与速查网站；准确性、时效性、适用性和私有数据隔离优先于迁移数量。

## 当前 Phase

- Phase 1～5：完成
- Phase 6：进行中
  - core laws：43
  - current verified lawVersions：43
  - conservative verified clauses：54 / 54
  - conservative verified hazards：642 / 642，迁移完成
  - conservative link candidates：179 / 179，迁移完成
  - link applicability 专业复核：**15 / 179 已完成，164 条待复核**

不得因工程迁移完成而跳过 link applicability、法规版本和条款适用性门禁。

## 当前工作分支

- GitHub：`An-0726/safety-basis`
- 正式施工分支：`chat-v4`
- 禁止直接修改 `main`

## 当前真实基线

### GitHub

本轮恢复时实际 HEAD：

`00c8d530cc651a2666e47396f8980e53853a5bfa`

本轮最新 link review data commit：

`e641a43a4517a086b6862393ed2eb872eb721f0e` — 完成第 11～15 条 Stable-ID 顺序 link applicability 专业复核。

本 handoff commit 位于其后；下一轮仍必须重新读取 `chat-v4` 的真实 HEAD。

近期关键提交：

- `6bbcc18` — 完成 hazards 231～642，至此 642/642 hazards 完成
- `12cd3e4` — hazards manifest 收口
- `899745c` — 迁移 179 条 link candidate
- `1750884` / 后续 manifest sync — links=179、evidence=548
- `513c8841e09ecccd2b8ce959e777d316a5541e93` — link candidate migration handoff
- `5b9df1d2da73a527955d13a533d145b549509aee` — 新增 V4.1 法规驱动知识生产设计
- `5f8584c0231cc2173e2e64a7cd56229d46aff0a3` — 首批 10 条 link applicability 专业复核
- `81cdb27864ccf94dd4cc3d55ff4b03913d162070` ～ `e641a43a4517a086b6862393ed2eb872eb721f0e` — 第 11～15 条 link applicability 专业复核

所有分支推进必须 non-force；写入前重新读取 HEAD，若并发前移则先同步并重算差集。

### Google Drive / V3 冻结基线

- 工作面：`ESH_Codex/work/safety-basis`
- V3 冻结库：`source/master/safety.sqlite3`
- SQLite SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 最新可靠 V3 候选 release：`reviewed-20260909-r10`
- 生产 selection：`reviewed-20260909-r4`，不得自行切换

本轮没有修改 Drive、V3 SQLite、fulltext、正式 release 或生产网站。

## 当前 manifest

`knowledge/manifest.json` 当前实体计数：

- laws：43
- lawVersions：43
- clauses：54
- hazards：642
- links：179
- evidence：548
- successions：2

manifest 的 `links=179` 只表示 link 实体已经迁入，不代表 179 条都经过专业 applicability verified。专业 review 状态由 `knowledge/reviews/links/` 决定。

## 本轮完成

### 恢复并发后的真实状态

恢复时发现 `chat-v4` 已比旧 handoff 记录的 `5f8584c...` 前移至 `00c8d530...`。经实际文件核对确认：642/642 hazards 与 179/179 link candidates 已迁完，真正断点为 link applicability 专业复核；未重复执行 hazard/link 迁移。

### Link applicability 第 11～15 条

按 Stable-ID 排序继续逐条读取 `Link → Hazard → Clause → Review/Evidence`，完成 5 条专业判断：

11. `K_053502698cf8f03c4ab637f4` — **rejected**：Hazard 明确依赖 GB 50054-2011 第7.6.38的电缆穿管专项技术要求；《消防法》第二十七条第二款只是要求线路敷设符合消防技术标准，不能以当前 `role=direct` 直接证明具体穿管方式。可在改为 supporting/fallback 后另行复核。
12. `K_0561db716bd11d87c7b0b129` — **rejected**：Hazard 是《生产安全事故应急条例》第四条意义上的应急工作责任制专项义务；《安全生产法》第五条只是主要负责人对安全生产全面负责的一般责任，当前 `role=direct` 过强。
13. `K_05B2CCBBD57A37BE1D8393A0FE` — **verified**：《安全生产法》第五十一条直接规定依法参加工伤保险并为从业人员缴费，与 Hazard 的对象、义务和条件一致。
14. `K_05C601114F154B9A94578C68C2` — **verified**：《安全生产法》第四十一条直接要求重大事故隐患排查治理情况及时向监管部门和职代会/职工大会报告，与条件型 Hazard 直接对应。
15. `K_07d6f00250bbdd273a194b68` — **verified**：《安全生产法》第二十八条对安全生产教育培训、必要知识技能和未经培训合格不得上岗的要求与 Hazard 直接一致。

本批结果：**3 verified / 2 rejected / 0 pending**。

累计前 15 条：首批为 3 verified / 4 rejected / 3 pending；本批新增 3 verified / 2 rejected，因此累计为：

- verified：6
- rejected：6
- pending：3
- reviewed：15 / 179
- remaining：164

## 本轮修改文件

- `knowledge/reviews/links/K_053502698cf8f03c4ab637f4.json`
- `knowledge/reviews/links/K_0561db716bd11d87c7b0b129.json`
- `knowledge/reviews/links/K_05B2CCBBD57A37BE1D8393A0FE.json`
- `knowledge/reviews/links/K_05C601114F154B9A94578C68C2.json`
- `knowledge/reviews/links/K_07d6f00250bbdd273a194b68.json`
- `docs/CHAT_HANDOFF.md`

## 本轮校验

- 5 条 link 均逐条读取并与对应 Hazard、Clause 对照；未继承 V3 `passed` 作为自动结论。
- 复用既有 review sidecar 中的 `reviewedContentHash`、`contextHashes`、`evidenceRefs` 和 `migratedFromV3Verification`，未伪造旧审查元数据。
- 复核确认 canonical content hash 算法为排序键、紧凑 JSON 的 SHA-256；抽查现有已审 link 的 `reviewedContentHash` 与算法一致。
- 两条 rejected 均属于“法规本身有效，但当前 direct link 支撑强度不足”，未删除法规/条款实体。
- 本轮只修改上述 5 个 link review sidecar 和 handoff；未修改 link 实体、hazard、clause、manifest 实体计数。
- `main`、生产 selection、V3 SQLite/fulltext、Pages/线上网站均未修改。

## 当前项目状态

V4 核心实体迁移已经完成；Phase 6 当前主要剩余工作不是搬运实体，而是对 179 个 link 的真实适用性逐条专业复核。首 15 条已再次证明历史 V3 `passed` 不能等价为 V4 professional verified。

已暴露的主要质量类型：

- `DIRECT_ROLE_OVERSTATED` / 当前 direct 角色支撑强度不足
- `SPECIFIC_CLAUSE_REQUIRED`
- `COMPOSITE_HAZARD`
- `PARTIAL_CLAUSE_COVERAGE`
- `FACT_NOT_HAZARD`
- `SCOPE_MISMATCH`
- `TECHNICAL_OBJECT_MISMATCH`

## V4.1 设计补强

规范性补充：`docs/V4_1_REGULATION_DRIVEN_KNOWLEDGE.md`。

核心规则继续有效：

1. 双向知识生产：Hazard-driven 与 Regulation-driven。
2. 不采用“一条 Clause = 一条 Hazard”，引入 Requirement 中间层。
3. 完整法规导入后逐条结构化、提炼 Requirement、查重/复用 Hazard，再生成必要 candidate。
4. 新版本应形成 Clause/Requirement/Hazard/Link 影响清单，不机械替换标准号。
5. 网站搜索不得退化，aliases、keywords、category、places、法规名称、条款和 Requirement 检查词参与召回。
6. 搜索可以宽召回，但 verified 仍严门禁，语义相似不能自动证明适用性。

后续在合适节点整合进 `PROJECT_PLAYBOOK.md`、`ARCHITECTURE_V4_CHAT_FIRST.md`、`GATE_V4.md`，不得阻塞当前 link 复核。

## 未完成事项

1. 剩余 164 条 link applicability 专业复核。
2. 对 rejected/pending 中暴露出的 role 过强、组合型 Hazard、专项条款缺失等问题形成后续修复队列；当前不要为追求通过率直接改写历史实体。
3. 补 catalogue law/current version。
4. 完成 Phase 6 后再按顺序进入 Phase 7。

## 下一轮第一步

从尚未复核的下一条 Stable-ID 顺序 candidate：

`K_0ae618827e98fe36f8b04c7951`

开始下一批 link applicability 专业复核。继续逐条读取：

`Link → Hazard → Clause → LawVersion/Law（需要时）→ Review/Evidence`

明确判断 role、对象、条件、适用范围、技术要求和版本是否真实覆盖当前 Hazard；建议每 10～20 条形成一个独立 review 工作单元，但宁可少审也不得批量猜测。

## 后续任务

1. 完成 179 link applicability 专业复核及必要修复。
2. 补 catalogue law/current version。
3. Phase 7：法规与标准核验框架，纳入完整法规结构化、Requirement 提取、版本影响分析。
4. Phase 8：历史报告条款与组合型 Hazard 重审。
5. Phase 9：Validator，增加 Requirement/schema/hash/context 及搜索索引检查。
6. Phase 10：Gate，增加 Requirement 和搜索非退化验收规则。
7. Phase 11～16：候选 release、网站构建、搜索回归、V3/V4 对比、差异修复与验收。
8. Phase 17：仅用户明确批准后切换生产。

## 法规/标准待核验队列

本轮新增/确认的后续专项核验线索：

- `H_C7284453E8E94532A44FC5F5EF`：应优先核验其声称的《低压配电设计规范》GB 50054-2011 第7.6.38是否准确、现行且具体要求确实对应“穿管保护”；C005不作为该专项技术事实的 direct 证明。
- `H_407B9F4BFC5A4879B9950C9D87`：优先保留/核验《生产安全事故应急条例》第四条作为专项依据；《安全生产法》第五条仅考虑 supporting/fallback 角色。

## 风险 / 阻塞

- 无需要用户决策的阻塞。
- 并发施工仍可能使 HEAD 前移；下一轮必须 HEAD-first，不得覆盖并发成果。
- 部分历史 Hazard 是组合义务或事实表述不规范；link review 应先标 pending/rejected，再在 Phase 8 或专门修复单元处理实体结构，避免边审边大规模改写。

## 用户待决策事项

无。

## 明确禁止事项

- 不修改 `main`
- 不切换生产网站/Pages 数据源
- 不覆盖 V3 SQLite/fulltext/正式 release
- 不 force push / force update ref
- 不恢复 r8 错误关联
- 不因关键词相似自动核验 Link
- 不把 hazard content verified 等同于 link applicability verified
- 不把 V3 passed 无条件继承为 V4 verified
- 不伪造法规、标准、版本、条款、原文、证据或 review 元数据
- 不公开私有路径、受限全文、snapshot_ref / legacy payload
