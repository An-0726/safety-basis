# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮先读取 `docs/PROJECT_PLAYBOOK.md`、本文件、`knowledge/manifest.json`，再读取 `chat-v4` 最新 HEAD。若文本与实际 Git 状态不一致，以实际 HEAD/文件为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前工作面

- GitHub 正式施工分支：`chat-v4`
- 禁止直接修改 `main`
- 本地同步盘：`ESH_Codex/work/safety-basis`，用于读取 V3 SQLite/私有原始资料；Google Drive 已同步到本地，施工 Agent 不需要访问 Drive 网站/API。
- V3 冻结库：`source/master/safety.sqlite3`
- SQLite SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 最新可靠 V3 候选 release：`reviewed-20260909-r10`
- 生产 selection 仍为 `reviewed-20260909-r4`，不得自行切换。

## 当前 Phase

- Phase 1～5：完成
- Phase 6：进行中
  - core laws：43
  - current verified lawVersions：43
  - conservative verified clauses：54 / 54
  - conservative verified hazards：642 / 642，迁移完成
  - conservative link candidates：179 / 179，迁移完成
  - link applicability 专业复核：**10 / 179 已完成，169 条待复核**

不得因工程迁移完成而跳过 link applicability、法规版本和条款适用性门禁。

## 当前 GitHub 基线

本文件更新前 HEAD：

`5f8584c0231cc2173e2e64a7cd56229d46aff0a3` — `review: adjudicate first 10 Phase 6 link candidates`

近期关键提交：

- `6bbcc18` — 完成 hazards 231～642，至此 642/642 hazards 完成
- `12cd3e4` — hazards manifest 收口
- `f26154b` — hazards-008 handoff
- `899745c` — 迁移 179 条 link candidate
- `1750884` / 后续 manifest sync — links=179、evidence=548
- `513c8841e09ecccd2b8ce959e777d316a5541e93` — link candidate migration handoff
- `5b9df1d2da73a527955d13a533d145b549509aee` — 新增 V4.1 法规驱动知识生产设计
- `5f8584c0231cc2173e2e64a7cd56229d46aff0a3` — 首批 10 条 link applicability 专业复核

所有分支推进必须 non-force；写入前重新读取 HEAD，若并发前移则先同步并重算差集。

## 当前 manifest

`knowledge/manifest.json` 当前实体计数：

- laws：43
- lawVersions：43
- clauses：54
- hazards：642
- links：179
- evidence：548
- successions：2

manifest 的 `links=179` 表示 179 个 link 实体已迁入，不表示 179 条都已经专业 verified。专业 review 状态由 `knowledge/reviews/links/` 决定。

## V4.1 设计补强

新增规范性设计补充：

`docs/V4_1_REGULATION_DRIVEN_KNOWLEDGE.md`

该文件已正式进入 `chat-v4`，在后续合并回总设计前，对以下事项具有规范效力：

1. Safety Basis 采用双向知识生产：
   - Hazard-driven：现场隐患 → 法规依据
   - Regulation-driven：完整法规/标准 → Clause → 原子 Requirement → Hazard candidate → Link
2. 不采用“一条 Clause = 一条 Hazard”；新增 Requirement 中间层，法规原文、AI 提炼、现场隐患三层分离。
3. 完整法规导入后应逐条结构化、提炼可检查 Requirement、与已有 Hazard 查重/复用，再生成必要的新 Hazard candidate。
4. 新法规版本导入要产生 Clause/Requirement/Hazard/Link 影响清单，不允许只机械替换标准号。
5. V4 网站搜索能力不得退化：标题之外的 aliases、keywords、category、places、法规名称、条款和 Requirement 检查词都应参与召回，并保留相关度排序和搜索回归测试。
6. 搜索可以宽召回；verified 状态仍必须严门禁，语义相似度不能自动证明法规适用性。

后续应在合适节点把该补充整合进 `PROJECT_PLAYBOOK.md`、`ARCHITECTURE_V4_CHAT_FIRST.md` 和 `GATE_V4.md`，但不得因此阻塞当前 link 复核。

## 179 条 Link Candidate 状态

本地 Agent 已完成 179/179 candidate migration：

- 178 `direct`
- 1 `fallback`
- 初始 review 全部为 `pending`
- review sidecar 已保存 V3 applicability reason、contextHashes 和 evidenceRefs
- 不允许因为 V3 曾 passed 就批量自动升级 V4 verified

### 已专业复核前 10 条

当前结果：**3 verified / 4 rejected / 3 pending**。

