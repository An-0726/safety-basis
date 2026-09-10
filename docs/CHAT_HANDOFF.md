# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目必须先读取本文件，并核对 GitHub `chat-v4` 真实 HEAD、`knowledge/manifest.json`、最新 V4 验收结果和 Google Drive `ESH_Codex/work/safety-basis`。真实文件状态优先于聊天历史。本分支存在多方并发提交，**写入前必须重新 fetch，禁止 reset / force push**。

## PROJECT_STATUS

**READY_FOR_ACCEPTANCE** — Phase 16 最终验收已完成，等待用户批准是否进入 Phase 17。

当前知识树实测：**85 laws / 85 lawVersions / 177 clauses / 712 hazards / 829 links / 590 evidence / 75 requirements / 23 successions**。
最近一次完整候选发布链验收：**641 publishable hazards / 801 eligible links / strictBlockers 0**，`sourceStateHash 3e329e2a32bf7b2d`。

完整验收结论见 **`docs/V4_FINAL_ACCEPTANCE_REPORT.md`**（A–J 全部 PASS）。
候选包已包含网站前端与数据投影，可在 `source/releases/v4-candidate-20260910/` 直接起静态服务验证；
网站投影由 `tools/v4/build_site_data.py` 生成，已接入 CI 与双构建确定性检查。

**未获用户明确批准前不得进入 Phase 17、修改 `main` 或切换生产网站。**

## 当前总目标

在保留 V3 Stable ID、法规/标准身份、版本、条款、可靠隐患、正确关联、证据、历史 release 与网站能力的前提下，完成 Chat-first V4，并在 Phase 16 全部验收通过后进入 `READY_FOR_ACCEPTANCE`。未经用户明确批准不得进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

Phase 16：最终验收。

## 当前工作分支

`chat-v4`

## 当前真实基线

- 本轮核对时 GitHub `chat-v4` 已推进至 `e24c5f4d84d566c2129cbba78e63c474ba67e1a9`；随后新增 H058/H043 重复判定文档提交 `94a356ad96e594a145a10dbe03b48d710cd22509`，本 handoff 更新提交在其后。
- `e24c5f4` 新增 `tools/v4/ocr_pdf.py`，用于扫描 PDF 的全文检索定位；OCR 结果只用于定位线索，条款引用仍须对原件或第二来源核验。
- V3 冻结基线：`source/master/safety.sqlite3`，SHA-256 `7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`，未修改。
- `main`、production、GitHub Pages、V3 SQLite：均未修改。
- Google Drive 已按真实父目录确认 `ESH_Codex/work/safety-basis`，本轮未使用 Drive 私有原件覆盖 GitHub；Drive 工作目录仍保留源码、docs、source、data、tools 等历史工作成果。

## 本轮完成

### A. 既有 Phase 16 专业终审

- H046／H048 结构化收口并重绑审核内容哈希。
- H047 补《江苏省安全生产条例》第十五条第（二）项 direct；H073 补《消防法》第二十一条第一款 direct。
- 已废止 GB 50016 条文逐步替换为现行依据；失效关联不为维持发布数量而强行保留。
- 新建 JGJ 91-2019《科研建筑设计标准》必要实体与强制性条文，归位 H063 及实验室隐患。
- 修复 `gate_link` 未检查目标 hazard 已合并/非 active 的系统性漏洞，12 条历史关联转为 superseded。
- 合并 GB 50016-2014 重复版本实体。
- 仓储类、消防类及 H039 等多条隐患已完成直接依据终审或角色降级。
- 当前 manifest 已对账为 78/78/111/712/761/576/75/23。

### B. 本轮新增：H058 / H043 重复判定

已创建 `docs/reviews/H058_H043_DUPLICATE_REVIEW_20260910.md`。

结论：H058《仓储场所在岗人员消防安全教育频次不足》完整落在 H043《仓储场所未按要求开展消防安全教育培训》的规范义务范围内，没有形成独立检查对象或独立义务边界，**建议 H058 合并至 H043，并保留 H058 Stable ID 作为历史实体**。

本轮未直接执行合并。正式合并前必须先核对 H058 的 links 与 review binding，确认没有 H043 尚未承接的唯一有效依据；随后按现有 merged hazard 处理惯例同步更新 lifecycle、mergedInto、关联状态和审核内容哈希，避免只改 hazard 而遗留可发布关联。

### C. 并发施工状态

本轮观察到 `chat-v4` 在工作期间从 `f82350e6` 继续推进到 `e24c5f4`。最新并行工作新增扫描 PDF OCR 适配器，并已用于定位 JGJ 91-2019 条款。由于存在持续并发，本轮没有盲目覆盖 H058 数据文件。

