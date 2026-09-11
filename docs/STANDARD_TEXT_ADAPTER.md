# 标准条款结构抽取器

`tools/pipeline/standard_text.py` 用于处理 GB、GB/T、AQ、HG、DL 等采用十进制条号并包含表格的标准文件。它与面向“第 X 条”法规正文的 `legal_text.py` 分开，避免把表格序号、交叉引用和页码误当成法律条款。

输出是私有的待审阅结构目录，保留原 PDF 段落位置、条号候选、原文片段、表格边界和 SHA-256。它不会写入 `safety.sqlite3`，不会生成依据关联，也不会进入网站发布包。表格仅先保存为完整块，`rowParsingStatus=待人工确认`；待确认列边界和行跨度后，才能进一步形成条款候选。

```powershell
python -X utf8 tools/pipeline/standard_text.py `
  --snapshot "D:/Desktop/GBT+47236-2026.pdf" `
  --chapters 4 5 6 `
  --annexes B `
  --output source/exchange/continuation-20260911/gbt47236-2026/standard-directory.json `
  --workbook source/exchange/continuation-20260911/gbt47236-2026/standard-review.xlsx `
  --law-version-id LV_STD_GBT47236_2026
```

审阅顺序为：核对章节与表格覆盖范围；修复 PDF 换行和表格跨页；确认每个条号的完整原文；为确认项生成 `catalog-v1` 请求；通过 `catalog.py` 加入母库后，再用 `review.py` 逐项登记证据结论。仅通过条款及其依据关联门禁的内容能够进入网站 JSON。
