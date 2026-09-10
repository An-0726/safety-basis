# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目必须先读取本文件，并核对 GitHub `chat-v4` 真实 HEAD、`knowledge/manifest.json`、最新 V4 验收结果和 Google Drive `ESH_Codex/work/safety-basis`。真实文件状态优先于聊天历史。本分支存在多方并发提交，**写入前必须重新 fetch，禁止 reset / force push**。

## PROJECT_STATUS

ACTIVE — Phase 16 最终验收进行中。

当前知识树实测：**77 laws / 77 lawVersions / 105 clauses / 712 hazards / 756 links / 574 evidence / 75 requirements / 23 successions**。
当前发布链：**644 publishable hazards / 723 eligible links / strictBlockers 0**（另有 21 rejected、12 superseded link）。
`knowledge/manifest.json` 已与真实树精确对账。

## 当前总目标

在保留 V3 Stable ID、法规/标准身份、版本、条款、可靠隐患、正确关联、证据、历史 release 与网站能力的前提下，完成 Chat-first V4，并在 Phase 16 全部验收通过后进入 `READY_FOR_ACCEPTANCE`。未经用户明确批准不得进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

Phase 16：最终验收。

## 当前工作分支

`chat-v4`

## 当前真实基线

- 本轮到 `c6cb126` 为止已完成 10 个提交（含并行方 2 个），全部经本机全套验收后推送。
- V3 冻结基线：`source/master/safety.sqlite3`，SHA-256 `7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`，未修改。
- `main`、production、GitHub Pages、V3 SQLite：均未修改。
- Google Drive 已确认存在 `safety-basis` 工作目录；本轮未使用 Drive 私有原件覆盖 GitHub。

## 本轮完成

### A. 专业终审与依据归位（ZCode 侧，提交 `c1aee4f`–`c6cb126`）

| 提交 | 内容 |
|---|---|
| `c1aee4f` | H046／H048 结构化收口：清理 note 过期说明，重绑 hazard review 与 4 条 link review 内容哈希。 |
| `82ff33c` | H047 补《江苏省安全生产条例》第十五条第（二）项 direct（新增 `C_JS32_15_2`）；H073 补《消防法》第二十一条第一款 direct（新增 `C074`）；H036／H064／H068 纠正 `SPECIFIC_CLAUSE_REQUIRED` 误标并补齐证据。 |
| `323fea8` | 已废止条文清理首批：新增 GB 55037-2022 第3.4.5条第1款、第3.4.2条；H066 与 `H_4C083C15…` 改用现行条文；驳回 `H_1F19FA1B…` 的失效关联（发布数 645→644）。 |
| `e6526e8` | 新建《科研建筑设计标准》JGJ 91-2019 实体与 3 条强制性条文（5.2.4／5.2.5／5.2.6）；H063 与 3 条实验室隐患归位。 |
| `432b0c4` | `manifest.json` 精确对账；修正 `sync_manifest.py` 的 Phase 22 错误，改为幂等。 |
| `2e0cb89` | 4 条消防隐患（消火栓、疏散门、疏散照明、疏散指示标志）的泛化条款由 direct 降为 fallback。 |
| `502bfa3` | **修复门禁漏洞**：`gate_link` 增加「目标 hazard 已合并/非 active」检查；12 条此类 verified 关联改为 superseded；strict audit 增加对应 excluded 分类。eligible links 由虚高的 726 修正为 714。 |
| `196be91` | 合并 GB 50016-2014 重复版本实体：`C_GB50016_*` 归并到 V3 既有 `L025`，删除 `L_GB50016／LV_GB50016_2014`；laws/lawVersions 77/77 → 76/76。 |
| `c6cb126` | 仓储类 8 条终审：新增 `C_XF1131_6_8`（堆垛间距五距，覆盖 H052/H053/H054/H055/H069）、`C_XF1131_3_3_1`（消防重点岗位培训，H067）、`C_GB15603_5_9`（易燃与氧化性气体应分离储存，H065）、`C031`（安全生产法第三十一条三同时，H079）；原泛化条款一律降 fallback。clauses 99→103，links 747→755，eligible links 714→722。 |
| `18ddf82` | 合并并行方 handoff，补充本侧批次记录与真实计数。 |
| `e9c8f6f` | H039 终审：新建 HJ 2026-2013《吸附法工业有机废气治理工程技术规范》实体（law + lawVersion + evidence + 第6.5.3条／第9.1.2条）；H039 改挂 6.5.3 为 direct，原《危险化学品安全法》第三十七条降 fallback。laws/lawVersions 76/76→77/77，clauses 103→105，links 755→756，eligible links 722→723。 |

### B. 照明/疏散指示依据核验（并行方，提交 `ef64e18`／`65e33cc`）

结论见 `docs/reviews/FIRE_LIGHTING_DIRECT_BASIS_REVIEW_20260910.md`：

