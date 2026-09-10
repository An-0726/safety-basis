# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目时必须先读取本文件、`docs/V4_FINAL_ACCEPTANCE.md`、`docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`、`knowledge/manifest.json`，并重新核对 `chat-v4` 真实 HEAD、最新 V4 Final Acceptance CI 和 Google Drive `ESH_Codex/work/safety-basis`。聊天历史不得覆盖真实文件状态。

## PROJECT_STATUS

ACTIVE — Phase 16 最终验收继续执行。机器链式 Gate 已修复并全绿，但法规适用性人工专业终审、20 条 pending Requirement、旧标准/替代关系队列、V3/V4 最终差异、页面/PWA/隐私终审尚未收口，因此不得标记 READY_FOR_ACCEPTANCE。

## 当前总目标

在保留 V3 Stable ID、法规身份/版本/条款、可靠隐患、正确关联、证据、历史 release 和网站能力的基础上完成 Chat-first V4。全部 Phase 16 验收通过后才改为 `READY_FOR_ACCEPTANCE`；只有用户明确批准才进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

**Phase 16：最终验收。**

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub / Knowledge

本轮开工时真实 HEAD：`1a96095c2e8bea21adbcc1dc684c2bfde161bab7`。

本轮有效代码修复提交：

`0a7673149c012cf39238e019c05626ef11e8c285` — `fix: index V4 reviews by entity id`

随后更新终审库存文档：

`49ba9101e9682d4d50335b639fcad8358693bc3d` — `docs: correct Phase 16 inventory after review-index fix`

本文件提交后 HEAD 会再次前移；下一轮必须重新读取分支真实 HEAD，不得仅依赖此处记录。

当前 knowledge counts 未改动：

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- requirements: 75
- evidence: 567
- successions: 23

本轮**没有修改任何 `knowledge/**/*.json`**，所以 candidate `sourceStateHash` 仍为：

`545a828e653fe634754d50699c7e321448dbac25396500b15c1a015f1a0e0e5f`

### V3 冻结基线

- `source/master/safety.sqlite3`
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 本轮未修改 SQLite / fulltext。

### Google Drive

`ESH_Codex/work/safety-basis` 本轮已确认仍可访问，根目录包含 `.git`、`data/`、`docs/`、`source/`、`tools/`、网站源码等工作资产。本轮没有覆盖 Drive 正式文件。

### 最新机器 Candidate / CI

commit `0a767314...` 对应 V4 Final Acceptance：

- run id: `34456894682`
- conclusion: SUCCESS
- artifact id: `10143845362`
- artifact name: `v4-final-acceptance-0a7673149c012cf39238e019c05626ef11e8c285`
- candidate: true
- production: false
- eligible hazards: **645**
- eligible links: **716**
- active hazards without qualifying direct/fallback: **0**
- superseded/merged hazards: 67
- link reviews: 716 verified / 19 rejected
- strict release blockers: 0
- search regression: PASS
- deterministic build: PASS
- knowledge mutation check: PASS

## 本轮完成

1. 恢复并核对 GitHub、Google Drive 和上一轮 Phase 16 状态，确认未有并发新提交覆盖本轮开工基线。
2. 复核 H043 后发现：hazard、link、clause、lawVersion、law 均已有有效 review，但旧 inventory 仍把 H043 判成“无 qualifying link”。
3. 定位根因到 `tools/v4/release_gate_core.py`：普通实体和 review sidecar 共用 `load_dir()`，而新式 review 同时带有自身 `id=RV_*` 和被审核实体 `entityId`。旧逻辑优先使用 review 自身 `id` 建索引，发布 Gate 后续却按实体 ID 查 review，导致新式 review 被系统性误判为缺失。
4. 实施最小修复：普通实体仍按自身 `id`；新增 `load_reviews()` 专门按 `entityId` 建索引，无 `entityId` 的旧 sidecar 才以文件名兜底。未修改法规、隐患、关联或 review 内容本身。
5. 修复后重新跑 V4 Final Acceptance，全套机器验收通过；真实库存由旧的 `596 hazards / 666 links / 49 active missing` 修正为 `645 hazards / 716 links / 0 active missing`。
6. 更新 `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`，明确旧“49 条缺依据”是读取逻辑造成的假缺口，不再把这 49 条作为后续逐条补链任务。
7. 明确新的终审边界：机器 Gate 全绿只证明结构和既定规则链完整，**不代表 716 条法规关联的专业语义全部正确**；仍须继续人工审查过泛 fallback、地方频次义务、旧标准和替代关系。

## 本轮修改文件

- `tools/v4/release_gate_core.py`
- `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`
- `docs/CHAT_HANDOFF.md`

## 本轮校验

V4 Final Acceptance run `34456894682`：

- integrated validator: PASS
- candidate build: PASS
- Gate STRUCTURAL: PASS
- Gate CONTENT: PASS
- Gate APPLICABILITY: PASS
- Gate VERSION: PASS
- Gate EVIDENCE: PASS
- Gate RELEASE: PASS
- strict audit: PASS
- release blockers: 0
- search regression: PASS
- candidate boundary (`candidate=true`, `production=false`): PASS
- deterministic double-build: PASS
- acceptance tools modified knowledge: NO
- artifact successfully generated

关键修复效果：

