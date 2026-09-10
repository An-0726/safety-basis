# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目时必须先读取本文件、`docs/V4_FINAL_ACCEPTANCE.md`、`docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`、`knowledge/manifest.json`，并重新核对 `chat-v4` 真实 HEAD、最新 V4 Final Acceptance CI 和 Google Drive `ESH_Codex/work/safety-basis`。聊天历史不得覆盖真实文件状态。

## PROJECT_STATUS

ACTIVE — Phase 16 最终验收继续执行。H043、H049 已完成当前轮次专业终审，但仍有地方频次义务、高价值关联、20 条 pending Requirement、旧标准/替代关系、manifest 精确对账、V3/V4 最终差异及页面/PWA/隐私验收未收口，因此不得标记 READY_FOR_ACCEPTANCE。

## 当前总目标

在保留 V3 Stable ID、法规身份/版本/条款、可靠隐患、正确关联、证据、历史 release 和网站能力的基础上完成 Chat-first V4。全部 Phase 16 验收通过后才可改为 `READY_FOR_ACCEPTANCE`；只有用户明确批准才进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

**Phase 16：最终验收。**

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub / Knowledge

本轮恢复时发现上一版 handoff 已落后于真实仓库。真实 `chat-v4` 开工 HEAD 为：

`5417512a27c4fbbdae00a2ae69916e90a458a4fb` — `fix: replace H043 secondary evidence with official XF 1131 source`

H049 终审记录提交：

`17fcc663b80cc9f1c533057f9230333fc322be9a` — `docs: record H049 final legal review`

本文件提交后 HEAD 会再次前移；下一轮必须重新读取分支真实 HEAD，不得把上述 SHA 当作未来固定 HEAD。

当前最近一次已确认成功候选构建统计：

- laws: 76
- lawVersions: 76
- clauses: 92
- hazards: 712
- links: 739
- requirements: 75
- successions: 23
- eligible hazards: 645
- eligible links: 719
- active hazards without qualifying direct/fallback: 0
- strict release blockers: 0

`knowledge/manifest.json` 仍为旧计数，尤其 laws/lawVersions/clauses/links/evidence 需要单独精确对账；禁止根据“旧总数 + 近期新增”猜测 evidence 总数。

### V3 冻结基线

- `source/master/safety.sqlite3`
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 本轮未修改 V3 SQLite / fulltext。

### Google Drive

本轮通过 Google Drive 搜索已重新确认存在 `safety-basis` 项目/工作目录相关结果，说明之前“根目录枚举未返回内容”不代表项目不存在。本轮未发现需要用 Drive 文件覆盖当前 `chat-v4` 的证据，也未覆盖任何 Drive 正式文件。后续涉及数据库、私有报告或大型产物时仍需重新核对 `ESH_Codex/work/safety-basis` 的具体文件版本。

### 最近一次已确认成功 Candidate / CI

H043 修正后的 V4 Final Acceptance：

- run id: `34463598243`
- conclusion: SUCCESS
- artifact id: `10146561825`
- candidate: true
- production: false
- eligible hazards: 645
- eligible links: 719
- active hazards without qualifying direct/fallback: 0
- strict release blockers: 0

本轮仅新增 H049 终审文档并更新 handoff，未修改结构化知识实体；提交后仍应检查最新 CI 状态，但不得把文档提交触发与否误写成结构化数据验收。

## 本轮完成

1. 按真实 GitHub/Google Drive 状态恢复现场，确认 Phase 16 和 `chat-v4` 未变。
2. 发现 `docs/CHAT_HANDOFF.md` 记录的 HEAD 已落后；以实际仓库 `5417512a...` 为准继续，避免重复执行 H043。
3. 复核 H049 当前结构化数据和历史提交，确认此前已完成：
   - 建立《中华人民共和国安全生产法》（2021年修正）第八十三条；
   - 建立 H049 → 第八十三条精确直接关联；
   - 完成第八十三条条款原文和 H049 适用性审核；
   - 对历史误配的第八十一条关联作 rejected 处理。
4. 重新联网核验现行政府公开正文，确认第八十三条直接规定生产经营单位负责人接到事故报告后迅速组织抢救，并按国家有关规定立即如实报告，与 H049 的主体、事故阶段和义务内容一致。
5. 同时复核《生产安全事故报告和调查处理条例》（国务院令第493号）第九条、第十四条。两条具有补充相关性，但当前 H049 未写入“1小时内报告”等更具体事实，第八十三条已完整覆盖当前隐患，因此不为了增加依据数量重复建立关联。
6. 新增 `docs/reviews/H049_FINAL_REVIEW_20260910.md`，固化 H049 专业终审结论、版本判断、适用边界、补充法规比较和数据处理决定。
7. 识别出 `knowledge/hazards/H049.json` 仍留有“尚未完成逐条官方原文终审”的过期交接文字。由于 hazard 已进入 review 内容绑定链，在未确认项目现成 review/hash 刷新机制前，本轮未直接手改结构化 hazard，避免破坏既有机器审核绑定。
8. 未新增重复 law/clause/link，未重分 Stable ID，未修改 V3 数据库，未修改 `main`，未切换生产网站。

