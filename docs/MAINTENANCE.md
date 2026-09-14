# 日常维护

## 法规或标准入库

1. 原件复制到 `source/library/incoming-YYYYMMDD/`，保留用户原文件不动。
2. 计算SHA-256并去重；登记规范名称、编号、版本、来源、效力日期、版权边界和提取质量。
3. 可提取文本的文件导入私有全文库；乱码或扫描件进入OCR队列。
4. 更新 `knowledge/` 中的法规身份、版本、条款和核验记录。不能从文件名推断现行性。
5. 允许公开的目录或全文才同步到 `source/publication/`。
6. 重建并验证 `source/releases/current/`。

## 必跑检查

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
```

如果构建器修改了当前包，还要确认 `source/releases/site-selection.json` 的 `releaseHash` 与发布包一致，并检查 `git diff` 没有混入私有原件或临时文件。

候选隐患的状态含义和接手处理流程见 [CANDIDATE_REVIEW_PLAYBOOK_20260914](CANDIDATE_REVIEW_PLAYBOOK_20260914.md)。

## 数量口径

- 法规库数量：按 `source/publication/law-index.json` 的目录项目统计。
- 知识源数量：分别统计法规身份、法规版本、条款、隐患和关联，不能相加成“法规数”。
- 全文数：只统计私有SQLite中成功建立正文记录的文档；目录项和 `link_only`/`metadata_only` 不算全文。
- 公开全文数：只统计 `source/publication/fulltext/` 中获准公开分发的文档。
# 本地最终版

法规目录、隐患关系或私有全文库更新并验证通过后，运行：

```powershell
py -3 tools/build_local_release.py
```

生成物位于 `dist/local/`，日常使用统一双击 `dist/local/打开本地最终版.cmd`。启动器只在本机回环地址临时提供页面，关闭命令窗口即停止，不会上传私有全文。其中 `public/` 是公开精简版，`fulltext/` 是不得整体对外发布的私有全文版。`dist/` 是可重建成品，不提交 Git。
