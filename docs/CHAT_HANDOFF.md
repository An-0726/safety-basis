# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目时必须先读取本文件、`docs/V4_FINAL_ACCEPTANCE.md`、`docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`、`knowledge/manifest.json`，并重新核对 `chat-v4` 真实 HEAD、最新 V4 Final Acceptance CI 和 Google Drive `ESH_Codex/work/safety-basis`。聊天历史不得覆盖真实文件状态。

## PROJECT_STATUS

ACTIVE — Phase 16 最终验收继续执行。H043 仓储消防培训已完成专项依据终审并通过机器验收，但仍有法规适用性人工专业终审、20 条 pending Requirement、旧标准/替代关系、V3/V4 最终差异、页面/PWA/隐私验收未收口，因此不得标记 READY_FOR_ACCEPTANCE。

## 当前总目标

在保留 V3 Stable ID、法规身份/版本/条款、可靠隐患、正确关联、证据、历史 release 和网站能力的基础上完成 Chat-first V4。全部 Phase 16 验收通过后才可改为 `READY_FOR_ACCEPTANCE`；只有用户明确批准才进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

**Phase 16：最终验收。**

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub / Knowledge

本轮开工真实 HEAD：`bd15dce910b5c5b555d07c3f944b112d8d661859`。

H043 知识修订完成后实际分支提交：`4ce976a2f47908cdeadf970c99757dfea04254d2` — `fix: bind H043 fallback to Safety Production Law evidence`。

随后终审库存文档提交：`38f644b5ec34c7da45dc2e2b058e7c707b70691f` — `docs: refresh final acceptance inventory after H043 review`。

本文件提交后 HEAD 会再次前移；下一轮必须重新读取真实分支 HEAD。

最新成功候选构建的真实 source counts：

- laws: 76
- lawVersions: 76
- clauses: 92
- hazards: 712
- links: 739
- requirements: 75
- successions: 23

注意：`knowledge/manifest.json` 仍保留旧计数 75 / 75 / 88 / 712 / 735 / evidence 567。本轮已确认 H043 开工前的成功候选实际已经有 91 clauses / 738 links，因此 manifest 至少在 clauses、links 上早已滞后。由于本轮未独立取得 evidence 目录精确总数，没有用猜测数字覆盖 manifest；后续单独精确对账。

最新成功 candidate `sourceStateHash`：

`8b9db3b22f6d07c01cd734286a6d37d8d4c453e355362b9f2eef26606f33a228`

### V3 冻结基线

- `source/master/safety.sqlite3`
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 本轮未修改 SQLite / fulltext。

### Google Drive

本轮 Google Drive 连接可调用，但根目录枚举未返回可用子项；这不能据此认定 `ESH_Codex/work/safety-basis` 不存在或文件丢失。本轮未覆盖任何 Drive 正式文件，下一轮恢复时应重新检查。

### 最新机器 Candidate / CI

H043 修正后的 V4 Final Acceptance：

- run id: `34463598243`
- conclusion: SUCCESS
- artifact id: `10146561825`
- artifact name: `v4-final-acceptance-cbde3621b7a3c2e67b0a855232f5cf9fe0c92af7`
- candidate: true
- production: false
- sourceStateHash: `8b9db3b22f6d07c01cd734286a6d37d8d4c453e355362b9f2eef26606f33a228`
- eligible hazards: **645**
- eligible links: **719**
- active hazards without qualifying direct/fallback: **0**
- link reviews: **719 verified / 20 rejected**
- supporting verified links: **11**
- strict release blockers: **0**

## 本轮完成

1. 按真实 `chat-v4` HEAD 和上一轮交接恢复现场，确认 Phase 16 继续执行。
2. 完成 H043 `仓储场所未按要求开展消防安全教育培训` 专业终审。
3. 官方核验确认 `XF 1131-2014《仓储场所消防安全管理通则》` 当前仍为现行；应急管理部 2020 年第 5 号公告只将原 `GA 1131-2014` 重新编号为 `XF 1131-2014`，顺序号、年代号和内容保持不变。未发现可证实的 `XF 1131-2025` 替代版本。
4. 恢复 V3 Stable ID：`LF_L015` / `L015` / `C042`，没有另造新编号。
5. 修正 C042 历史条款定位错误：由旧 `第4.1` 修正为 `3.3.2`。该条直接要求仓储员工上岗、转岗前消防安全培训，在岗人员至少每半年一次消防安全教育。
6. 新增 H043 → C042 专项 `direct` 关联。
7. 原 H043 →《中华人民共和国安全生产法》第二十八条关联保留，但从 `direct` 降为 `fallback`；理由是其仅为一般性从业人员安全生产教育培训义务，不能替代仓储消防场景和半年频次专项要求。
8. 同步更新 H043 标题、描述、适用条件、整改措施和说明；新增/更新 law、lawVersion、clause、hazard、link 的 review 与证据绑定。
9. 第一次 CI 失败仅发生在 `scan_evidence_exact`：安全生产法 fallback review 误绑定了仓储消防佐证来源。已改绑至库内现有的全国人大官方《安全生产法》证据记录。
10. 修正后 V4 Final Acceptance 全绿。
11. 更新 `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`，纠正真实源码和发布链统计，并明确 manifest 计数滞后问题。

## 本轮修改文件

核心知识：

