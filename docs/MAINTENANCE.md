# 日常维护

本项目只维护一条当前主线。历史从 Git 恢复，不从旧 Excel、旧发布包或网页生成物反向覆盖 `knowledge/`。

## 法规或标准入库

1. 原件复制到 `source/library/incoming-YYYYMMDD/`，保留用户原文件不动；
2. 计算 SHA-256 去重，登记规范名称、编号、版本、来源、发布日期/实施日期、版权边界和提取质量；
3. 文本/OCR 导入 `source/library/fulltext.sqlite3` 只用于检索定位，正式引用仍回看官方原文或原始文件；
4. 更新 `knowledge/` 的法规身份、版本、具体条款、隐患、关联和审核记录；
5. 允许公开的题录、官方入口或全文才同步到 `source/publication/`；多个来源不得制造多个正式法规身份；
6. 运行完整 Gate、构建和校验；涉及架构/口径/归并/候选策略时同步更新 README；交接方式实际变化时再更新 HANDOFF。

## PHASE 11 触发条件

当前处于长期维护等待态。出现下列任一情况才进入新的维护批次：

- 新法规、标准、修订版本、废止/替代关系或官方证据需要纳管；
- 新隐患、既有隐患修订、候选证据补齐或 `proposed` 转正审核；
- Validate / strict gate / fresh build / verify / Pages 出现异常；
- `PROJECT_STATE.md`、README、HANDOFF 与远端实际状态出现实质冲突；
- 私有 SQLite 到达计划备份/integrity 维护点，或出现文档数、FTS 行数、paragraph sum、archive 引用等不变量异常。

没有上述触发条件时，不为“保持活跃”而改业务数据，不重复正式发布验收，也不把 499 条 `proposed` 强行清零。

## 候选

候选规则只认 `docs/CANDIDATE_REVIEW.md`。`proposed` 可留在 knowledge 继续审核，但**不得进入正式发布包**。

## 数量口径

- 法规身份数：`knowledge/laws/`；
- 法规版本库存数：`knowledge/law-versions/`；
- 正式法规页数：当前正式条款实际引用并通过 Gate 的法规版本；
- publication 数：公开来源/题录项目，不是正式法规身份数；
- knowledge 隐患数：含 active / proposed / superseded 等全部实体；
- 正式隐患数：当前日期链式 Gate 通过的已核验隐患；
- 私有全文数：SQLite 中成功建立正文记录的文档；
- 公开全文数：`source/publication/fulltext/` 中允许公开分发的全文。

当前 2026-09-17 正式基线：1,429 条正式隐患、57 个实际引用法规版本、1,205 条正式条款、1,544 个正式关联；499 条 proposed 只留后台。knowledge 库存为 103 laws / 106 lawVersions / 2,847 clauses / 2,014 hazards / 1,567 links；publication 为 69 个 canonical 来源关系（11 full_text + 58 link_only）。

## 正式发布构建

`source/releases/current/` 与 `source/releases/site-selection.json` 都是**生成物并已 Git 忽略**。不要提交、不要手改、不要拿旧快照做输入。

本地需要单独重建正式包时：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
# 先删除本地旧生成物 source/releases/current 和 site-selection.json
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
# 按 release.json 的 releaseHash 生成 site-selection.json 后：
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
```

GitHub Actions 会自动完成删除旧生成物、重建、生成 selection、严格校验和部署。任何正式业务数据变化仍按现有 Validate → strict gate → fresh build → verify → Pages → online acceptance 链闭环。

## 本地最终版

日常本地使用直接运行：

```powershell
py -3 tools/build_local_release.py
```

该脚本会自动：

1. 校验 knowledge 和严格 Gate；
2. 删除本地旧 `source/releases/current/`，从当前源码重建正式公开包；
3. 验证发布包；
4. 只读打开 `source/library/fulltext.sqlite3`；
5. 生成 `dist/local/public`、`dist/local/fulltext` 和统一入口。

`dist/` 与 `source/releases/current/` 都是可重建成品，不提交 Git，也不得反向当母库。
