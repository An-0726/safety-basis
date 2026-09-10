# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目时必须先读取本文件、`docs/V4_FINAL_ACCEPTANCE.md`、`docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`、`knowledge/manifest.json`，并核对 `chat-v4` 当前真实 HEAD 与最新 V4 Final Acceptance CI。聊天历史不得覆盖真实文件状态。

## PROJECT_STATUS

ACTIVE — Phase 16 最终验收正在执行。技术 Validator / Gate / Strict / 搜索 / 确定性构建已在当前知识基线上通过，但人工法规版本、Hazard→Clause 适用性、Requirement、V3/V4 最终差异以及页面/PWA/隐私终审尚未全部收口，因此不得提前标记 READY_FOR_ACCEPTANCE。

## 当前总目标

在保留 V3 Stable ID、法规身份/版本/条款、可靠隐患、正确关联、证据、历史 release 和网站能力的基础上，完成 Chat-first V4；由 ChatGPT 负责 Phase 16 最终总检查、问题修复和收口。全部验收通过后再把项目状态改为 `READY_FOR_ACCEPTANCE`；只有用户明确批准才进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

**Phase 16：最终验收。**

不得再使用此前错误的“Phase 22”编号。正式施工顺序仅为用户定义的 Phase 1–17。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub / Knowledge

本轮机器终审使用的最新知识基线：

`cd29037630c9f52688692ab3f9212bd7dc9fde9d`

该基线之后本轮新增的是验收文档/报告提交，不改变 `knowledge/**/*.json`，因此下述 `sourceStateHash` 仍对应当前知识内容。下一轮开工仍必须重新读取实际 HEAD，不能直接假定本文件记录的是远端最新 commit。

当前 knowledge counts：

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- requirements: 75
- evidence: 567
- successions: 23

`knowledge/manifest.json` 已纠正为 Phase 16，并将 scope 从历史 68 laws / 662 hazards / 181 links 更新到当前规模。

### V3 冻结基线

- `source/master/safety.sqlite3`
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 本轮未修改。

### 当前最新机器 Candidate

知识基线 `cd290376...` 对应的 V4 Final Acceptance CI：

- run id: `34453384587`
- artifact id: `10142435867`
- artifact name: `v4-final-acceptance-cd290376`
- candidate sourceStateHash: `545a828e653fe634754d50699c7e321448dbac25396500b15c1a015f1a0e0e5f`
- candidate: true
- production: false
- publishable hazards / eligible hazards: 596
- eligible links: 666
- strict audit: PASS
- blockerCount: 0
- warningCount: 60
- excludedCount: 105
- search regression: 20/20 PASS
- deterministic build: PASS

注意：仓库现有 `source/releases/v4-candidate-20260910/` 是知识修改前的 tracked candidate，不应只手工改一个 `release.json` 来冒充完整最新候选。当前最新完整 candidate 证据是上述 CI artifact。待知识树最终稳定后，应生成新的完整 final candidate 路径/版本并整体提交，而不是局部覆盖旧候选。

### Google Drive

`ESH_Codex/work/safety-basis` 本轮开工已确认可访问。本轮未覆盖 Drive 正式文件，未修改 SQLite/fulltext。

## 本轮完成

1. 建立正式 Phase 16 总验收框架 `docs/V4_FINAL_ACCEPTANCE.md`，明确 A–J 验收域和 READY_FOR_ACCEPTANCE 条件；确认最终验收由 ChatGPT 负责，用户只需对 Phase 17 生产切换做最终授权。
2. 修正 `knowledge/manifest.json` 的旧 scope 数字和错误 Phase 22 标记，统一为 Phase 16。
3. 将旧 `docs/V4_STRICT_AUDIT.md`、`docs/V3_V4_DIFF_REPORT.md` 从过期统计中纠正出来，禁止旧 162/209、543/596 等中途数字继续冒充最终状态。
4. 新增 `.github/workflows/v4-final-acceptance.yml`，形成自动终审闭环：integrated validator → candidate build → 六阶段 Gate → strict audit → acceptance inventory → search regression → candidate-only 边界 → 两次确定性构建 → knowledge mutation check → artifact。
5. 新增 `tools/v4/final_acceptance_inventory.py` 和 `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`，把真实终审库存形成机器可重复生成的报告。
6. 首轮终审发现此前“只剩 1 条未 publishable hazard”的过程结论不正确。真实非发布结构原为 66 superseded + 50 active 无合格 direct/fallback；本轮进一步纠正一条正向事实后变为 67 superseded/merged + 49 active 无合格 direct/fallback。
7. 逐条确认 `H_A73EC0543AA24DF583F70E566B` 的正文是“未见与办公生活区域混杂布置情况”，属于正向事实而不是隐患。保留 Stable ID，lifecycle 改为 `superseded`，Hazard review 改为 superseded；其 `K_0193ab27f4a0e63fd8f1ecf5` direct link 继续 rejected，并重新绑定 hazard context hash。
8. 修复 `tools/v4/scan_evidence_exact.py`：EXPECT 现在是 allowlist；未配置来源只记 UNMAPPED；真实 mismatch 才记 MISMATCHED；MISMATCHED > 0 返回非零退出码，确保 CI/Gate 能真正阻断。
9. 最新机器终审在知识基线 `cd290376...` 上全绿：六阶段 Gate 全 PASS、Strict PASS、blocker=0、搜索 20/20、确定性构建 PASS、knowledge mutation=0。
10. 发现 `docs/V4_GATE_REPORT.md` 曾被并发流程污染成 PowerShell/Python traceback；已恢复为当前真实 Gate 结果，并明确“技术 Gate PASS ≠ Phase 16 总验收完成”。

