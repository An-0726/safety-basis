# 私有法规全文库整理与修复方案

日期：2026-09-14  
适用范围：本地私有 `source/library/`；不适用于公开发布数据。

## 1. 目的

本方案把私有全文库的“证据原件、检索文本、法规身份”拆开治理，避免用一次简单的 SQLite 去重同时破坏证据链、历史版本或较好的全文抽取结果。

正式法规事实仍以 `knowledge/` 的法规身份、版本、条款和审核为准；`source/library/fulltext.sqlite3` 只承担私有全文检索与本地查阅，不是最高法律证据。

## 2. PHASE 1 已核结论

只读审计确认：

- 当前全文库有 170 个 document、166 个唯一文件 SHA、215,326 个全文段落；
- `sum(documents.paragraph_count) = count(fulltext_fts) = 215,326`，逐 document 的段落计数也一致；
- 存在 4 组“同一文件 SHA 被登记成两个 document”的重复身份；
- 同标题双记录共 20 组，其中 2 组是真实不同版本，必须分别保留；其余属于同一真实版本的旧身份/再导入身份/多载体表达；
- current archive 有 7 个未被 document 直接引用的历史对象，经读取均为文本派生物，不是 7 部漏入全文库的独立法规；
- 旧 `evidence/...` 引用仍有历史残留，不能把不存在的旧路径随意重指到标题相似文件；
- `pending-originals` 中历史待 OCR 项不能仅凭“待办仍存在”再次导入，必须先与当前已检索版本核同一性；
- 当前 `document_id` 同时存在 `LF_*`、`LV_*`、旧 `Lxxx`、标准号等多种命名，不得直接当 canonical law-version 主键；
- 当前 FTS5 倒排索引存在 `malformed inverted index`，但在副本上执行 FTS rebuild 后可恢复 `PRAGMA integrity_check = ok`，同时 documents 数、全文段落数和全文内容摘要均保持不变。

因此：**FTS 索引损坏**与**法规身份重复**是两个独立问题，必须分开修。

## 3. 固定维护原则

1. `archive/` 的原件/历史载体默认不可变；不能因为 document 重复就删除原始证据。
2. 同一真实法规版本可以有多个来源载体，但正式结构化版本只能有一个 canonical identity。
3. `fulltext_fts` 是可重建检索索引；可以修复，但修复不得改变全文内容行。
4. OCR、TXT、HTML、抽取文本只是检索派生物，不能升级成正式法规原文证据。
5. 真实不同版本必须分别保留；“标题一样”绝不是合并依据。
6. 旧稳定 ID 不做破坏性重编号；需要归并时用 alias/canonical mapping 过渡。
7. 任何工作母库写操作都必须先有一致性备份、变更前指标、变更后指标和回滚路径。

## 4. PHASE 2 决策

### 4.1 先修 FTS，不同时做 document 去重

第一项实际修复只做：

```sql
INSERT INTO fulltext_fts(fulltext_fts) VALUES('rebuild');
```

但必须通过安全维护工具执行，不能手工直接敲库。执行前后至少核对：

- `PRAGMA integrity_check`；
- `PRAGMA foreign_key_check`；
- documents 数；
- `count(fulltext_fts)`；
- `sum(documents.paragraph_count)`；
- 每个 `document_key` 的 FTS 行数是否等于 `paragraph_count`；
- 按 `document_key, paragraph_no` 排序后的全文内容 SHA-256 摘要。

副本测试已证明 rebuild 可以把完整性从 FTS 错误恢复为 `ok`，同时保持 170 / 215,326 以及全文内容摘要不变。

### 4.2 4 组同 SHA 重复 document 不直接 DELETE

四组重复里有两组的全文抽取完全相同，另两组虽然原始文件相同，但历史抽取文本不同。因此统一策略是：

- 先建立 alias/canonical 映射；
- 本地展示层只显示一个法规版本入口；
- 先保留全部历史 FTS 行，直到确认 canonical 搜索载体；
- 对文本完全相同的重复行，可在后续安全删除其中一套 FTS/document 记录；
- 对文本不同的重复行，必须比较可读性、条款完整性和检索质量，不能按段落数量机械选择。

已观察到：

- `GB/T 12801-2008` 两套全文抽取一致，可列为确定性身份重复；
- `GB 55036-2022` 两套全文抽取一致，可列为确定性身份重复；
- `HJ 2025-2012` 两套抽取分段和文本摘要不同，需要保留到 canonical 搜索文本确认；
- `GB 15603-2022` 的旧抽取含明显字体编码残片，而新抽取虽有 OCR 噪声但总体更可检索，不能因旧记录段落数更多就保留旧抽取。

### 4.3 同一真实版本多身份：先 alias，不删证据

PHASE 1 中除 2 组真实不同版本外，其余同标题双记录均进入“同一真实版本多身份”队列。处理方式：

