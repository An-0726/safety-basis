# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（Pending 39 落定轮收尾）。恢复项目时必须先读取本文件、`knowledge/manifest.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub 真实文件为准。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

最终验收与遗留项收口阶段。本轮完成：39 条 pending link 落定、21 个复合隐患拆分任务登记、RELEASE gate 自动化收口（六级 PASS）、manifest 同步。

## 当前工作分支

`chat-v4`

## 当前真实基线（GitHub）

- 本轮最终 HEAD 由提交链决定：`17f90c2`（上一轮终态）→ `d425459`（pending39 落定）→ `9f40da7`（release 重建）→ merge `9544c49d`（GPT 标准日期核验）→ `7feb20e`（merge gate 报告修正 91ed7a78）→ merge `ebbbeb97`（GPT handoff）→ gate RELEASE 收口 commit → 本次 handoff commit。
- 施工期间检测到 3 次并发推进（GPT/Hsu Zane）：`9544c49d`（标准日期+succession）、`91ed7a78`（gate 报告修正）、`ebbbeb97`（handoff），全部已 merge 整合，无文件冲突、无 force。
- **下一轮仍须重新读取 `chat-v4` 获取最终真实 HEAD**，禁止把这里的提交号当成永远不变的最终 HEAD。

## 当前知识规模（真实文件统计，2026-09-10）

- laws：68
- lawVersions：68
- clauses：76
- requirements：75（草案，全部 pending）
- hazards：662（642 迁移 + 20 补迁）
- links：181
- evidence：552
- successions：22（19 + GPT 补 3：GB 12801-2008→2025、GB 6514、GB 15607 替代关系）

Link review（181 全审）：
- **verified：128**
- **rejected：21**
- **pending：32**
- 合计：181

`knowledge/manifest.json` 已同步上述真实计数（不再落后）。

## V3 冻结基线

