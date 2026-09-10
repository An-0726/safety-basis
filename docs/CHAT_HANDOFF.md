# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。恢复项目必须先读取本文件，并核对 GitHub `chat-v4` 真实 HEAD、最新 Phase 16 inventory / acceptance、`knowledge/manifest.json` 与 Google Drive `ESH_Codex/work/safety-basis`。真实文件状态优先于聊天历史。分支存在并发施工，写入前重新 fetch；禁止 reset / force push。

## PROJECT_STATUS

**READY_FOR_ACCEPTANCE** — Phase 16 全部验收已完成，等待用户批准是否进入 Phase 17。

当前知识树实测：**85 laws / 85 lawVersions / 177 clauses / 712 hazards / 829 links / 590 evidence / 75 requirements / 23 successions**。
最近一次完整候选发布链验收：**640 publishable hazards / 801 eligible links / strictBlockers 0**。

完整验收结论见 **`docs/V4_FINAL_ACCEPTANCE_REPORT.md`**（A–J 全部 PASS）。
候选包已包含网站前端与数据投影，可在 `source/releases/v4-candidate-20260910/` 直接起静态服务验证；
网站投影由 `tools/v4/build_site_data.py` 生成，已接入 CI 与双构建确定性检查。

**唯一未收口项**：`H_1F19FA1B951D46C1971E9B59B4`（门窗未朝外开启）现场信息不足——
"门窗"混指门与窗、缺少场所类型与门的用途，且 GB 55037-2022 第7.1.6条只对列举场所的疏散出口门强制生效。
按 `docs/reviews/H_1F19FA1B951D46C1971E9B59B4_DATA_QUALITY_REVIEW_20260910.md` 的结论**不强行补依据**；
该隐患保留 Stable ID 与历史记录，active 但无 qualifying link，因此不在公开投影中，待原始场景确认后重新核定。

**未获用户明确批准前不得进入 Phase 17、修改 `main` 或切换生产网站。**

## 当前总目标

在保留 V3 Stable ID、法规/标准身份、版本、条款、可靠隐患、正确关联、证据、历史 release 与网站能力的前提下完成 Chat-first V4。Phase 16 全部真实验收通过后进入 `READY_FOR_ACCEPTANCE`；未经用户明确批准不得进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

Phase 16：最终验收。

## 当前工作分支

`chat-v4`

## 当前真实基线

- 本轮开始核对的 GitHub `chat-v4` HEAD：`f858eba417c8968daba4810a736d7de3bc95e344`。
- `f858eba4` 已完成一次完整候选重建和全验收：`validate_all` 6/6 PASS；643 publishable hazards；752 eligible links；六阶段 Gate 全 PASS；strictBlockers=0；search regression 20/20；双构建 diff clean；公开投影隐私扫描零命中。
- 最新 Phase 16 inventory 对当前知识树统计：79 laws / 79 lawVersions / 129 clauses / 712 hazards / 781 links；643 eligible hazards / 743 inventory eligible links；68 superseded/merged hazards；仅 1 条 active hazard 无 qualifying direct/fallback link。
- V3 冻结基线 `source/master/safety.sqlite3` 未修改；`main`、production、GitHub Pages 正式数据源均未修改。
- Google Drive 已核对 `ESH_Codex/work/safety-basis` 路径，本轮未以旧 Drive 文件覆盖 GitHub。

## 本轮完成

1. 纠正旧 handoff：实际仓库已明显超过其中记录的 78/78/111/712/761 状态，完整验收也已从 644 条推进到 643 条真实可发布隐患；旧“49 条队列”等不能再作为当前断点。
2. 定位 Phase 16 inventory 中唯一 active 且无 qualifying direct/fallback 的隐患：`H_1F19FA1B951D46C1971E9B59B4`《门窗,未朝外开启》。
3. 对该条完成数据质量复核并新增 `docs/reviews/H_1F19FA1B951D46C1971E9B59B4_DATA_QUALITY_REVIEW_20260910.md`。
4. 复核结论：当前记录把“门”和“窗”混为同一对象，缺少建筑/场所、人员、门用途及位置等适用条件；整改措施与“开启方向”问题也不对应。当前不能安全补 direct/fallback，也没有充分依据指定 mergedInto 目标。不得为了清零 inventory 强行配法规或猜合并对象。
5. 本轮没有修改该 hazard 的 lifecycle；先保留 Stable ID 和历史事实，等待按现有 V4 schema / merged precedent 确认正确退出 active 的处理方式。