1. `H_69344942331F4E74ACB10315FE`：旧 `GB 50016-2014 10.3.5` 不再作为现行 direct；应核定 `GB 55037-2022 10.1.8`（设置义务）与 `GB 51309-2018 4.5.10(1)`（出口标志灯安装位置）的组合关系，后者为安装位置 direct 候选。
2. `H_590F1752697D4CA1B2D7F949F0`：**hazard 自身语义冲突**——description 写"备用照明灯具"，title／keywords／measures 写"疏散照明灯具"。必须先做语义校准，不得把旧 `10.3.4` 机械平移；未校准前保持 fallback。

## 当前项目状态

- 机器验收：`validate_all` 6/6 PASS、六阶段 Gate PASS、strict audit blockerCount=0、search regression 20/20、确定性构建 PASS。
- 已完成专项终审：H043、H046、H047、H048、H049、H063、H064、H065、H066、H067、H068、H069、H073、H079、H052–H055，以及 3 条实验室隐患（JGJ 91 强制性条文）与 `H_4C083C15…`（GB 55037 第3.4.2条）。
- 已纠正的批量误标：H036、H064、H068 的 `SPECIFIC_CLAUSE_REQUIRED`。
- 已处置的系统性问题：GB 50016 已废止条文引用、指向已合并隐患的虚高 eligible link、GB 50016 重复版本实体、manifest 计数滞后、`sync_manifest.py` 的 Phase 22 错误。

## 未完成事项

1. **消防技术 direct 补齐**：`H_69344942331F4E74ACB10315FE`（先查库内是否已有 `GB 51309-2018` law/lawVersion/clause，禁止重复造 ID）、`H_590F1752697D4CA1B2D7F949F0`（先做疏散照明/备用照明语义校准）、`H_2689A44E…`（室内消火栓，需 GB 55036-2022 对应条款）、`H_79D2938F…`（疏散门，描述残缺需先重述）。
3. **H058 与 H043 疑似重复**（同为仓储消防安全教育培训，均指向 XF 1131-2014 3.3.2），需判定是否合并。
4. 8 条 `H_*` 的【Phase8】版本待办（GB 5083-2023、GB 15603-2022 已可回填、GB 2894-2025、GB 9448-2025、GB 12801-2025 新版条款号）。
5. 剩余 36 条 active hazard 的"尚未终审"note 必须随逐条终审收口，**禁止批量删除**。
6. 20 条 pending Requirement 语义校准。
7. 8 条 obligation-restatement、47 对近似重复标题。
8. 复核非官方证据来源（`gzhxaq.com`、`zhc.dicp.ac.cn`、`cli.im`）；补缺 `sourceUrl` 的条款与版本。
9. 刷新最终 `docs/V3_V4_DIFF_REPORT.md`。
10. 页面、筛选、law index、PWA/Service Worker、隐私公开投影人工验收。
11. 知识树稳定后生成完整 final candidate 并跑最终全套验收。

## 下一轮第一步

**先查库内法规目录，确认是否已存在 `GB 51309-2018` 及其 4.5.6／4.5.7／4.5.10(1) 条款**：存在则复用 Stable ID，不存在则按 V4 结构建立最小必要实体，然后结构化收口 `H_69344942331F4E74ACB10315FE`；同时对 `H_590F1752697D4CA1B2D7F949F0` 做"疏散照明／备用照明"语义校准。每完成一个工作单元后执行完整 `validate_all → build_release → gate_v4 → strict_release_audit → test_search` 并刷新内容绑定。

## 法规/标准待核验队列

- `GB 51309-2018`：库内实体与 4.5.6／4.5.7／4.5.10(1)。
- `GB 55037-2022`：10.1.8、10.1.9 与照明类 hazard 的关系（3.4.2／3.4.5／7.1.2 已核实原文）。
- `GB 55036-2022`：3.0.5 室内消火栓条款完整原文（尚未取得）。
- `HJ 2026-2013`：已完成实体化与 H039 归位。
- Phase8 新版条款号：GB 5083-2023、GB 2894-2025、GB 9448-2025、GB 12801-2025。

## 风险 / 阻塞

- 当前没有必须用户决策才能继续 Phase 16 的 blocker。
- **GitHub 存在并发施工**：本轮已实际遇到一次远端领先（`ef64e18`／`65e33cc`）。每次写入前必须重新 fetch，用 merge 而非 force push；handoff 变更可能与并行方互相覆盖，需以最新远端为准再补充。
- `H_590F1752…` 语义冲突若不先处理，可能把"备用照明"与"疏散照明"错误合并为同一直接依据。
- 消防技术 direct 仍不完整：4 条消防隐患目前只有 fallback。
- 机器 gate 全绿不代表法规语义已全部终审；关联层审核历史上有 95% 来自批量流程。

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
- 不批量删除"尚未终审"说明制造已完成假象。
- 不 reset / force push / 覆盖并行提交。
