# 本地全文库与公开导出

`tools/pipeline/fulltext.py` 保存私有官方原件全文，`tools/pipeline/public_fulltext.py` 负责公开导出。全文库可以包含待核文本；公开导出还要通过母库当前法规、法规版本、证据原件、全文 SHA、复核时间和出版授权门禁。全文库的 `reviewStatus` 或 URL 单独不能放行。

私有全文清单使用 `safety-fulltext-manifest-v1`：

```json
{
  "schemaVersion": "safety-fulltext-manifest-v1",
  "documents": [{
    "documentId": "LF_001",
    "title": "正式法规名称",
    "version": "2024",
    "officialUrl": "https://example.gov.cn/law",
    "snapshotPath": "./original.html",
    "asOf": "2026-09-09",
    "currentStatus": "现行有效",
    "reviewStatus": "待核验"
  }]
}
```

```text
python tools/pipeline/fulltext.py --library PRIVATE_DIR import --manifest manifest.json
python tools/pipeline/fulltext.py --library PRIVATE_DIR search --query 消防 --limit 20
```

搜索默认按字面量处理；中文一至两字查询使用字面量 `LIKE` 回退。结果始终带 `eligibleAsCurrentBasis` 和 `basisStatus`，待核文本只能作为全文参考。原件按 SHA-256 归档，`snapshotPath` 不进入库。

公开导出清单使用 `safety-public-fulltext-checklist-v1`。每一项必须明确 `lawId`、`versionId`、`fullTextSha256`、`evidenceId`、公开方式及理由/出处、`reviewer` 和带时区的 `reviewedAt`。全文需要 `fullTextReviewed=true`，公开许可为 `official_legal_text` 或 `explicit_permission`。只发布元数据和官方入口时使用 `metadata_only`、空全文 SHA、`fullTextReviewed=false`；此方式不能发布任何正文，也不宣称已获得标准全文转载许可。

```text
python tools/pipeline/public_fulltext.py --db PRIVATE_MASTER.sqlite3 \
  --library PRIVATE_FULLTEXT --checklist reviewed.json \
  --as-of 2026-09-09 --output public-fulltext-001
```

导出器只读取母库。全文库按 `documentId=lawId`、`version=law_version.version_key` 查找目标版本。它要求目标 `law` 与 `law_version` 的当前依赖证据门禁通过；法规效力元数据证据可以与清单中的全文证据分开，全文证据仍须可读且其官方 URL、SHA 与全文归档相等。全文重新解析后的段落数和文本 SHA 与索引一致，`legal_text.directory` 还必须没有重复、无序或不支持的条目；没有中文“第 X 条”的标准按当前适配边界阻断公开导出，但原件仍保留在私有全文库。法规版本在基准日现行有效，且全文复核时间不晚于基准日。`link_only` 仍须通过母库与授权门禁，只输出官方链接元数据。

新输出目录只含公开白名单字段：`catalog.json`、`search-index.json`、`texts/<versionId>.json` 和按 SHA-256(UTF-8 二元组) 前两位分片的 `grams/<prefix>.json`。`search-index.json` 的 `gramShards` 将前缀映射到分片路径；分片仅保存 `gram -> versionId[]`，正文仍按需读取。正文分片仅含法规/版本标识、标题、版本和段落定位文本；不含本地路径、`evidenceId`、审阅理由、审阅人或审阅时间。阻断项写到输出目录同级的私有 `<output-name>.blockers.json`，待核、失效、尚未施行和未授权文本不会进入公开目录。

## 一个命令生成可预览网站

```text
python tools/pipeline/manage.py site --as-of 2026-09-09 --output NEW_SITE_DIR
python tools/pipeline/manage.py verify-site --output NEW_SITE_DIR
python -m http.server 8766 --bind 127.0.0.1 --directory NEW_SITE_DIR
```

默认读取 `source/master/safety.sqlite3`、`source/library/` 和私有 `source/master/fulltext-reviewed.json`。可分别用 `--db`、`--library`、`--checklist` 指向其他私有工作区；Node 不在 PATH 时指定 `--node`。输出必须是新目录。

`site` 统一执行母库门禁、核心数据构建、全文导出、前端资源复制与清单生成；不会替换根目录 `data/` 或部署网站。私有 `<输出名>.review.json` 保存在包外，不能加入公开 Git。公开包带 `release.json`、`site-manifest.json` 和 `checksums.json`，可独立校验。`library.html` 检索标题和正文、筛选法规、分段阅读，并跳转已收条款和关联隐患。

浏览器固定读取同一份发布清单，正文、索引和分片都校验 SHA；部署中途切换导致文件不一致时要求刷新。Service Worker 只缓存页面资源，法规数据联网读取，离线时不悄悄回退过期法律。纯静态包可迁移到其他静态托管服务；容量与发布方式另按目标服务确认。

## 原件与容量

当前 8 份官方 DOCX 总计 500,233 字节；带正文、二元组索引、前端及校验清单的网站包约 4.1 MB。两份扫描标准 PDF 合计 49,248,593 字节，保存在本地 `source/library/pending-originals/`，目录明确标记需要 OCR，不计作已可全文检索。取得原件、可抽取文字、现行性核验、具体条款适用性和允许公开是不同条件。

法规库按实际收录范围展示，不承诺覆盖全国全部法规标准。日期、复核期限、未来实施与废止门禁保证本次构建按指定基准日判断；后续修订需要补官方证据并重新构建。整部标准更新、部分强制性条文废止和上位法变化不能混为一谈。