- `knowledge/laws/LF_L015.json`
- `knowledge/law-versions/L015.json`
- `knowledge/clauses/C042.json`
- `knowledge/hazards/H043.json`
- `knowledge/links/K_8a321f06af023ba4fba73c3d.json`
- `knowledge/links/K_f1313b10272b1d1f3f163c64.json`
- `knowledge/evidence/E_9faac5a2516a7f857dfe2163d017511ee692d43abca9b21d420b5c672c82ba1a.json`
- `knowledge/evidence/E_6f17cf85f91a6367a25cd532e5cf0d58b05e9e43bd728cf2427f2c5a86bc5449.json`
- `knowledge/evidence/E_277d781095b57f83d39eecb7283118ff69fde1134fcdd09aed6b95ca479f6d2c.json`
- `knowledge/evidence/E_0c7688d70354bebaf603be58527f588c17f9354236d13884e1be44b74afab707.json`
- `knowledge/reviews/laws/LF_L015.json`
- `knowledge/reviews/law-versions/L015.json`
- `knowledge/reviews/clauses/C042.json`
- `knowledge/reviews/hazards/H043.json`
- `knowledge/reviews/links/K_8a321f06af023ba4fba73c3d.json`
- `knowledge/reviews/links/K_f1313b10272b1d1f3f163c64.json`

文档：

- `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`
- `docs/CHAT_HANDOFF.md`

## 本轮校验

第一次 H043 修改后的 CI：结构校验、候选构建和法规链式适用性均通过；唯一失败为证据精确来源映射。

修正证据映射后的 V4 Final Acceptance run `34463598243`：

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

真实候选构建统计：76 laws / 76 lawVersions / 92 clauses / 712 hazards / 739 links；发布链 645 hazards / 719 links；active missing basis = 0。

## 当前项目状态

### 发布链

- total hazards: 712
- active / machine-eligible hazards: 645
- eligible links: 719
- link reviews: 719 verified / 20 rejected
- active hazards without qualifying direct/fallback: 0
- supporting verified links: 11
- candidate=true / production=false

### Requirement

- verified: 55
- pending: 20

### 已完成高价值终审

- H043：专项 `XF 1131-2014 3.3.2` direct + 《安全生产法》第二十八条 fallback 已收口。
- H048：上一轮已确认全国法只能作为 fallback；地方具体年度频次义务仍需按后续队列核验。

## 未完成事项

1. H049 事故发生后组织抢救、及时如实报告的精确直接法条终审。
2. H046/H048 江苏地方具体季度/年度频次条款继续核验，不能用泛化全国法冒充具体频次依据。
3. H052-H055、H058、H065、H067、H069、H079 等高价值 link 做现行版本、条款原文和适用范围终审。
4. 完成 20 条 pending Requirement 逐条语义校准。
5. 终审 14 条旧标准引用候选和 12 条 partial-replaced hit。
6. 处理 11 条 obligation-restatement candidates。
7. 处理 9 条 links-to-merged-hazard candidates。
8. 精确对账并修正 `knowledge/manifest.json`，尤其 evidence 总数，禁止猜数。
9. 刷新最终 `docs/V3_V4_DIFF_REPORT.md`。
10. 执行候选网站页面、筛选、law index、PWA/Service Worker、隐私公开投影验收。
11. 知识树最终稳定后生成完整 final candidate 并跑最终全套验收。
12. 全部 Phase 16 收口后才改 `READY_FOR_ACCEPTANCE`。

## 下一轮第一步

**优先完成 H049 专业终审。**

读取 H049 hazard → 当前 links/reviews → clauses/lawVersions；联网核验事故发生后生产经营单位负责人“立即组织抢救”和“及时如实报告”的现行精确直接法条及适用边界。若库中现有关联只是“制定应急预案”等相邻义务，应降级或替换；找到直接条款后按 Stable ID、证据等级和 review/hash 规则规范入库，再跑 V4 Final Acceptance。

如果 H049 在恢复现场时已被其他并发提交完成，则先按真实 HEAD 复核，再转到 H046/H048 地方具体频次义务。

## 后续任务

1. H049 专业终审。
2. H046/H048 江苏地方频次条款。
3. H052-H055、H058、H065、H067、H069、H079 终审。
4. 20 条 pending Requirement。
5. 14 条旧标准 + 12 条 partial replacement。
6. 11 条 obligation-restatement + 9 条 merged-link。
7. manifest 精确对账。
8. 最终 V3/V4 diff。
9. 页面/PWA/隐私验收。
10. final candidate + 全套 validator/gate/strict/deterministic build。
11. 最终验收报告 → `READY_FOR_ACCEPTANCE`。
12. 用户批准后才进入 Phase 17。

## 法规/标准待核验队列

高优先级：

- 《中华人民共和国安全生产法》中事故发生后单位负责人组织抢救、及时如实报告的精确条款。
- 江苏省安全生产现行地方法规：主要负责人季度全面检查、年度全面安全风险辨识的具体条款和现行效力。
- 仓储堆垛距离现行标准版本及条款。
- 易燃气体与助燃气体同库储存的直接技术依据。
- 建设项目安全设施设计“三同时”直接依据。
- 2026《中华人民共和国危险化学品安全法》与既有危险化学品行政法规/规章的现行并存和替代边界。
- 14 条旧标准引用候选、12 条 partial-replaced hits。

已从待核队列移除：H043 仓储消防培训，已于 2026-09-10 完成 `XF 1131-2014 3.3.2` 专项直接依据终审。

## 风险 / 阻塞

当前没有必须用户决策才能继续 Phase 16 的 blocker。

已知风险：

- `knowledge/manifest.json` 计数已滞后；当前真实实体数量以最新成功候选构建为准。evidence 精确总数尚需独立对账，禁止凭“旧 567 + 本轮新增”直接推算，因为此前并发轮次也可能改动 evidence。
- 当前 645/719 是机器发布链结果，不能等同于全部法规专业终审完成。
- Google Drive 本轮目录枚举未返回内容，属于连接/枚举限制，不能据此判断 Drive 文件丢失。
- `docs/V4_GATE_REPORT.md` 历史上可能被并发流程污染；使用实时统计优先核最新成功 CI 产物。

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
