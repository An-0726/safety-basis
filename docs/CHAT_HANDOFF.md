# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。恢复项目时必须先读取本文件、`knowledge/manifest.json`、`source/releases/v4-candidate-20260910/release.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub 真实文件状态为准。

## PROJECT_STATUS

ACTIVE — V4 已进入最终验收前阶段；候选发布包当前通过既有共享链式门禁，但 production 切换仍需用户明确批准。

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

Phase 22 / 最终验收前。

已完成的主要工作包括：基础迁移、link applicability 复核归零 pending、复合 Hazard 拆分、V3 verified backfill、merge 验收、Requirement 语义校准、共享链式发布判定、V3/V4 差异报告、候选 release 构建和 backlog 大规模清理。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub

- 本轮开工时真实 HEAD：`9936756008616e427145083dc75f22eb05734a3d`
- 该提交说明：`fix: align gate_v4 CONTENT/APPLICABILITY with shared chained gate; sync manifest; rebuild candidate; 596 publishable hazards; strict PASS`
- 本轮新增：
  - `cbefe6a41cefcac76516d8f4a88b3ac9be2316e7` — 同步 `docs/V4_GATE_REPORT.md` 到最新候选包真实状态
- 本 handoff 提交位于其后；下一轮仍必须重新读取 `chat-v4` 获取真实最终 HEAD。
- main 分支保持 V3 时代状态，未修改。

### V3 冻结基线

- `source/master/safety.sqlite3`
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 全程只读，未修改。

### 当前知识规模

以 `knowledge/manifest.json` 的 counts 与最新 candidate release 为准：

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- requirements: 75
- evidence: 567
- successions: 23

### 当前 link / 发布状态

最新 `source/releases/v4-candidate-20260910/release.json`：

- Link review: 666 verified / 19 rejected / 0 pending
- publishable hazards: 596 / 712
- notPublishable hazards: 116
- eligible links: 666
- candidate: true
- production: false
- sourceStateHash: `6b0adf8953769c5aa84b017ff9b0160ea8b0baddaf1bc35f87b2864c09cee9a7`
- 当前 Gate：STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE 全部 PASS
- strict audit：PASS

### 核心基础设施

- `tools/v4/release_gate_core.py`：共享链式发布判定核心
- `build_release.py` / `strict_release_audit.py` / `gate_v4.py` 共用同一链式判定逻辑
- 公开 `search-index.json` 仅含 publishable hazard；全量实体继续保留在非公开发布链数据中

## 本轮完成

1. 重新读取 `docs/CHAT_HANDOFF.md`、`knowledge/manifest.json`、最新 `chat-v4` HEAD 与 candidate release。
2. 发现原 `docs/V4_GATE_REPORT.md` 仍停留在旧快照：CONTENT / APPLICABILITY 显示 FAIL，eligibleHazards 仅 296，与最新候选包不一致。
3. 已将 `docs/V4_GATE_REPORT.md` 同步到最新候选包：596 publishable hazards、666 eligible links、六阶段 Gate 全 PASS、production=false。
4. 确认 `knowledge/manifest.json` 的 counts 已同步到当前知识规模，但其 `scope` 文本仍残留早期 68 laws / 662 hazards / 181 links 等旧描述；不得把该 scope 当作当前真实统计。
5. Google Drive 中 `safety-basis` 工作目录仍可访问；本轮未覆盖 Drive 正式文件。

## 本轮修改文件

- `docs/V4_GATE_REPORT.md`
- `docs/CHAT_HANDOFF.md`

## 本轮校验

- 已回读 `chat-v4` 真实 HEAD。
- 已核对 `knowledge/manifest.json` counts。
- 已核对 `source/releases/v4-candidate-20260910/release.json` sourceCounts、reviewStats、reviewStatsByLink、strictGate、production 标志和 sourceStateHash。
- 已确认当前候选包 `production=false`。
- 未修改 `main`、V3 SQLite、fulltext、GitHub Pages 正式数据源和生产网站。

## 当前项目状态

V4 已具备候选发布条件并处于最终验收前。现有候选包的发布链判定为 PASS，但正式切换仍未授权。

当前主要不是继续大规模迁移，而是：

1. 做最终独立终审；
2. 清理剩余文档一致性问题；
3. 如知识树再发生变化，必须重建 candidate 并重跑完整 validator / gate / strict audit；
4. 仅在用户批准后执行 production 切换。

## 未完成事项

- `knowledge/manifest.json` 的 `scope` 文本仍是旧叙述，需要同步为当前 75 / 75 / 88 / 712 / 735 / 75 等真实规模；counts 本身已经是最新值。
- 继续独立抽查 596 条 publishable hazard 的代表性法规链、版本时效、Requirement 语义和隐私边界。
- 评估剩余非阻断库存 warning 是否需要在生产切换前进一步处理。
- 用户尚未批准 production 切换。

## 下一轮第一步

先修正 `knowledge/manifest.json` 的 `scope` 旧叙述，并再次核对当时真实 HEAD 与 candidate `sourceStateHash`；随后继续最终终审抽查，不得直接切换 production。

## 后续任务

1. 最终独立终审：抽查高风险设备、危化品、消防、电气、粉尘防爆、特种设备、江苏/南京地方依据。
2. 若终审发现知识树发生任何实质修改，重新 build candidate，并重跑 validator / gate / strict audit。
3. 扩展搜索回归和页面功能验收。
4. 用户明确批准后，才进入 production 切换。

## 风险 / 阻塞

- `manifest.scope` 仍有历史数字残留，属于文档一致性问题，不是当前发布链数据断链。
- 当前 candidate 只能代表其 `sourceStateHash` 对应的知识状态；后续任何知识修改都会使它变成旧快照。
- 生产切换属于不可逆高影响操作，必须等待用户明确批准。

## 用户待决策事项

- 是否批准最终 production 切换：当前尚未批准。

## 明确禁止事项

- 不得修改 `main`
- 不得正式切换 production
- 不得切换 GitHub Pages 正式数据源
- 不得用旧 release 覆盖当前候选或生产成果
- 不得修改 V3 冻结 SQLite
- 不得 force push
- 不得为了提高发布数量降低法规、条款、适用性或证据准确性要求
