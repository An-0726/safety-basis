# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目时必须先读取本文件、`docs/V4_FINAL_ACCEPTANCE.md`、`docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`、`knowledge/manifest.json`，并重新核对 `chat-v4` 真实 HEAD、最新 V4 Final Acceptance CI 和 Google Drive `ESH_Codex/work/safety-basis`。聊天历史不得覆盖真实文件状态。

## PROJECT_STATUS

ACTIVE — Phase 16 最终验收继续执行。H043、H049、H046、H048 已完成专业终审；H046/H048 的结构化收口（过期交接说明清理 + review/hash 重绑）本轮已完成并通过全套机器验收。但全库仍存在**公开投影工作中间态泄漏**（43 条 active hazard 的 `note` 仍写"尚未完成逐条官方原文终审；核验完成前不得进入公开运行库"，却已进入 candidate 公开投影）、9 条已 verified 的 link review 自身 `reasonCodes` 仍声明需要专项条款、9 处非官方证据来源、20 条 pending Requirement、14 条旧标准引用、12 条 partial-replaced hit、11 条 obligation-restatement、9 条 links-to-merged-hazard，以及 manifest 精确对账、V3/V4 最终差异和页面/PWA/隐私验收未收口，因此不得标记 READY_FOR_ACCEPTANCE。

## 当前总目标

在保留 V3 Stable ID、法规身份/版本/条款、可靠隐患、正确关联、证据、历史 release 和网站能力的基础上完成 Chat-first V4。全部 Phase 16 验收通过后才可改为 `READY_FOR_ACCEPTANCE`；只有用户明确批准才进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

**Phase 16：最终验收。**

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub / Knowledge

上一轮交接 HEAD 为 `a7e4321`（docs: hand off H046 H048 final reviews）。本轮从该提交继续，未 reset、未 force push。

真实知识树实测计数（本轮直接扫描 `knowledge/` 所得，非引用旧文档）：

- laws：76
- lawVersions：76
- clauses：92
- hazards：712
- links：739
- evidence：572
- requirements：75
- successions：23
- reviews/hazards：712，reviews/links：739，reviews/clauses：92，reviews/laws：76，reviews/law-versions：76

最近一次机器发布链结果（本轮重跑）：

- publishable hazards：645
- eligible links：719
- link review：719 verified / 20 rejected
- strict release blockers：0
- strict warningCount：11（全部为 supporting_link）
- strict excludedCount：106
- candidate=true / production=false

`knowledge/manifest.json` 仍为旧计数（laws 75 / lawVersions 75 / clauses 88 / links 735 / evidence 567），需精确对账。实测差额为 +1 law、+1 lawVersion、+4 clauses、+4 links、+5 evidence，hazards/successions/requirements 一致。

### V3 冻结基线

- `source/master/safety.sqlite3`
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 本轮未修改 V3 SQLite / fulltext。

### Google Drive

本轮未重新执行 Drive 逐目录审计，以 GitHub `chat-v4` 作为 V4 日常工作面。涉及数据库、私有报告、标准原件或大型产物时仍须重新核对 `ESH_Codex/work/safety-basis` 的具体版本、时间和大小。

### 最近一次已确认成功 Candidate / CI

本轮在本机重跑并确认（顺序与 CI 一致）：

- integrated validator：PASS
- candidate build：PASS（确定性构建两次 diff 一致）
- STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE：全部 PASS
- strict release audit：PASS，blockerCount=0
- search regression：20/20 PASS
- candidate-only 边界：保持（production=false）
- 验收工具未反向修改 `knowledge`

## 本轮完成

1. 按真实 GitHub 状态恢复现场：确认 `chat-v4` 真实 HEAD 为 `a7e4321`，本地无未推送提交，远端不是交接计划书中的 `c9b21ab`（该提交已是历史）。
2. 核对 H049 已由并行提交 `c9b21ab` 完成内容绑定刷新，未重复修改。
3. 核对 H046/H048 的结构化依据确实已存在且审核通过：
   - `H046 → C_JS32_15_1`（direct，ChatGPT 审核）＋ `H046 → C017`（fallback，豆包）
   - `H048 → C_JS32_15_3`（direct，ChatGPT 审核）＋ `H048 → C024`（fallback，ChatGPT 审核）
   - `LF_L020 江苏省安全生产条例`（L020，2023-07-01 起施行，来源 flk.npc.gov.cn）复用 V3 Stable ID，未新建重复实体。