1. `K_006af5b6d4446159a05ac5f7b4` — **verified**：消防设施年度检测记录与《消防法》对应条款直接吻合。
2. `K_00bb5b7226cf0cfd890c781e` — **rejected**：通用消防法线路义务不足以 direct 支撑仓储线路必须穿特定保护管的具体技术要求。
3. `K_012500360729ae5276213ac4` — **pending**：Hazard 合并多项管理义务，单一 Clause 仅部分覆盖，应拆分或补齐 links。
4. `K_015967d6f6a697f197ebbdad` — **rejected**：通用安全警示标志义务不能 direct 推出危化品暂存间必须标明“名称、性质、灭火方法”的具体内容。
5. `K_0193ab27f4a0e63fd8f1ecf5` — **rejected**：Hazard 实际文本为“未见混杂”，不是隐患事实；且员工宿舍条款不能泛化为全部办公生活区域。
6. `K_01DD57C7DD1768B0CD4B56F12C` — **verified**：GB 18597-2023 第4.6条与危险废物识别标志缺失直接对应；旧 conditions 条号留待清理。
7. `K_03BF627B0B2DF4D35F2FCF5C39` — **pending**：Hazard 同时混合液体泄漏与气体净化，当前 Clause 仅覆盖液体要求。
8. `K_04361764d56792472364b113` — **pending**：Hazard 同时包含责任制、规章制度、应急预案等，多义务需拆分/补齐 Clause。
9. `K_04BD5E63412B9DEE6F3374C7F3` — **rejected**：液体泄漏收集 Hazard 错挂到气体收集净化条款，技术对象明显不一致。
10. `K_04cdf5ee09cb1c9b9690bc5a` — **verified**：在危化品试剂间属于较大危险因素场所的前提下，通用安全警示标志义务直接适用；不扩张为 GB 13690 等专项危险性公示要求。

上述 review 已写入对应 `knowledge/reviews/links/*.json`，reviewer=`ChatGPT`，并绑定当前 link/hazard/clause hashes。

## 当前暴露出的数据质量问题

第一批 10 条已证明历史 V3 `passed` 不能直接等价为 V4 professional verified，主要问题类型包括：

- `DIRECT_ROLE_OVERSTATED`：依据过宽却标成 direct；
- `SPECIFIC_CLAUSE_REQUIRED`：需要更具体专项条款；
- `COMPOSITE_HAZARD`：一条 Hazard 混合多个独立义务；
- `PARTIAL_CLAUSE_COVERAGE`：单一 Clause 只覆盖 Hazard 一部分；
- `FACT_NOT_HAZARD`：历史文本实际描述“未发现问题”；
- `SCOPE_MISMATCH`：法规对象/场景和 Hazard 不一致；
- `TECHNICAL_OBJECT_MISMATCH`：液体、气体等技术对象错配。

后续应持续使用这些 reasonCodes 做质量归类，并在 Phase 8 集中修复历史 Hazard/Link 结构问题。

## 下一步

### 主任务：继续 169 条 Link applicability 专业复核

从尚未复核的下一条 Stable-ID 排序 candidate 开始，逐条读取：

`Link → Hazard → Clause → LawVersion/Law（需要时）→ Review/Evidence`

判断：

- role 是否应为 `direct / supporting / fallback`；
- applicability 是否真实覆盖当前 Hazard；
- jurisdiction / 对象 / 条件 / 限值是否匹配；
- 是否存在新版/旧版条款错挂；
- 是否需要更具体专项条款；
- 是否属于组合型 Hazard 需要拆分。

结论规则：

- 明确成立 → `verified`
- 明确错误 → `rejected`
- 需要拆分、补证或法规专项核验 → `pending`

不得为了提高通过率而把疑问项强行 verified。

建议每 10～20 条形成一个 review commit；每批结束后更新本文件的累计统计。

### 并行工程任务

本地工程 Agent 可以继续处理不涉及法规最终判断的工作，例如：

- catalogue law/current version 的候选准备；
- validator / report 工具；
- V4.1 Requirement schema/脚手架；
- 搜索回归测试脚手架；
- 数据质量扫描。

但不得并发修改 ChatGPT 正在复核的同一批 link review sidecar。

## 后续 Phase

1. 完成 179 link applicability 专业复核及必要修复。
2. 补 catalogue law/current version。
3. Phase 7：法规与标准核验框架，纳入完整法规结构化、Requirement 提取、版本影响分析。
4. Phase 8：历史报告条款与组合型 Hazard 重审。
5. Phase 9：Validator，增加 Requirement/schema/hash/context 及搜索索引检查。
6. Phase 10：Gate，增加 Requirement 和搜索非退化验收规则。
7. Phase 11～16：候选 release、网站构建、搜索回归、V3/V4 对比、差异修复与验收。
8. Phase 17：仅用户明确批准后切换生产。

## 明确禁止

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

## 当前阻塞

无需要用户决策的阻塞。当前工作可以继续推进。