- canonical 法规身份和版本最终以 `knowledge/` 为准；
- SQLite 旧 `document_key` 先作为 alias 保留；
- publication/source 只作为来源，不产生第二个法规版本；
- local library 页面应按 canonical version 聚合，不向用户展示两个法规卡；
- 等 alias 映射、全文质量和引用都验证后，再决定是否物理删除重复 document 行。

### 4.4 真实不同版本必须保留

目前已明确至少包括：

- `AQ 4228-2012` / `AQ 4228-2025`；
- `GB/T 13869-2017` / `GB/T 13869-2026`。

后续还要继续按文号、版本时间、生效/失效日期而不是标题判断版本关系。尚未实施版本不得被当作当前正式依据。

### 4.5 7 个 archive-only 文本派生物

这 7 个对象均已确认是历史文本派生物，并且对应法规在当前 SQLite 已另有 document。

本轮不删除、不移动它们。先在私有 inventory 中标记为 `legacy_derived_text`；它们：

- 不作为法规独立身份；
- 不作为最高原始证据；
- 不计入“漏入全文库法规”；
- 后续如要迁出 `archive/`，必须在完整备份和引用扫描后单独执行。

### 4.6 旧 `evidence/...` 路径

旧路径缺失不能通过“同标题猜文件”修复。

仅在以下条件都满足时才能重绑：

- 原始 SHA 明确一致；
- 法规版本明确一致；
- 目标 archive 文件存在且 SHA 校验通过。

否则保持 legacy missing 状态；本地页面可以不显示原始文件链接，但全文检索记录可继续存在。

### 4.7 `pending-originals` 与 inventory-only 文件

- TSG 08-2026、TSG 92-2026 的旧待 OCR 记录先做来源/版本核对，不直接二次 OCR/导入；
- inventory 中未命中 SQLite 的文件不批量导入；
- 征求意见稿、编制/修订说明、指南、工作手册、错误命名文件不得因为“文件存在”就进入正式依据链；
- 只有确认属于需要保存的官方版本/历史版本/来源载体后才进入私有证据库。

## 5. 工作母库实际写入前的备份规则

优先使用 SQLite Backup API 创建一致性快照，而不是在数据库可能被占用时直接复制文件。

备份必须：

1. 写到 `source/library/backups/` 或项目外部私有备份目录；
2. 名称带 UTC/本地时间戳；
3. 记录源文件大小与 SHA-256；
4. 记录备份文件大小与 SHA-256；
5. 对备份执行可打开性、表计数和 FTS 行计数核验；
6. 写操作结束前不删除该备份。

注意：因为备份发生在 FTS rebuild 之前，备份会保留当前 FTS 索引故障，这是正常的——它的职责是完整回滚到变更前状态，而不是作为修复后的新基线。

## 6. PHASE 3 推荐执行顺序

1. 确认没有其他进程正在写 `fulltext.sqlite3`；
2. 运行维护工具 `audit`，保存变更前指标；
3. 创建 SQLite 一致性备份；
4. 仅执行 FTS rebuild；
5. 再次运行 `audit`；
6. 必须得到 `integrity_check=ok`；
7. documents、FTS 行数、段落总数、逐 document 段落数、全文内容摘要必须与 rebuild 前一致；
8. 做若干中文短词、条款号、标准号搜索抽检；
9. rebuild 成功后，才进入 alias/canonical 映射；
10. document 物理删除/合并属于后续独立变更，不与 FTS rebuild 同批执行。

## 7. 回滚条件

出现任一情况立即停止后续写操作：

- documents 数变化；
- FTS 行数变化；
- `sum(paragraph_count)` 与 FTS 行数不一致；
- 全文内容摘要变化；
- 任一 document 的 FTS 行数与 `paragraph_count` 不一致；
- rebuild 后 `integrity_check` 仍非 `ok`；
- 本地全文搜索出现明显缺失；
- archive_ref 出现新的缺失或 SHA 不一致。

如果需要回滚：关闭数据库连接和本地站点进程，保留失败库副本，再从一致性备份恢复；不得一边有 SQLite 写连接一边做文件替换。

## 8. PHASE 2 退出条件

PHASE 2 完成需要满足：

- 已明确 FTS rebuild 与法规身份去重分批执行；
- 已定义备份、前后指标和回滚门槛；
- 已明确 4 组同 SHA 重复的处理方式，不再采用“直接删一行”；
- 已明确真实历史版本继续保留；
- 已明确 7 个历史派生文本对象的性质；
- 已明确旧 evidence、pending、inventory-only 的处理门禁；
- 工作母库在进入 PHASE 3 前仍未被本轮操作写入。

下一步：实现并验证安全维护工具；在副本上跑通备份 + audit + rebuild + audit，再由本机工作库执行 PHASE 3。