# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。每轮恢复项目必须先读取本文件，并核对 GitHub `chat-v4` 真实 HEAD、`knowledge/manifest.json`、最新 V4 验收结果和 Google Drive `ESH_Codex/work/safety-basis`。真实文件状态优先于聊天历史。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 Stable ID、法规/标准身份、版本、条款、可靠隐患、正确关联、证据、历史 release 与网站能力的前提下，完成 Chat-first V4，并在 Phase 16 全部验收通过后进入 `READY_FOR_ACCEPTANCE`。未经用户明确批准不得进入 Phase 17、修改 `main` 或切换生产网站。

## 当前 Phase

Phase 16：最终验收。

## 当前工作分支

`chat-v4`

## 当前真实基线

- 本轮开始核对时真实知识树：76 laws / 76 lawVersions / 99 clauses / 712 hazards / 747 links / 573 evidence / 75 requirements / 23 successions。
- 最近已确认发布链：644 publishable hazards / 714 eligible links / strictBlockers 0。
- 12 条指向 merged/superseded hazard 的 verified link 已在 `502bfa3` 处置，eligible links 从虚高的 726 修正为 714，hazard 数未减少。
- GB 50016-2014 重复版本实体已在 `196be91` 合并回 V3 既有实体，laws/lawVersions 从 77/77 回到 76/76。
- V3 冻结基线：`source/master/safety.sqlite3`，SHA-256 `7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`，本轮未修改。
- Google Drive 已确认存在 `safety-basis` 工作目录；本轮未使用 Drive 私有原件覆盖 GitHub。

## 本轮完成

本轮围绕“消防技术直接依据补齐”执行第一工作单元，完成 H_590F1752697D4CA1B2D7F949F0 与 H_69344942331F4E74ACB10315FE 的现行依据路径核验，并新增：

`docs/reviews/FIRE_LIGHTING_DIRECT_BASIS_REVIEW_20260910.md`

核心结论：

1. `H_69344942331F4E74ACB10315FE`：旧 `GB 50016-2014(2018年版) 10.3.5` 不再作为现行 direct。现行体系应优先核定 `GB 55037-2022 10.1.8`（应设置灯光疏散指示标志的建筑范围）与 `GB 51309-2018 4.5.10(1)`（出口标志灯安装位置）的组合关系。后者与“安全出口/疏散门上方安装位置”事实直接对应，属于 direct 候选。
2. `H_590F1752697D4CA1B2D7F949F0`：发现 hazard 自身语义冲突——description 写“备用照明灯具”，title/keywords/measures 写“疏散照明灯具”。因此不得机械把旧 `GB 50016 10.3.4` 平移到新标准；必须先校准该 hazard 到底描述疏散照明还是备用照明，再确定 `GB 55037-2022 10.1.9` 与 `GB 51309-2018 4.5.6/4.5.7` 的正确关系。
3. 本轮未为了增加发布数量强行 verified，未修改结构化 knowledge 数据。

## 本轮修改文件

- 新增 `docs/reviews/FIRE_LIGHTING_DIRECT_BASIS_REVIEW_20260910.md`
- 更新 `docs/CHAT_HANDOFF.md`

## 本轮校验

- 已核对 `chat-v4` 在施工过程中存在并发提交，始终以最新 GitHub 状态为准，未 reset、未 force push。
- 已核对目标 hazard 当前仍引用旧 GB 50016 语义，确认此次核验不是重复工作。
- 公开资料交叉核对确认：`GB 55037-2022 10.1.8` 对灯光疏散指示标志设置范围有直接要求；`10.1.9` 对疏散照明设置部位有直接要求；`GB 51309-2018 4.5.6/4.5.7/4.5.10` 对照明灯、出口标志灯安装方式/位置作出具体规定。
- 本轮只新增审核文档和 handoff，没有改动 knowledge，故未触发重新构建 release；结构化修改必须在下一工作单元完成后执行完整 `validate_all → build_release → gate_v4 → strict_release_audit → test_search`。
- `main`、production、GitHub Pages、V3 SQLite 均未修改。