4. 完成 H046/H048 结构化收口：移除两条 hazard `note` 中已过期的"交接状态：…尚未完成逐条官方原文终审；核验完成前不得进入公开运行库"段落，并同步刷新受影响的内容绑定：
   - `knowledge/reviews/hazards/H046.json`、`H048.json` 的 `reviewedContentHash`
   - 4 条 link review 的 `contextHashes.hazard`（K_c68b66ed…/K_eb3ae934…/K_0bbd8d2d…/K_c3b9ac7d…）
   - H046 内容哈希 921089b3… → 912b62cc…；H048 dc1b62ae… → a56a444b…
5. 确认修复后公开发布投影中 H046/H048 的 `note` 已不带过期说明，并且两条 hazard 仍保持可发布（645 条未减少）。
6. 全库扫描发现并记录一项系统性缺陷：**45 条 active hazard 的 `note` 仍是同一模板的过期交接说明，且全部进入 candidate 公开投影**（H033–H081 连续区间中除已收口的 H043/H046/H048/H049 外共 45 条）。其中 9 条的 link review `reasonCodes` 自身声明仍缺专项条款（H036/H039/H063/H064/H068 = SPECIFIC_CLAUSE_REQUIRED，H047 = DIRECT_STANDARD_PENDING，H066/H073 = DIRECT_CLAUSE_NEEDED），说明这些条目的"尚未终审"表述仍然准确，**不得批量删除**，必须逐条完成终审后再清理。
7. 另记录 8 条 `H_*` Stable ID hazard 的 `note` 带【Phase8】实质待办（原标准已被新标准替代、新版条款号待核验 + 义务条款复述型描述候选），属 14/12 版本队列，需真正核验而非删除。
8. `knowledge/reviews/links/K_18fef2d1546e124d7e828d3039.json` 的 `reason` 残留"发布门禁需同步处理"待办语句，待清理。

## 本轮修改文件

- `knowledge/hazards/H046.json`
- `knowledge/hazards/H048.json`
- `knowledge/reviews/hazards/H046.json`
- `knowledge/reviews/hazards/H048.json`
- `knowledge/reviews/links/K_0bbd8d2da630b657d0ed4520.json`
- `knowledge/reviews/links/K_c3b9ac7d5380e0f9ffc919cf.json`
- `knowledge/reviews/links/K_c68b66ed9601e8a33de23809.json`
- `knowledge/reviews/links/K_eb3ae9347005b98332d2ddca.json`
- `docs/V4_GATE_REPORT.md`（门禁脚本重写的最新机器结果）
- `source/releases/v4-candidate-20260910/**`（按当前知识树完整重建，非手工改 release.json）
- `docs/CHAT_HANDOFF.md`

## 本轮校验

- `python tools/v4/validate_all.py`：6/6 PASS，BLOCKING failures: none。
- `check_catalogue`：laws 76 / lawVersions 76 / clauses 92 / successions 23，errors 0。
- `check_requirements`：requirements 75，errors 0。
- `check_review_binding`：reviews 739，unbound 0，stale link hash 0，stale hazard ctx 0，stale clause ctx 0。
- `scan_evidence_exact`：MISMATCHED 0。
- `py tools/v4/build_release.py`：publishable hazards 645 of 712，eligible links 719 of 739。
- 确定性构建：连续两次构建 `diff -r` 一致，PASS。
- `py tools/v4/gate_v4.py`：六阶段全部 PASS。
- `py tools/v4/strict_release_audit.py`：strictVerdict PASS，blockerCount 0。
- `py tools/v4/test_search.py`：20 cases，failed 0。
- `git diff --exit-code -- knowledge`：验收工具未修改知识树（仅本轮 8 个文件为本意修改）。
- `main` / production / GitHub Pages / V3 SQLite：未修改。

## 当前项目状态

### 发布链

- total hazards：712
- active / machine-eligible hazards：645
- eligible links：719
- link reviews：719 verified / 20 rejected
- active hazards without qualifying direct/fallback：0
- superseded/merged hazards：67
- supporting verified links：11
- candidate=true / production=false