## 本轮修改文件

- `docs/reviews/H049_FINAL_REVIEW_20260910.md`
- `docs/CHAT_HANDOFF.md`

## 本轮校验

- GitHub 真实分支恢复：PASS；开工 HEAD 已核为 `5417512a27c4fbbdae00a2ae69916e90a458a4fb`。
- Google Drive 项目存在性复核：PASS；可搜索到 `safety-basis` 相关项目/目录结果。
- H049 数据链复核：PASS；现有第八十三条 clause、direct link、verified applicability 均已存在，没有重复创建。
- H049 法规版本/条款语义人工终审：PASS。
- 第八十一条误配判断：保持 rejected，PASS。
- 国务院第493号令补充适用性：已核对，不新增冗余依据。
- 结构化知识数据：本轮未改，因此未产生新的内容绑定变化。
- `main` / production：未修改。

## 当前项目状态

### 发布链

- total hazards: 712
- active / machine-eligible hazards: 645
- eligible links: 719
- link reviews: 719 verified / 20 rejected（最近一次成功候选）
- active hazards without qualifying direct/fallback: 0
- candidate=true / production=false

### Requirement

- verified: 55
- pending: 20

### 已完成高价值终审

- H043：`XF 1131-2014 3.3.2` 专项直接依据 + 《安全生产法》第二十八条上位法兜底，已收口并通过上一轮机器验收。
- H049：《安全生产法》（2021年修正）第八十三条为精确直接依据；第八十一条误配保持 rejected；国务院第493号令相关条款本轮不作冗余叠加。
- H048：已确认全国法只能作为兜底；江苏地方具体年度频次义务仍待专项核验。

## 未完成事项

1. 安全清理 H049 hazard 中已经过期的“尚未终审”交接说明：先定位并复用项目现有 review/hash 内容绑定刷新机制，随后重新执行 V4 Final Acceptance。
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

**先处理 H049 结构化文件中的过期“尚未终审”说明。**

从 `chat-v4` 真实最新 HEAD 恢复后，定位项目用于生成/校验 hazard review `contentHash/contextHash` 的现有代码或命令；只在能够同步刷新受影响 review 绑定的前提下更新 `knowledge/hazards/H049.json`。完成后运行 V4 Final Acceptance 并确认所有 Gate、strict audit、search regression 继续通过。

如果恢复现场时 H049 过期说明已被其他并发提交安全清理并通过 CI，则跳过重复工作，直接转 H046/H048 江苏地方具体频次义务。

## 后续任务

1. H049 review/hash 安全刷新与最终机器验收。
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

- 江苏省安全生产现行地方法规：主要负责人季度全面检查、年度全面安全风险辨识的具体条款和现行效力。
- 仓储堆垛距离现行标准版本及条款。
- 易燃气体与助燃气体同库储存的直接技术依据。
- 建设项目安全设施设计“三同时”直接依据。
- 2026《中华人民共和国危险化学品安全法》与既有危险化学品行政法规/规章的现行并存和替代边界。
- 14 条旧标准引用候选、12 条 partial-replaced hits。

已从待核队列移除：

- H043 仓储消防培训：已完成 `XF 1131-2014 3.3.2` 专项直接依据终审。
- H049 事故后组织抢救、及时如实报告：已确认现行《安全生产法》第八十三条为精确直接依据。

## 风险 / 阻塞

当前没有必须用户决策才能继续 Phase 16 的 blocker。

已知风险：

- H049 hazard 文件的旧交接说明已过期，但直接修改可能使已绑定 review 失效；必须先使用项目既有内容绑定刷新机制。
- `knowledge/manifest.json` 计数滞后，evidence 精确总数尚需独立对账。
- 当前 645/719 是最近一次成功机器发布链结果，不能等同于全部法规专业终审完成。
- GitHub 可能存在并发提交；每轮必须重新核真实 HEAD，不能依赖本文件记载的旧 SHA。
- Drive 本轮只确认项目/目录可搜索到，没有对所有私有文件逐件做版本比较；涉及其内容时必须再核。

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