V3 SQLite SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`；全程未修改 V3 SQLite（只读）。

## Candidate release

`source/releases/v4-candidate-20260910/`（candidate=true, production=false）
- `release.json` 已按当前 HEAD 重建：sourceStateHash 与当前 knowledge 一致、counts 匹配、reviewStatsByLink=128/21/32。
- **链式发布门禁已生效**：`search-index.json` 只含 **113 条 publishable hazard**（至少 1 条 eligible verified direct/fallback link + hazard 内容审查通过 + clause 审查通过，与 `strict_release_audit.py` 完全对齐）；全部 662 条 hazard 保留在 `data/hazards/` 和 `search-index-all.json` 供验收查看。
- Gate 六级：STRUCTURAL/CONTENT/APPLICABILITY/VERSION/EVIDENCE/RELEASE 全部 PASS。
- production 未切换（需用户批准）。

## 严格发布审计（Strict Release Audit）

GPT 新增 `tools/v4/strict_release_audit.py`（只读）和 `tests/test_v4_strict_release_audit.py`（CI）。
- **strictVerdict: BLOCK**（157 blockers, 1 warning）
- eligibleLinks: 126 / 181
- eligibleHazards: **113 / 662**（与 build_release 链式门禁一致）
- backfill（20 条补迁）eligible: 0 / 20（全部无 link，正确）
- Blocker 分类：hazard_content 48、pending_link_on_blocked_hazard 31、law 28、lawVersion 28、clause 22
- 主要原因：law/lawVersion/clause/hazard 的 review 缺失或 hash stale（非数据错误，是审查覆盖尚未完成）
- 详细报告：`docs/V4_STRICT_AUDIT.md`
- 最终 production 切换前必须消除所有 blocker 或经专业验收确认可豁免。

## 本轮完成

1. **39 条 pending link 落定**：1 verified（K_13863d87 灭火器筒体，V3 核验记录交叉确认）、6 rejected（4 条 FACT_NOT_HAZARD 法规义务复述、2 条 SCOPE_MISMATCH 挂错条款）、32 条保持 pending 但理由补强（GB 2894-2025 官方解读核验、TSG 81-2022 指向）。
2. **21 个复合隐患拆分任务登记**：`docs/V4_HAZARD_SPLIT_TASKS.md`（Hazard ID / 混合义务 / 相关 Link / 拆分建议）。
3. **RELEASE gate 自动化收口**：`gate_v4.py` 新增 RELEASE 级一致性核对（sourceStateHash/counts/reviewStats vs candidate），输出 PASS 而非 NOT_RUN。
4. **manifest 同步**：`sync_manifest.py` 从真实文件统计更新 counts（68/68/76/662/181/552/22/75）。
5. 合并 GPT 并发：标准日期核验（GB 6514-2023、GB 15607-2023、GB 12801-2025 实施日期确认 + 6514/12801 名称与状态纠正 + 3 条 succession）、gate 报告修正、handoff 更新。

## 本轮修改文件

- `knowledge/reviews/links/*.json`（41 条：7 决策 + 2 补强 + 32 复合登记）
- `knowledge/hazards/*.json`（4 条 FACT_NOT_HAZARD note 标记）
- `knowledge/manifest.json`（同步）
- `knowledge/law-versions/laws/successions`（GPT 9544c49d 的 9 个文件，已 merge）
- `tools/v4/apply_pending39.py`、`extract_pending39.py`、`sync_manifest.py`、`build_release.py`（双级 reviewStats）、`gate_v4.py`（RELEASE 检查）
- `docs/V4_HAZARD_SPLIT_TASKS.md`（新）、`docs/V4_GATE_REPORT.md`、`docs/CHAT_HANDOFF.md`
- `source/releases/v4-candidate-20260910/`（重建）
- `tools/workbooks/pending_39_workbook.json`（新）

未修改 V3 SQLite、`main`、production、GitHub Pages 数据源。

## 本轮校验

- `validate_all.py`：check_catalogue / check_requirements / check_review_binding（unbound 0、stale 0）/ scan_evidence_exact / scan_quality / version_impact 全 PASS。
- `gate_v4.py`：六级全 PASS（RELEASE 经一致性核对）。
- `test_search.py`：20/20 通过。
- `version_impact.py`：full-replaced 迁移 0、partial 7（不迁移）。

## 当前项目状态

- 181 条 link 已全部有明确状态（128 verified / 21 rejected / 32 pending）。
- 32 条 pending 全部有扎实理由，其中 21 个复合隐患已登记拆分任务（`docs/V4_HAZARD_SPLIT_TASKS.md`），拆分后再判定 link 角色。
- 20 条 V3 补迁 hazard 仍无 link（刻意不迁移 V3 旧关联），需建立可靠新 link。
- Requirement 层 75 条仍为 pending 草案，checkItems 待校准。
- 候选网站与搜索回归 20/20；V3/V4 差异验收完成主要检查。
- Gate 六级 PASS；production 切换需用户批准。

## 未完成事项（最终验收范围）

1. 32 条 pending link 的补证与复合 hazard 拆分（21 个任务在 `docs/V4_HAZARD_SPLIT_TASKS.md`）。
2. 20 条补迁 hazard 建立新 link 并逐条 review。
3. Requirement 层：被 link 引用的 clause 对应 RQ 校准 verified + checkItems；不得批量强行 verified。
4. 45 组 merge 候选语义判定（`docs/V4_MERGE_CANDIDATES.md`）。
5. 工贸企业重大事故隐患判定标准（应急部令第 10 号 vs 2025 新令）状态核验入库。
6. GB 50140-2005 / GB 50016-2014 与 GB 55036/55037-2022 partial replacement 复核。
7. 危化品条例处置关系：GPT 已独立核验 partially_replaces 正确（司法部国家行政法规库仍列现行有效），建议最终验收复核留存。

## 法规/标准待核验队列

- GB 6514-2023 / GB 15607-2023 / GB 12801-2025 实施日期：**已由 GPT 9544c49d 核验补全**，不得再按旧描述重复施工。
- 工贸企业重大事故隐患判定标准新旧版本状态：未核验、未入库。
- 32 条 pending 涉及的专项技术标准全文/局部条款证据（见各 review reason）。

## 风险 / 阻塞

- 无需要用户立即决策的硬阻塞。
- 并发施工活跃：每次写入前必须 `git ls-remote origin chat-v4` 重读真实 HEAD；只允许 non-force fast-forward。
- candidate 与 handoff 可能在并发下继续落后；所有后续轮次先读真实 HEAD。
- pending 不得为追求完成率强行改 verified。

## 用户待决策事项

生产切换（Phase 17）仍等待用户明确批准；当前不授权修改 `main`、GitHub Pages 数据源或 production selection。

## 明确禁止事项

- 不修改 `main`。
- 不切换 production。
- 不切换 GitHub Pages 数据源。
- 不覆盖或修改 V3 冻结 SQLite。
- 不 force push / force update ref。
- 不恢复历史 r8 错误关联。
- 不因关键词相似、任务完成率或批量规则把 pending 强行改为 verified。
- 不使用旧 candidate / 旧 handoff 覆盖更新的真实成果。