### Requirement

- verified：55
- pending：20

### 已完成高价值终审

- H043：`XF 1131-2014 3.3.2` 专项直接依据 + 《安全生产法》第二十八条上位法兜底，已收口。
- H049：《安全生产法》（2021年修正）第八十三条为精确直接依据；第八十一条误配保持 rejected。
- H046：《江苏省安全生产条例》（2023年修订）第十五条第一项为精确地方直接依据，每季度至少一次全面检查；结构化收口本轮完成。
- H048：《江苏省安全生产条例》（2023年修订）第十五条第三项为精确地方直接依据，每年至少一次全面安全风险辨识；结构化收口本轮完成。

### 审核来源构成（判断"是否真正核完"的关键证据）

- 法规 law（76）：ChatGPT 直接终审 26；其余 50 为 V3 迁移审核（standard_metadata_review / engineering_standards_review / 各 META-WORK 子代理 / Codex 主核验）。
- 版本 lawVersion（76）：ChatGPT 直接终审 19；其余 57 为 V3 迁移或豆包；有效力状态 active 57 / repealed 18 / upcoming 1。
- 条款 clause（92）：ChatGPT 直接终审 26；其余 66 来自豆包续接集成 / 全文库核验 / Doubao-MainAgent / agent2-backfill。
- 关联 link（739）：豆包系列 705（Doubao-Agent 669 + Doubao-Agent-Sub3 28 + doubao-subagent2-v4 8），agent2-backfill 20，ChatGPT 仅 14。
- 隐患 hazard（712）：V3 迁移 688（并发重验批次 410 / Codex 主核验 240 / doubao-work 系列 38），直接 reviewer 仅 24。
- 条款正文与定位完整性：0 条缺 `quote`、0 条缺 `articlePath`；4 条缺 `sourceUrl`。
- 版本日期完整性：0 条缺 `effectiveDate`；19 条缺 `sourceUrl`，其中仅 `LV_GB50016_2014`（建筑设计防火规范 GB 50016-2014（2018年版））为现行 active，另 18 条为 repealed 历史版本。
- 非官方来源 9 处：`gzhxaq.com` 1（同时被 1 条 clause 与 1 条 evidence 使用）、`www.zhc.dicp.ac.cn` 6、`cli.im` 1。

## 未完成事项

1. 逐条完成 45 条 active hazard 的专业终审，再清理其 `note` 过期说明并刷新绑定；禁止批量删除（其中至少 9 条的 review 自身声明尚缺专项条款）。
2. 处置 8 条 `H_*` hazard 的【Phase8】版本待办：确认 GB 15603-2022 / GB 5083-2023 / GB 2893 / GB 2894 等新版对应条款号，并判断义务条款复述型描述是否改写。
3. H052-H055、H058、H065、H067、H069、H079 等高价值 link 做现行版本、条款原文和适用范围终审。
4. 完成 20 条 pending Requirement 逐条语义校准。
5. 终审 14 条旧标准引用候选和 12 条 partial-replaced hit。
6. 处理 11 条 obligation-restatement candidates。
7. 处理 9 条 links-to-merged-hazard candidates。
8. 补 4 条缺 `sourceUrl` 条款与 19 条缺 `sourceUrl` 版本的官方来源（优先 `LV_GB50016_2014`）；复核 9 处非官方证据来源，尤其是 `cli.im`。
9. 精确对账并修正 `knowledge/manifest.json`（含 evidence 572），禁止猜数；`tools/v4/sync_manifest.py` 内仍是错误的 Phase 22 与旧 scope 文本，需一并修正。
10. 刷新最终 `docs/V3_V4_DIFF_REPORT.md`。
11. 执行候选网站页面、筛选、law index、PWA/Service Worker、隐私公开投影验收（含 43 条过期说明泄漏项）。
12. 知识树最终稳定后生成完整 final candidate 并跑最终全套验收。
13. 全部 Phase 16 收口后才改 `READY_FOR_ACCEPTANCE`。

## 下一轮第一步