## 本轮修改文件

主要文件：

- `docs/V4_FINAL_ACCEPTANCE.md`
- `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`
- `docs/V4_GATE_REPORT.md`
- `docs/V4_STRICT_AUDIT.md`
- `docs/V3_V4_DIFF_REPORT.md`
- `docs/CHAT_HANDOFF.md`
- `knowledge/manifest.json`
- `.github/workflows/v4-final-acceptance.yml`
- `tools/v4/final_acceptance_inventory.py`
- `tools/v4/scan_evidence_exact.py`
- `knowledge/hazards/H_A73EC0543AA24DF583F70E566B.json`
- `knowledge/reviews/hazards/H_A73EC0543AA24DF583F70E566B.json`
- `knowledge/reviews/links/K_0193ab27f4a0e63fd8f1ecf5.json`

## 本轮校验

知识基线 `cd290376...` 的 V4 Final Acceptance CI：

- check_catalogue: PASS（75 laws / 75 lawVersions / 88 clauses / 23 successions）
- check_requirements: PASS（75 requirements）
- dangling references: 0
- unbound link reviews: 0
- stale link content hash: 0
- stale hazard context hash: 0
- stale clause context hash: 0
- exact evidence mismatch: 0
- Gate STRUCTURAL: PASS
- Gate CONTENT: PASS
- Gate APPLICABILITY: PASS
- Gate VERSION: PASS
- Gate EVIDENCE: PASS
- Gate RELEASE: PASS
- strict verdict: PASS
- blockerCount: 0
- search regression: 20 / 20 PASS
- deterministic double-build: PASS
- candidate=true / production=false: PASS
- acceptance tools modified knowledge: NO

自动质量扫描仍给出语义终审候选：

- stale old-standard refs in hazard fields: 14
- obligation-restatement candidates: 11
- links to merged hazards: 9
- partial-replaced standard hazard hits: 12
- full-replaced standard hazard hits: 0

这些不是自动确认错误，必须在 Phase 16 专业复核后分类。

## 当前项目状态

### 发布链

- total hazards: 712
- publishable: 596
- eligible links: 666
- link reviews: 716 verified / 19 rejected
- 716 是 review 决策口径，666 是通过完整共享链式 Gate 的发布依据口径；不得混用。

### Requirement

- verified: 55
- pending: 20

### 非发布库存

- active hazards without qualifying direct/fallback: 49
- verified supporting-only links: 11
- superseded/merged hazards: 67
- rejected links: 19
- repealed lawVersions: 18
- upcoming lawVersion: 1

49 条 active 非发布 hazard 的完整清单已经保存到 `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`。它们目前不泄漏到公开 release，因此不是当前生产内容 blocker；但 Phase 16 必须逐条判断是否应补直接依据、合法留作 backlog、改类、或确认并非隐患。

## 未完成事项

1. 对 49 条 active 无合格 direct/fallback 的 hazard 逐条专业终审，不得批量强行建链。
2. 继续 20 条 pending Requirement 的逐条语义校准。
3. 对 14 条旧标准引用候选和 12 条 partial-replaced standard hit 做当前官方来源时效核验。
4. 处理 11 条 obligation-restatement candidates。
5. 处理 9 条 links-to-merged-hazard candidates。
6. 最终刷新 `docs/V3_V4_DIFF_REPORT.md`，做 Stable ID/内容/法规链/搜索/页面语义差异验收。
7. 完整执行候选网站页面、筛选、law index、PWA/Service Worker、隐私公开投影验收。
8. 知识树最终稳定后生成新的完整 final candidate，并重跑全套验收；之后生成最终验收报告。
9. 只有全部完成后才把 PROJECT_STATUS 改为 `READY_FOR_ACCEPTANCE`。