## 当前项目状态

- Phase 16 继续进行，没有需要用户立即决策的 blocker。
- 机器验收最近一次完整记录：`validate_all` 6/6 PASS、六阶段 Gate PASS、strict audit blockerCount=0、search regression 20/20、确定性构建 PASS。
- 上述完整候选验收数据属于最近一次完整构建记录；当前知识树又有增量修改，因此最终 `READY_FOR_ACCEPTANCE` 前必须统一重建 candidate 并重跑全套验收。
- H058/H043 重复语义已经判定，数据层合并尚未执行。
- `tools/v4/ocr_pdf.py` 已补上扫描件全文定位能力，但 OCR 文本不能直接作为条款原文的唯一证据。

## 未完成事项

1. **消防技术 direct 补齐**：`H_69344942331F4E74ACB10315FE`、`H_590F1752697D4CA1B2D7F949F0`、`H_2689A44E…`、`H_79D2938F…`。
2. **执行 H058 → H043 合并**：先查 H058 全部 links / reviews / 唯一依据，再按现有 merged precedent 原子化处理。
3. 8 条 `H_*` 的【Phase8】版本待办（含 GB 5083-2023、GB 15603-2022、GB 2894-2025、GB 9448-2025、GB 12801-2025 新版条款号）。
4. 剩余 active hazard 的“尚未终审”note 随逐条终审收口，禁止批量删除。
5. 20 条 pending Requirement 语义校准。
6. obligation-restatement 与近似重复标题继续逐条语义判定。
7. 复核非官方证据来源并补缺 `sourceUrl`。
8. 刷新最终 `docs/V3_V4_DIFF_REPORT.md`。
9. 页面、筛选、law index、PWA/Service Worker、隐私公开投影人工验收。
10. 知识树稳定后生成完整 final candidate 并跑最终全套验收。

## 下一轮第一步

**先完成 H058 → H043 合并前置检查**：枚举 H058 当前所有 links 与 hazard/link reviews，确认是否存在 H043 未承接的唯一有效依据；同时找一个已经正确 merged 的 hazard 作为字段和关联状态处理样板。若无独立依据冲突，则执行保留 Stable ID 的合并并刷新相关内容哈希。

普通内容批次只做必要的 schema / 引用 / 局部门禁 / hash binding 校验，不再每个小批次机械重建完整 candidate；只有修改 Gate、构建、公开投影、搜索、隐私或 PWA 等发布链逻辑时立即做对应完整回归。知识树稳定后统一进行最终完整构建、双构建确定性验证和全套验收。

## 法规/标准待核验队列

- `GB 51309-2018`：库内实体与 4.5.6／4.5.7／4.5.10(1)。
- `GB 55037-2022`：10.1.8、10.1.9 与照明类 hazard 的关系。
- `GB 55036-2022`：室内消火栓直接依据的准确条款定位与原文。
- Phase8 新版条款号：GB 5083-2023、GB 2894-2025、GB 9448-2025、GB 12801-2025。

## 风险 / 阻塞

- 当前没有必须用户决策才能继续 Phase 16 的 blocker。
- **GitHub 存在持续并发施工**：每次写入前必须重新 fetch；禁止 reset / force push；如果目标文件已变化，先吸收真实远端状态再处理。
- 机器 Gate 全绿不代表法规语义已全部终审；关联层历史审核曾受批量流程污染。
- OCR 会误识别数字、标准号和条款号，只能用于检索定位，不能作为 clause.quote 的唯一核验来源。
- H058/H043 合并如不先检查 links / reviews，可能丢失独立依据或留下指向 merged hazard 的错误可发布关联。

## 用户待决策事项

当前无。只有进入 Phase 17、修改 `main` 或正式切换生产网站时需要用户明确批准。

## 明确禁止事项

- 不修改 `main`。
- 不切换生产网站 / GitHub Pages 正式数据源。
- 不覆盖 V3 SQLite 冻结基线。
- 不用旧 release / 旧报告覆盖新成果。
- 不因机器 Gate 全绿自动宣告法规语义全部正确。
- 不批量假定 links 正确，不重演 r8 质量事故。
- 不为提高发布数量强行建立或 verified 依据。
- 不把通用上位法包装成具体技术 direct 依据。
- 不因缺少整本标准全文而编造条款；可靠局部条款可按证据等级核验。
- 不批量删除“尚未终审”说明制造已完成假象。
- 不 reset / force push / 覆盖并行提交。
