# 当前交接说明

> 本文件只描述**当前接手状态**。历史批次、旧阶段报告和旧“最终版”不留在当前目录树；需要追溯时直接查看 Git 历史。

## 1. 接手顺序

新接手者按以下顺序阅读：

1. 根 `README.md`：唯一主线、维护边界、当前数据口径和本次收口说明；
2. `docs/ARCHITECTURE.md`：技术架构；
3. `docs/MAINTENANCE.md`：入库、构建和验证；
4. `docs/LEGAL_STATUS_POLICY.md`：法规效力和版本规则；
5. `docs/CANDIDATE_REVIEW.md`：候选去重和转正；
6. 本文件：当前待办和风险。

不要从旧 Excel、旧发布包、历史网页、OCR/TXT/HTML 派生文本反向覆盖当前知识源。

## 2. 当前唯一工作入口

本地工作仓库：

`D:\ESH\ESH_Codex\work\safety-basis\`

- 正式结构化知识：`knowledge/`
- 公开来源/题录/获准全文：`source/publication/`
- 本地私有法规证据：`source/library/`（Git 忽略）
- 当前发布包：`source/releases/current/`（构建产物）
- 网站源码：`web/`
- 当前构建器：`tools/v4/build_unified_release.py`

私有全文检索数据库：`source/library/fulltext.sqlite3`。它用于定位原文，不取代官方网页或原始 PDF 的证据地位。

## 3. 当前数据口径（2026-09-14）

- 新版 Excel 目标集：1,929 个唯一隐患 ID；621 条修订，1,308 条保留。
- `knowledge/`：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体；其中 1,419 active、517 proposed、78 superseded。
- 当前已核验隐患：1,409 条；8 条已识别重复记录不重复发布；其余候选继续后台回绑条款和证据。
- `source/publication/`：216 项公开题录/来源目录、15 份获准公开全文、140 项官方入口。目录项不是法规身份数。
- 私有全文交接统计：170 份全文、215,326 个检索段落，后续以实际 `fulltext.sqlite3` 复核为准。

不要再把旧批次“1250”、Excel“1929”、knowledge“2014”、publication“216”或旧发布法规卡“223”当成同一种数据库总数。

## 4. 网站当前行为

- 正式隐患视图只加载 `已核验` 记录；`proposed` 仍保存在 knowledge 中，但不与正式结果混排。
- 正式法规视图只加载存在正式收录条款的法规版本；只有题录/来源的 publication 记录留在“法规全文/来源资料”层。
- 技术稳定 ID 继续保留用于关联，但长 `LV_* / H_*` 不作为主要用户展示标签。
- 主导航只保留“隐患速查 / 法规库 / 法规全文”。
- `main` 是唯一自动部署分支；GitHub Actions 会从当前源码重新构建 `source/releases/current/` 后再验证和部署。

## 5. 当前优先任务

1. 等云盘中的本地 `source/library/` 上传完成后，对实际 PDF / archive / incoming / SQLite 做一次完整去重盘点；不要凭目录名删除原始证据。
2. 继续对候选做“隐患去重 → 法规身份/版本确认 → 具体条款 → 原文证据 → 适用性审核 → 转正”。
3. 法规重复只在确认“同一身份 + 同一真实版本”后合并来源；不同真实版本必须保留版本关系。
4. 每次大量转正或法规归并后更新 README 当前基线，并重新构建/验证网站。

## 6. 禁止事项

- 不提交私有 PDF、SQLite、企业资料或受限全文；
- 不直接手改 `source/releases/current/` 数据；
- 不为了界面整洁重编号稳定 ID；
- 不把“最新发布版”自动当作“当前现行版”；
- 不按标题相似直接删隐患或法规；
- 不把 AI 摘要、搜索摘要、OCR 或 Excel 条款要点当正式法条；
- 不重新创建多个日期版 handoff、final、latest 或 history 目录。

## 7. 每次改动后的最低动作

涉及架构、法规/隐患数据、候选策略或发布范围时：

1. 同步更新根 `README.md`；
2. 必要时更新本文件；
3. 运行完整校验/测试；
4. 由构建器重新生成 `source/releases/current/`；
5. 核对 releaseHash / site-selection；
6. 确认 Git diff 没有混入私有原件；
7. 提交说明写清“改了什么、为什么、影响什么、是否需重新审核/重建”。

本地历史备份仍位于仓库外：

`D:\ESH\ESH_Codex\archive\safety-basis-private-backup-20260913\`

该备份只用于灾难恢复和历史追溯，不是当前运行依赖。