## 下一轮第一步

读取本文件和 `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md` 后，从 49 条 active 无合格依据 hazard 中开始**第一批逐条专业终审**，优先处理常见且价值高、可通过当前官方来源明确核验的：

`H043`（仓储消防教育培训）、`H046`（江苏主要负责人季度全面检查）、`H048`（江苏年度全面风险辨识）、`H049`（事故抢救和如实报告）、`H052`–`H055`（仓储堆放距离）、`H058`、`H067`、`H069`（仓储消防管理）、`H065`（易燃气体与助燃气体同库）、`H079`（建设项目安全设施设计）。

逐条执行：读取 Hazard → 查现有 links/clauses → 当前官方网页核法规/标准版本与原文 → 判断 direct/fallback/supporting/不适用 → 保存 review/证据 → 每小批次重跑 V4 Final Acceptance CI。不得因为覆盖率目标自动 verified。

如果第一批中某条需要新标准 clause，先核条款原文和现行版本后再新增；找不到可靠证据就继续保持非发布，不阻断其他条目。

## 后续任务

1. 继续剩余 49 条 active 非发布 hazard 的风险导向终审。
2. 穿插完成 20 条 pending Requirement，避免最终阶段只清 links 不清义务层。
3. 收口版本影响队列（14 / 12）。
4. 收口 obligation/merged-link 队列（11 / 9）。
5. 最终 V3/V4 diff。
6. 页面/PWA/隐私验收。
7. final candidate + full validator/gate/strict/deterministic rebuild。
8. 最终验收报告 → `READY_FOR_ACCEPTANCE`。
9. 用户批准后才进入 Phase 17。

## 法规/标准待核验队列

高优先级：

- 2026《中华人民共和国危险化学品安全法》与既有《危险化学品安全管理条例》/相关规章的现行并存、替代和条款适用边界。
- 江苏省安全生产地方规则：主要负责人季度全面检查、年度风险辨识等具体义务。
- 仓储消防管理类直接依据：培训、堆垛距离、防雷、重点岗位培训等。
- 易燃气体与助燃气体分库存放直接技术依据。
- 建设项目安全设施设计“三同时”直接依据。
- 14 条 hazard 旧标准引用候选。
- 12 条 partial-replaced standard hazard hits。

证据不足的维持 pending/非发布。

## 风险 / 阻塞

当前没有必须用户决策才能继续 Phase 16 的 blocker。

已知风险：

- 过去过程报告曾错误声称“只剩 1 条未 publishable hazard”；现已由机器库存纠正为真实 49 条 active 无 qualifying link + 67 条 superseded/merged，后续必须以 inventory 为准。
- `docs/V4_GATE_REPORT.md` 曾被并发操作污染成 traceback；下一轮开工需回读，发现并发覆盖立即以 CI/真实文件纠正，禁止 force push。
- tracked `source/releases/v4-candidate-20260910/` 不是当前知识变更后的完整最终候选；不要只更新 release.json hash。最新机器完整候选在 CI artifact，待知识稳定后整体生成新 final candidate。
- 自动质量扫描的 14/11/9/12 是候选，不可机械当成错误或机械清零。
- 49 条 active 非发布项目前不会进入公开投影，但是否应进入最终产品仍需逐条专业判断。

## 用户待决策事项

当前无。

未来唯一必须用户决定的高影响事项：Phase 16 全部验收通过、状态达到 `READY_FOR_ACCEPTANCE` 后，是否批准 Phase 17 正式 production 切换。

## 明确禁止事项

- 不得修改 `main`
- 不得正式切换 production
- 不得切换 GitHub Pages 正式数据源
- 不得用旧 release 覆盖新 release
- 不得用旧数据库覆盖新数据库
- 不得修改 V3 冻结 SQLite/fulltext
- 不得 force push
- 不得把历史报告中的法规条款未经现行核验直接当当前有效依据
- 不得为了提高 publishable 数量批量把 link 改 direct/verified
- 不得使用同一证据机械证明不同条款/隐患
- 不得把泛上位法包装成具体技术依据
- 不得让私有 Drive 路径/资料进入公开发布数据