- eligible hazards: 596 → **645**
- eligible links: 666 → **716**
- active hazards without qualifying direct/fallback: 49 → **0**

这 49 条并不是本轮批量“通过”或新增依据，而是其既有 verified review 被旧 Gate 以错误键读取，修复索引后恢复到正确链式状态。

## 当前项目状态

### 发布链

- total hazards: 712
- active / machine-eligible hazards: 645
- superseded/merged hazards: 67
- eligible links: 716
- link reviews: 716 verified / 19 rejected
- active hazards without qualifying direct/fallback: 0
- supporting verified links: 11
- candidate=true / production=false

### Requirement

- verified: 55
- pending: 20

### 仍需人工语义终审的队列

机器链完整后，后续重点不再是“给 49 条补 link”，而是审核已有 link 是否真的足够直接、适用和现行：

- pending Requirements: 20
- stale old-standard refs in hazard fields: 14
- partial-replaced standard hazard hits: 12
- obligation-restatement candidates: 11
- links to merged hazards: 9
- H046 江苏主要负责人“每季度至少一次全面检查”：现有全国法只能作为泛化兜底，必须核江苏现行地方直接条款
- H048 江苏主要负责人“每年至少一次全面风险辨识”：必须核地方具体频次义务，不能仅以全国风险分级管控制度代替
- H049 事故发生后组织抢救、及时如实报告：必须核精确直接法条，不能由“制定应急预案”义务替代
- H043 仓储消防培训：继续确认消防专项直接依据是否优于现有通用安全生产教育培训条款
- H052-H055、H058、H065、H067、H069、H079 等高价值条目继续做现行版本、条款原文和适用范围终审

## 未完成事项

1. 对上述高价值 link 做专业适用性终审，必要时把过泛的 direct 降为 fallback/supporting 或补更直接依据；不得因为当前 eligible=645 就自动保留所有 link 角色。
2. 完成 20 条 pending Requirement 的逐条语义校准。
3. 终审 14 条旧标准引用候选和 12 条 partial-replaced hit，确认当前版本及替代关系。
4. 处理 11 条 obligation-restatement candidates。
5. 处理 9 条 links-to-merged-hazard candidates。
6. 刷新最终 `docs/V3_V4_DIFF_REPORT.md`。
7. 执行候选网站页面、筛选、law index、PWA/Service Worker、隐私公开投影验收。
8. 知识树最终稳定后生成新的完整 final candidate 路径并整体提交，再跑全套最终验收。
9. 只有全部 Phase 16 收口后才改 `READY_FOR_ACCEPTANCE`。

## 下一轮第一步

**不要再按旧 inventory 的 49 条“缺依据”逐条补链。**

先对第一组高风险/高价值既有 link 做法规语义终审：`H046`、`H048`、`H049`、`H043`。逐条读取 hazard → 当前 link/review → clause/lawVersion → 联网核当前官方法规原文和效力 → 判断现有 role 是否合理。重点先解决江苏地方频次条款和 H049 精确事故报告/抢救义务；找到直接条款则规范入库，证据不足则维持现状或降级，禁止为了覆盖率强行 verified。

完成这一小批后重新跑 V4 Final Acceptance，并更新 inventory/handoff。

## 后续任务

1. H046 / H048 / H049 / H043 专业终审。
2. H052-H055、H058、H065、H067、H069、H079 终审。
3. 20 条 pending Requirement。
4. 14 条旧标准 + 12 条 partial replacement。
5. 11 条 obligation-restatement + 9 条 merged-link。
6. 最终 V3/V4 diff。
7. 页面/PWA/隐私验收。
8. final candidate + 全套 validator/gate/strict/deterministic build。
9. 最终验收报告 → `READY_FOR_ACCEPTANCE`。
10. 用户批准后才进入 Phase 17。

## 法规/标准待核验队列

高优先级：

- 江苏省安全生产现行地方法规：主要负责人季度全面检查、年度全面安全风险辨识的具体条款和现行效力。
- 《中华人民共和国安全生产法》中事故后单位负责人组织抢救、及时如实报告的精确条款。
- 仓储消防培训、在岗培训频次、消防重点岗位培训的直接消防专项依据。
- 仓储堆垛距离现行标准版本及条款。
- 易燃气体与助燃气体同库储存的直接技术依据。
- 建设项目安全设施设计“三同时”直接依据。
- 2026《中华人民共和国危险化学品安全法》与既有危险化学品行政法规/规章的现行并存和替代边界。
- 14 条旧标准引用候选、12 条 partial-replaced hits。

## 风险 / 阻塞

当前没有必须用户决策才能继续 Phase 16 的 blocker。

已知风险：

- 旧 Phase 16 inventory 的 49 条 active missing 是 Gate review 索引 bug 导致的错误统计，已修正；任何旧报告若仍出现 596/666/49，应视为过期统计。
- 当前 645/716 是**机器发布链结果**，不能等同于人工法规专业终审结论。部分新增 link 的 role 仍可能偏泛，下一轮必须从 H046/H048/H049/H043 开始人工复核。
- `docs/V4_GATE_REPORT.md` 过去曾被并发流程污染；使用统计时优先核最新 CI artifact，不以旧 tracked 报告冒充实时结果。
- 容器直连 GitHub 偶发 DNS 失败，但 GitHub 连接器读写正常，不构成当前项目阻塞。

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
