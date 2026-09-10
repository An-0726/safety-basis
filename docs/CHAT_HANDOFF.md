# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。恢复项目时必须先读取本文件、`knowledge/manifest.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub / Google Drive 真实文件为准。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

主体迁移、关联复核、Validator、Gate、候选网站、候选 release、V3/V4 差异检查均已完成机制或主要工作；当前处于**最终验收与遗留项收口阶段**。

当前优先问题不是继续旧 Phase 6 批量迁移，而是：
1. 同步已经继续前移的真实知识状态；
2. 收口 pending link / 补迁 hazard / Requirement 等遗留项；
3. 基于最新状态重建 candidate release 并重新执行 RELEASE 级验收。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub

本轮开始时真实 HEAD 为 `9544c49d43e39dda68f024d1b73b92acbe49de7a`，提交说明为 `fix: verify pending standard dates and 12801 transition`；它晚于上一版 handoff 所记载的 `6d075c6`，因此上一版 handoff 已部分滞后。

本轮随后提交：
- `91ed7a78e03eff4ae1b0ca1841ad9a7a01b44505` — 修正 `docs/V4_GATE_REPORT.md` 中错误的 RELEASE 状态。

本 handoff 提交位于其后；下一轮仍须重新读取 `chat-v4` 获取最终真实 HEAD，禁止把这里记录的前置提交号当成永远不变的最终 HEAD。

### 当前知识规模（最近一次完整统计）

最近一次完整 handoff 统计为：
- laws：68
- lawVersions：68
- clauses：76
- requirements：75（草案，全部 pending）
- hazards：662
- links：181
- evidence：552
- successions：19

Link review 最近一次完整统计：
- verified：127
- rejected：15
- pending：39
- 合计：181

注意：`knowledge/manifest.json` 当前仍保留早期 Phase 6 汇总值（43 laws / 43 lawVersions / 54 clauses / 642 hazards / 179 links / 548 evidence / 2 successions），**已经明显落后于后续 catalogue、GB 2894、20 条 hazard 补迁以及最终 link review 等真实成果**。因此 manifest 当前不能作为最终计数事实源，下一轮应先同步它。

### V3 冻结基线