## 本轮修改文件

- `docs/reviews/H_1F19FA1B951D46C1971E9B59B4_DATA_QUALITY_REVIEW_20260910.md`
- `docs/CHAT_HANDOFF.md`

## 本轮校验

- 重新核对 `chat-v4` HEAD 与 Phase 16 完整验收提交。
- 核对最新 `V4_FINAL_ACCEPTANCE_INVENTORY.md`：唯一 active/no-qualifying-basis 为 `H_1F19FA1B951D46C1971E9B59B4`。
- 核对该 hazard 源文件：title/description 均为“门窗,未朝外开启”，conditions 仍引用 GB/T 12801-2008 5.4.6，measures 为“该公司设置了安全通道,疏散指示标志等”。
- 在当前候选全集中检索“疏散门/疏散方向/开启方向/向外开启/安全出口”等，没有获得足以证明可无损合并的 canonical hazard。
- 本地只读 clone 因当前执行环境 DNS 无法解析 `github.com` 而失败；GitHub connector 持续可用，因此不构成项目阻塞。

## 当前项目状态

- Phase 16 仍为 ACTIVE，无需用户立即决策。
- 最新完整构建链本身已全绿，但知识树最终语义收口尚差最后的 active/no-basis 分类，以及 handoff 中尚未确认已完成的旧遗留事项复核。
- 当前最重要原则：最后 1 条不能靠“随便补一个依据”清零；应该让错误/残缺知识退出公开候选，而不是制造错误依据。

## 未完成事项

1. 核对现有 hazard lifecycle / merged precedent，决定 `H_1F19FA1B951D46C1971E9B59B4` 应采用 rejected / superseded / merged 中哪一种真实语义；若无可靠合并对象，优先作为历史待复核实体退出 active，而不是伪造 mergedInto。
2. 处理该状态后刷新 review/hash binding，并跑相关 Validation / Gate。
3. 重新生成 Phase 16 inventory，确认 activeHazardsWithoutQualifyingLink 是否归零。
4. 对照当前真实仓库复核旧 handoff 列出的 H058→H043、Phase8、Requirement、重复项、sourceUrl 等事项是否已被并发提交完成；只处理仍真实存在的项，禁止重复施工。
5. 知识树稳定后再跑一次最终完整 candidate、确定性构建、strict audit、搜索、页面/PWA、隐私投影和 V3/V4 diff 收口。
6. 全部真实验收通过后将状态改为 `READY_FOR_ACCEPTANCE`，等待用户批准 Phase 17。

## 下一轮第一步

**先读取一个当前已经正确 `merged` / `superseded` / `rejected` 的 hazard 及其 review/link 处理样板，并核对 V4 validator 对 hazard lifecycle 的允许值。随后对 `H_1F19FA1B951D46C1971E9B59B4` 采用语义正确的退出 active 方案；不得猜 `mergedInto`。**

## 法规/标准待核验队列

以当前真实 Phase 16 inventory、reviews 与最新提交为准，不再照抄旧 handoff 的历史队列。只有仍影响 active 发布链的条款才进入优先核验；已完成或已 superseded 的项目不得重复查。

## 风险 / 阻塞

- 当前无必须用户决策的 blocker。
- GitHub 存在并发写入可能；每次写目标文件前重新 fetch，禁止覆盖新提交。
- 机器 Gate 全绿不等于语义天然正确；r8 历史事故继续作为长期禁令。
- 对残缺 hazard 不能用宽泛上位法或旧标准线索凑 direct/fallback。
- 本地 clone 的 DNS 失败只影响本轮本地执行校验，不影响 GitHub 远端读取/写入；最终全套验收仍应在可运行项目工具链的环境中执行。

## 用户待决策事项

当前无。只有进入 Phase 17、修改 `main` 或正式切换生产网站时需要用户明确批准。

## 明确禁止事项

- 不修改 `main`。
- 不切换 production / GitHub Pages 正式数据源。
- 不覆盖 V3 SQLite 冻结基线。
- 不用旧 release / 旧报告覆盖新成果。
- 不因 Gate 全绿自动宣告法规语义全部正确。
- 不批量假定 links 正确，不重演 r8。
- 不为提高发布数量强行建立 verified 依据。
- 不把通用上位法包装成具体技术 direct。
- 不因缺少全文而编造条款。
- 不 reset / force push / 覆盖并行提交。