**继续 45 条 active hazard 的逐条专业终审，优先 review 自身声明尚缺专项条款的 9 条（H036/H039/H047/H063/H064/H066/H068/H073 及相关条）与 8 条【Phase8】版本待办。** 每条完成后：清理 note 过期说明 → 刷新 hazard review 与 link review 绑定 → 跑 validate_all / build_release / gate_v4 / strict_release_audit，确认 eligible 数不下降、blocker 仍为 0。

## 后续任务

1. 45 条 note 中间态清理（随各自终审完成）。
2. H052-H055、H058、H065、H067、H069、H079 终审。
3. 20 条 pending Requirement。
4. 14 条旧标准 + 12 条 partial replacement + 8 条 Phase8 待办。
5. 11 条 obligation-restatement + 9 条 merged-link。
6. 来源缺口补齐与非官方来源复核。
7. manifest 精确对账 + `sync_manifest.py` 修正。
8. 最终 V3/V4 diff。
9. 页面/PWA/隐私验收。
10. final candidate + 全套 validator/gate/strict/deterministic build。
11. 最终验收报告 → `READY_FOR_ACCEPTANCE`。
12. 用户批准后才进入 Phase 17。

## 法规/标准待核验队列

高优先级：

- GB 50016-2014（2018年版）现行有效性与官方来源补齐（3 条条款无来源）。
- 仓储堆垛距离、仓储物品与照明灯/墙/柱安全距离（H052-H055）现行标准版本及条款。
- 易燃气体与助燃气体同库储存（H065）的直接技术依据。
- 建设项目安全设施设计"三同时"（H042）直接依据。
- 2026《中华人民共和国危险化学品安全法》与既有危险化学品行政法规/规章的现行并存和替代边界。
- GB 15603-2022、GB 5083-2023 等新版条款号回填（8 条 Phase8 待办）。
- 14 条旧标准引用候选、12 条 partial-replaced hits。

## 风险 / 阻塞

当前没有必须用户决策才能继续 Phase 16 的 blocker。

已知风险：

- **公开投影泄漏工作中间态**：43 条 active hazard 的 `note` 写着"核验完成前不得进入公开运行库"，却已进入 candidate 公开投影。candidate 尚未上线，但这是上线前必须清零的项。
- 45 条中的过期说明不能批量删除：至少 9 条的 review 自身声明仍缺专项条款，删说明会掩盖真实状态。
- 关联层审核 95.4% 来自豆包批量流程，不能等同于逐条专业终审；机器 blocker=0 只说明数据链满足发布规则。
- `knowledge/manifest.json` 计数滞后，evidence 精确总数（572）已实测但尚未写回。
- `tools/v4/sync_manifest.py` 会把 `migrationPhase` 写回错误的 Phase 22 并写入旧 scope 文本，使用前必须修正。
- `tools/v4/gate_v4.py` 每次运行会整体重写 `docs/V4_GATE_REPORT.md`，人工元信息不保留；人工状态统一维护在本文件与 `docs/V4_FINAL_ACCEPTANCE.md`。
- `tools/v4/check_review_binding.py` 只按文件名匹配 link id，会静默跳过 19 个 `RV_*` 命名的 review 文件（官方门禁 `release_gate_core.load_reviews` 按 `entityId` 索引，不受影响）。
- GitHub 可能存在并发提交；每轮必须重新核真实 HEAD，不能依赖本文件记载的旧 SHA。
- Drive 本轮未逐文件审计；使用私有文件时必须重新核对。

## 用户待决策事项

当前无。Phase 16 可继续自动推进。

只有进入 Phase 17、修改 `main` 或正式切换生产网站时需要用户明确批准。

## 明确禁止事项

- 不修改 `main`
- 不切换生产网站 / GitHub Pages 正式数据源
- 不覆盖 V3 SQLite 冻结基线
- 不用旧 release / 旧报告覆盖新成果
- 不因机器 Gate 全绿自动宣告法规语义全部正确
- 不批量假定 links 正确，不重演 r8 质量事故
- 不为提高发布数量强行建立或 verified 依据
- 不把通用上位法包装成具体技术 direct 依据
- 不因缺少整本标准全文而编造条款；可靠局部条款可按证据等级核验
- 不批量删除"尚未终审"类说明以制造已完成的假象