`knowledge/manifest.json` 仍记录 V3 SQLite SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`；本轮未修改 V3 SQLite。

Google Drive 搜索确认 `ESH_Codex/work/safety-basis` 相关历史架构/交接/导出资料仍可访问；本轮没有对 Drive 文件执行写入。对 `safety.sqlite3` / `fulltext.sqlite3` 的精确元数据没有取得比既有冻结记录更强的新证据，因此不得改写既有冻结 hash / size 结论。

### Candidate release

现有候选：`source/releases/v4-candidate-20260910/`

`release.json` 当前记录：
- candidate=true
- production=false
- laws=68
- law_versions=68
- clauses=76
- hazards=662
- links=181
- requirements=75
- reviewStats=114 verified / 14 rejected / 32 pending
- sourceStateHash=`fae429fff4aad1493d579143b8dbbf40904786ff332f24de949cb07ada47afe6`

这组 reviewStats 与当前真实 link review 统计 127 / 15 / 39 不一致；候选包生成后 `chat-v4` 还继续修正了法规版本元数据。因此该 candidate 已是**历史候选快照**，不能作为当前 HEAD 的发布一致性证明。

## 本轮完成

1. 按 HEAD-first 原则重新核对真实分支，发现施工期间 `chat-v4` 已从旧 handoff 记载状态继续前移到 `9544c49...`。
2. 核对现有 candidate release，确认候选构建实际已经执行，旧 `docs/V4_GATE_REPORT.md` 中 `RELEASE: NOT_RUN (candidate build pending)` 属于文档滞后。
3. 同时确认现有 candidate 的 reviewStats 已落后于当前知识库，且候选生成后又发生法规版本数据修正，因此不能把 RELEASE 直接改成 PASS。
4. 将 `docs/V4_GATE_REPORT.md` 的 RELEASE 状态改为 `REVIEW_REQUIRED`，明确要求基于最新 HEAD 重建 candidate 后重新跑完整发布级验收。
5. 识别出 `knowledge/manifest.json` 自 Phase 6 后未同步后续实体规模，是当前另一项明确状态债务；已在本 handoff 标记为下一轮第一步。

## 本轮修改文件

- `docs/V4_GATE_REPORT.md`
- `docs/CHAT_HANDOFF.md`

未修改知识实体、V3 SQLite、fulltext、现有 candidate 内容、`main`、production 或 GitHub Pages 数据源。

## 本轮校验

- 当前 candidate 确认存在，`candidate=true`、`production=false`。
- candidate `reviewStats=114/14/32` 与当前完整 review 统计 `127/15/39` 不一致，因此 RELEASE 不满足当前状态一致性要求。
- `docs/GATE_V4.md` 明确将 Stage 6 定义为 Release 一致性与确定性校验，因此当前采用 `REVIEW_REQUIRED` 而非虚假 PASS。
- 检测并尊重并发前移：在写入前重新读取真实 HEAD；没有 force update，没有回退覆盖并发成果。
- Google Drive 只读查询；未修改任何 Drive 资产。

## 当前项目状态

- 181 条 link 已完成一轮完整 review，但仍有 39 条 pending。
- 20 条 V3 已核验 hazard 已补迁，但旧 handoff 记录其无 link，需要后续建立可靠依据而不能恢复历史 r8 错误关联。
- Requirement 层机制已建，但 75 条仍为 pending 草案，checkItems 待校准。
- 候选网站与搜索回归曾完成 20/20；V3/V4 差异验收曾完成主要检查。
- **RELEASE 当前为 REVIEW_REQUIRED**：原因是候选包与最新知识状态发生漂移，而不是 candidate 从未生成。

## 未完成事项

1. 同步 `knowledge/manifest.json` 到当前真实知识状态，并确保统计来自实际文件而非手工猜测。
2. 基于最新 HEAD 重建新的 candidate release，重新计算 sourceStateHash / counts / reviewStats。
3. 对新 candidate 重跑 Validator、Gate、V3/V4 diff、search regression，收口 RELEASE 级状态。
4. 继续处理 39 条 pending link 的补证与适用性复核。
5. 为 20 条补迁 hazard 建立新的可靠 link 并逐条 review。
6. 校准被实际 link 引用的 Requirement，补 checkItems；不得批量强行 verified。
7. 继续处理 merge 候选、composite hazard 等最终验收遗留项。

## 下一轮第一步

**先按当前真实 HEAD 重新统计 `knowledge/` 各实体目录并同步 `knowledge/manifest.json`；同时核对 `9544c49...` 之后是否又有并发提交。只有 manifest 与真实文件一致后，才能基于最新状态重建 candidate release。**

## 后续任务

按顺序：manifest 同步 → 最新 candidate 重建 → Validator/Gate/diff/search regression → RELEASE 收口 → pending link 补证 → 20 条补迁 hazard 建依据 → Requirement 校准 → 其他最终验收项。

## 法规/标准待核验队列

上一版 handoff 所列 GB 6514-2023、GB 15607-2023、GB 12801-2025 实施日期“未获官方确认”的描述已被最新提交 `9544c49...` 部分/全部更新，**下一轮不得继续按旧描述重复施工**，应以最新实体与 review 文件为准重新判断剩余未决项。

仍需最终验收关注：
- 《危险化学品安全管理条例》与 2026 新法的具体处置关系；
- GB 50140-2005 / GB 50016-2014 与新强制性工程建设规范的 partial replacement 处理；
- 工贸企业重大事故隐患判定标准新旧版本状态；
- 39 条 pending link 中涉及的专项技术标准全文/局部条款证据。

## 风险 / 阻塞

- 当前无需要用户立即决策的阻塞。
- 最大状态风险是 manifest、candidate、handoff 可能在并发施工下继续落后；所有后续轮次必须先读真实 HEAD。
- 旧 candidate 已不代表当前知识状态，禁止据此切 production。
- pending 不得为追求完成率强行改 verified。

## 用户待决策事项

当前没有必须由用户立即决定的事项。正式生产切换仍必须等待用户明确批准。

## 明确禁止事项

- 不修改 `main`。
- 不切换 production。
- 不切换 GitHub Pages 数据源。
- 不覆盖或修改 V3 冻结 SQLite。
- 不 force push / force update ref。
- 不恢复历史 r8 错误关联。
- 不因关键词相似、任务完成率或批量规则把 pending 强行改为 verified。
- 不使用旧 candidate / 旧 handoff 覆盖更新的真实成果。