## 当前项目状态

- Phase 16 继续。
- 644 publishable hazards / 714 eligible links / strictBlockers 0 仍作为本轮开始时最近已确认机器基线。
- 消防直接依据队列已经从“完全未核”推进为：两条照明类 hazard 已形成明确结构化方案，其中 H693 可直接进入实体/条款复用检查，H590 必须先做 hazard 语义校准。

## 未完成事项

1. 结构化收口 H_69344942331F4E74ACB10315FE：先查库内是否已存在 GB 51309-2018 law/lawVersion/clause，禁止重复造 Stable ID；再补正确 clause/link/evidence/review。
2. 校准 H_590F1752697D4CA1B2D7F949F0 的“疏散照明/备用照明”语义，再确定 direct。
3. 继续补 H_2689A44E…（室内消火栓）和 H_79D2938F…（疏散门）的现行技术 direct。
4. H039 有机废气防爆。
5. 8 条 `H_*`【Phase8】版本待办。
6. 剩余 36 条 active hazard 的“尚未终审”note 必须随逐条终审收口，禁止批量删除。
7. 20 条 pending Requirement、8 条 obligation-restatement、47 对近似重复标题、非官方证据/sourceUrl 缺口。
8. 最终 V3/V4 diff 与页面、筛选、law index、PWA/Service Worker、隐私公开投影验收。

## 下一轮第一步

**先查 `chat-v4` 现有法规/版本/条款目录，确认是否已经存在 `GB 51309-2018` 及 `4.5.10(1)`；若存在则复用 Stable ID，若不存在则按现有 V4 结构建立最小必要实体。随后结构化收口 H_69344942331F4E74ACB10315FE，并执行完整验证链。**

## 后续任务

按优先级：

1. H590 语义校准与 direct。
2. 室内消火栓、疏散门现行技术 direct。
3. H039。
4. 8 条 Phase8 版本待办。
5. 其余高价值 link/Requirement/旧标准/重复标题队列。
6. 最终 V3/V4 diff、页面/PWA/隐私验收、final candidate。

## 法规/标准待核验队列

- `GB 51309-2018`：确认库内实体及 4.5.6、4.5.7、4.5.10(1) 是否已有；优先官方/权威标准正文证据。
- `GB 55037-2022`：10.1.8、10.1.9 与目标 hazard 的关系。
- `GB 55036-2022`：室内消火栓相关条款。
- H039：HJ 2026-2013 或其他现行直接依据。
- GB 15603-2022、GB 5083-2023、GB 2894-2025、GB 9448-2025、GB 12801-2025 等 Phase8 新版条款号。

## 风险 / 阻塞

- 当前没有必须用户决策才能继续 Phase 16 的 blocker。
- GitHub 存在并发施工；每次写入前必须重新核对真实 HEAD，禁止用旧 handoff 覆盖新提交。
- H590 语义冲突若不先处理，可能把“备用照明”与“疏散照明”错误合并为同一直接依据。
- GB 51309 的结构化 verified 前必须优先取得项目已有权威原件或官方/权威来源，不能只依赖普通网页摘录。
- 机器 gate 全绿不代表法规语义已全部终审。

## 用户待决策事项

当前无。

## 明确禁止事项

- 不修改 `main`。
- 不切换生产网站 / GitHub Pages 正式数据源。
- 不覆盖 V3 SQLite 冻结基线。
- 不用旧 release / 旧报告覆盖新成果。
- 不因机器 Gate 全绿自动宣告法规语义全部正确。
- 不批量假定 links 正确，不重演 r8 质量事故。
- 不为提高发布数量强行建立或 verified 依据。
- 不把通用上位法包装成具体技术 direct 依据。
- 不因缺少整本标准全文而编造条款。
- 不批量删除“尚未终审”说明制造已完成假象。
