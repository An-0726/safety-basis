# 日常维护

本项目只维护一条当前主线。历史阶段说明不在当前树中保留，需追溯时查看 Git 历史；不得从旧 Excel、旧发布包或网页生成物反向覆盖当前知识源。

## 法规或标准入库

1. 原件复制到 `source/library/incoming-YYYYMMDD/`，保留用户原文件不动。
2. 计算 SHA-256 并去重；登记规范名称、编号、版本、来源、效力日期、版权边界和提取质量。
3. 可提取文本的文件导入 `source/library/fulltext.sqlite3`；乱码或扫描件进入 OCR 队列。SQLite/OCR 只用于检索定位，正式引用仍须回看官方原文或原始文件。
4. 更新 `knowledge/` 中的法规身份、法规版本、具体条款和核验记录。不能从文件名、搜索摘要或 AI 摘要推断法条和现行性。
5. 允许公开的目录、官方入口或全文才同步到 `source/publication/`。同一法规版本的多个来源不得在正式法规页生成多个法规身份。
6. 重建并验证 `source/releases/current/`。
7. 涉及架构、数据口径、法规归并、候选策略或发布范围的改动，必须同步更新根 `README.md` 和必要的 `docs/HANDOFF.md`。

## 候选处理

候选隐患的含义、去重和转正规则只认 [CANDIDATE_REVIEW](CANDIDATE_REVIEW.md)。候选可以留在 `knowledge/` 中继续审核，但不能冒充已核验法律依据。

## 数量口径

这些数字必须分开报告，不能混为“数据库总数”：

- **法规身份数**：`knowledge/laws/` 中的法规/标准身份；
- **法规版本数**：`knowledge/law-versions/` 中的真实版本；
- **正式法规页数量**：当前已核验条款实际引用并进入正式视图的法规版本；
- **公开资料目录数**：`source/publication/law-index.json` 中的来源/题录项目；它不是正式法规身份数；
- **隐患知识实体数**：`knowledge/hazards/` 全部实体，包含 active / proposed / superseded；
- **当前正式隐患数**：通过链式 Gate 的已核验隐患；
- **全文数**：私有 SQLite 中成功建立正文记录的文档；`link_only` / `metadata_only` 不算全文；
- **公开全文数**：`source/publication/fulltext/` 中获准公开分发的全文。

## 必跑检查

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/build_unified_release.py --out source/releases/current
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
```

构建前若 `source/releases/current/` 已存在，按构建器要求先移走/删除旧生成物后重新生成；不要手工修发布包。构建后确认 `source/releases/site-selection.json` 的 `releaseHash` 与当前发布包一致，并检查 `git diff` 没有混入私有原件或临时文件。

## 本地最终版

法规目录、隐患关系或私有全文库更新并验证通过后运行：

```powershell
py -3 tools/build_local_release.py
```

生成物位于 `dist/local/`，日常使用统一双击 `dist/local/打开本地最终版.cmd`。其中 `public/` 是公开精简版，`fulltext/` 是本地私有全文阅读版。`dist/` 是可重建成品，不提交 Git，也不作为任何母库反向导入。
