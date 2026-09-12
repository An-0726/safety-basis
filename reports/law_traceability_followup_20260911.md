# 法规原件追溯处理清单

日期：2026-09-11  
模式：read-only

## 当前库核验

- `source/library/fulltext.sqlite3`：86 个文档、45,302 个 FTS 段落。
- SQLite integrity check：`ok`；foreign-key errors：0。
- 可解析 archive 引用 48 条，缺失引用 38 条。
- 可解析引用的 archive 目录 SHA 与 document SHA 不一致：0 条。

## 待处理范围

| 范围 | 数量 | 处理要求 |
|---|---:|---|
| `archive_ref` 指向不存在的 `evidence/...` 路径 | 38 | 逐条寻找可验证的原件位置或补齐来源映射；不得直接改写成 archive 路径 |
| 未被当前 documents 引用的 archive 原件 | 7 | 先确认是旧版本、重复件还是待挂接原件；不得删除 |
| incoming 中未与 archive/全文库 SHA 匹配的原件 | 2 | 先核对文号、原件身份、页数/文本完整性，再决定是否入库 |
| `pending-originals` 待核验记录 | 2 条、4 个文件 | 需要 OCR 与完整性核对；不能视为已批准来源 |

2 个未匹配 incoming 原件为：

- `incoming-20260910/GB51309-2018-原件扫描件.pdf`
- `incoming-20260910/XF1131-2014.doc`

7 个未引用 archive 原件的 SHA-256、38 条缺失引用对应的文档 ID/标题/状态，以及候选路径检查结果，见同目录 `law_traceability_followup_20260911.json`。

本清单只记录本地可追溯性事实。缺失路径不等于原件丢失或法规失效，哈希相同也不等于法规有效、条款适用或已获审批。未执行删除、重挂接、OCR 覆盖或 SQLite 写入。
