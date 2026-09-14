# 当前交接说明

> 本文件只描述**当前接手状态**，不保存历史批次细节。历史整改、迁移和交付记录统一放入 `docs/history/` 或 Git 历史。

## 1. 接手顺序

新接手者必须按以下顺序阅读：

1. 根目录 `README.md`：当前唯一主线、维护边界和硬规则；
2. `docs/ARCHITECTURE.md`：技术架构；
3. `docs/MAINTENANCE.md`：日常维护、构建和验证；
4. `docs/LEGAL_STATUS_POLICY.md`：法规效力、版本和过渡期规则；
5. 本文件：当前待办和风险。

不要从旧发布目录、历史报告、Excel 导出、网页生成物或 OCR 文本反向覆盖正式知识源。

## 2. 当前工作目录与数据源

本地当前工作仓库约定：

`D:\ESH\ESH_Codex\work\safety-basis\`

唯一当前维护入口：

- 结构化知识：`knowledge/`
- 公开出版/来源：`source/publication/`
- 本地私有证据与全文：`source/library/`（Git 忽略）
- 当前公开发布包：`source/releases/current/`（构建产物，不人工修数据）
- 网站前端：`web/`
- 当前构建器：`tools/v4/build_unified_release.py`

本地私有全文数据库：

`source/library/fulltext.sqlite3`

它是全文检索数据库，不是法律原文的最高证据。正式引用须能回到官方来源或本地原始 PDF / 网页快照。

## 3. 当前数据状态（2026-09-14）

- 新版工作簿目标集：1929条隐患。
- 当前公开发布：1921条，其中1409条已核验、512条待审核候选；8条重复记录保留追溯但不重复发布。
- `knowledge/` 当前记录：96个法规身份、97个法规版本、2,843条条款、2,014项隐患。
- `source/publication/`：216项公开目录、15份获准公开全文、140项官方入口。
- 私有全文库交接统计：170份全文、215,326个检索段落。

以上是不同统计口径，禁止把“法规目录数”“法规身份数”“法规版本数”“全文数”混为一个数字。

## 4. 当前最重要的维护任务

### A. 法规目录与法规身份去重

当前公开法规列表存在“同一法规/同一版本因为不同来源或目录记录而重复展示”的情况。处理原则：

- 先核对法规身份、版本、文号、实施日期和来源；
- 同一版本的多个官方来源保留为来源记录，不再各自生成法规卡；
- 不因前台 ID 难看而重编号现有 `LF_*`、`LV_*`、`C_*`、`H_*`；
- 真正需要合并法规身份时必须经过版本/条款/证据对账。

### B. 正式依据与候选分层

候选记录用于保存未完成的工作成果，不得冒充正式依据。后续目标是让公共正式页面优先只展示满足正式证据门禁的内容，候选留给内部审核工作台。

### C. 继续条款/证据回绑

新版工作簿仍有候选需要逐条完成：

`法规身份 → 现行/适用版本 → 具体条款 → 官方/原始证据 → 隐患适用性 → 审核记录`

AI 摘要、搜索摘要和“条款要点”只能用于发现线索，不能作为正式法条原文。

## 5. 禁止事项

- 不把私有 PDF、SQLite、企业资料提交 GitHub；
- 不直接手改 `source/releases/current/` 中的正式数据；
- 不删除/重编号稳定 ID 来解决前台显示问题；
- 不把“最新发布版本”自动等同于“当前现行适用版本”；
- 不按法规标题简单去重；
- 不把 OCR/HTML/TXT 派生文本当成最高法律证据；
- 不把历史日期文档当成当前维护规则。

## 6. 每次改动后的最低动作

涉及架构、法规数据、隐患关系、发布范围或候选策略时：

1. 更新根 `README.md`；
2. 必要时更新本 `HANDOFF.md`；
3. 运行：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/build_unified_release.py --out source/releases/current
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
```

4. 检查 `source/releases/site-selection.json` 与发布包哈希一致；
5. 确认 `git diff` 没有混入私有原件或临时文件；
6. 提交信息写清楚：改了什么、为什么、影响什么、是否需要重新审核/重建。

## 7. 历史备份

本地历史备份：

`D:\ESH\ESH_Codex\archive\safety-basis-private-backup-20260913\`

历史备份和 `docs/history/` 仅用于追溯，不是当前运行依赖。
