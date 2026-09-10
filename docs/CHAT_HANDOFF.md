# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（V4 backlog 大规模清理完成：publishable hazards 从 162 提升至 565/712，inventoryWarnings 从 486 降至 92，strict audit PASS / releaseBlockers=0 / Gate 六阶段全 PASS / pending links=0）。恢复项目时必须先读取本文件、`knowledge/manifest.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub 真实文件状态为准。

## PROJECT_STATUS

ACTIVE — 已达到可提交最终验收状态，等待独立审查方（ChatGPT）终审和用户生产切换决策。

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

Phase 22 / 最终验收前。基础迁移、link applicability 复核（179→0 pending）、复合 Hazard 拆分（21→50 子 hazard）、V3 verified backfill（20/20）、merge 验收（45/45）、严格发布审计主链（三脚本共用 release_gate_core）、Requirement 语义校准（44 发布链 verified）、backlog 大规模清理（468 无 link hazard → 剩余 24 个设计规范类）均已完成。V3/V4 差异验收报告已生成（docs/V3_V4_DIFF_REPORT.md）。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub

- 最近已知 HEAD：`2d96e0d6faf32c5caf2c248a05fc2002536d7be1`（必须重新 `git ls-remote origin chat-v4` 确认真实 HEAD）
- main 分支：`11a98ca3fa379a9e8a92549ba94dcc074297be1f`（V3 时代，未修改）
- 本轮关键 commits：
  - `3046d1d` — link-backfill: 37 new verified links
  - `bd9de4c` — docs: add V3/V4 diff report; rebuild candidate (543 publishable)
  - `1a84034` — link-backfill: 27 new verified links (562 publishable)
  - `2d96e0d` — link-backfill: 3 new verified links (565 publishable)
- 下一轮仍必须重新读取 `chat-v4` 获取真实最终 HEAD，禁止把本文记录的 SHA 当作永远不变的分支状态。

### V3 冻结基线

- `source/master/safety.sqlite3`，SHA-256 `7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`（全程只读，未修改）

### 当前数据规模（以真实 knowledge/ 为准）

- laws: 75 / lawVersions: 75 / clauses: 88 / hazards: 712 / links: 705 / requirements: 75 / evidence: 567+ / successions: 23
- Link review: 632 verified / 23 rejected / 0 pending（全库 pending 归零）
- publishable hazards: 565 / 712（79.4%）
- eligible links: 632 / 705
- strict audit: PASS，releaseBlockers=0，inventoryWarnings=92，excludedEntities=108
- 普通 Gate 六阶段：全 PASS（STRUCTURAL/CONTENT/APPLICABILITY/VERSION/EVIDENCE/RELEASE）
- 搜索回归：20/20 PASS
- candidate sourceStateHash: `899015a98a78b794`

### 核心基础设施

- `tools/v4/release_gate_core.py`（336 行）：三脚本共用的链式发布判定核心
- `build_release.py` / `strict_release_audit.py` / `gate_v4.py` 全部 `from release_gate_core import evaluate_release_gate`
- 公开 search-index.json 只含 publishable hazard，全量保留在 search-index-all.json

### 剩余 inventoryWarnings（92 个，不阻塞 production）

- 约 24 个厂址/总平面设计规范类 hazard（GB50187 等）：属设计阶段要求，非现场可检查隐患，不强行建 link
- 其余为 supporting-only link 和非发布链库存 backlog
- 这些是后续知识库建设遗留项，不影响当前发布安全性

### 约束遵守确认

- main 未修改 ✅
- production 未切换 ✅
- GitHub Pages 正式数据源未切换 ✅
- V3 SQLite 未修改（哈希匹配）✅
- 无 force push ✅
- PR #7 未 merge ✅
- 停在 chat-v4 ✅

## 下一步

1. 交付独立审查方（ChatGPT）做最终终审
2. 如终审通过，等待用户明确批准后执行 Phase 17 production 切换
3. 后续可继续处理 92 个 inventoryWarnings（设计规范类 hazard 评估是否保留/合并/删除）
4. 可继续扩展搜索回归测试覆盖（当前 20/20）
