# 当前交接说明

> 本文件只描述当前接手状态。旧批次、旧“最终版”和旧发布快照不留在当前目录树；历史直接查看 Git。

## 1. 先读什么

依次阅读：根 `README.md` → `docs/ARCHITECTURE.md` → `docs/MAINTENANCE.md` → `docs/LEGAL_STATUS_POLICY.md` → `docs/CANDIDATE_REVIEW.md` → 本文件。

不要从旧 Excel、旧发布包、网页生成物、OCR/TXT/HTML 反向覆盖 `knowledge/`。

## 2. 唯一工作入口

本地仓库：`D:\ESH\ESH_Codex\work\safety-basis\`

- `knowledge/`：正式结构化知识源；
- `source/publication/`：公开题录、官方入口、获准全文；
- `source/library/`：本地私有法规证据库，Git 忽略；
- `source/releases/current/`：**运行时生成物，Git 忽略**；
- `web/`：网站源码；
- `tools/v4/build_unified_release.py`：正式发布构建器。

`source/library/fulltext.sqlite3` 仅是全文检索数据库；正式引用仍须回到官方原文或原始 PDF / 网页快照。

## 3. 当前真实数据口径（2026-09-14）

PR #29 的完整 CI 从当前源码实际重建得到：

- knowledge 库存：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体、1,547 个关联；
- 当前正式发布：**1,409 条隐患、55 个实际引用法规版本、1,193 条正式条款、1,524 个正式关联**；
- knowledge 中当前 proposed 候选：**512 条**；正式公开候选：**0 条**；
- 公开全文资料：15 份全文、140 个官方入口；
- 新版 Excel 目标集仍是 1,929 个唯一隐患 ID（621 条修订、1,308 条保留），它不是正式发布数量；
- 私有全文旧交接记录为 170 份全文、215,326 个检索段落，待云盘上传完成后用实际 SQLite 重新核实。

旧文档里的“517 proposed”“1921=1409+512”“223 个法规版本”等数字属于旧口径，**不得再作为当前正式站统计**。

## 4. 当前发布规则

- 正式站只发布当前 `asOf` 日期链式 Gate 通过的 active 隐患；
- `proposed` 候选保留在 `knowledge/` 后台，不进入正式包；
- 正式法规页只包含正式条款实际引用的 `knowledge/law-versions`；
- `source/publication` 只提供来源/题录/全文资料，不再制造第二套正式法规卡；
- `upcoming` 尚未实施版本可留作版本衔接和资料查阅，但实施日前不能支撑当前正式隐患；
- Git 不再提交 `source/releases/current/` 与 `site-selection.json`，避免生成快照变成另一套旧版本；CI 和本地构建都现场重建。

## 5. 本地 agent 安全边界

本轮公开仓库整理没有修改：

- `source/library/fulltext.sqlite3`；
- 私有 PDF / archive / incoming；
- OCR 和私有全文索引；
- 既有 `LF_* / LV_* / C_* / H_*` 稳定 ID。

`tools/build_local_release.py` 现在会先从当前 `knowledge + publication + web` 重建正式公开包，再**只读**组合 `source/library/fulltext.sqlite3` 生成 `dist/local/`。

## 6. 下一步

1. 等云盘 `source/library/` 上传完成，实际盘点 PDF、archive、incoming、SQLite、OCR 的重复和版本关系；
2. 对 512 条候选继续做“隐患去重 → 法规身份/版本 → 具体条款 → 官方/原始证据 → 适用性 → 审核 → 转正”；
3. 法规只在确认“同一身份 + 同一真实版本”后归并来源，不按标题模糊删除；
4. 大批量转正/归并后重新跑 Gate、构建和 CI，并同步 README/HANDOFF。

## 7. 禁止事项

不得提交私有 PDF/SQLite；不得手改发布包；不得为了界面整洁重编号稳定 ID；不得把“最新发布”自动等同“当前适用”；不得把 AI/搜索摘要/OCR/Excel 条款要点当正式法条；不得重新堆多个 final/latest/日期版交接。
