# source 目录说明

`source/`只承载公开出版源、私有资料源和当前发布包，不再同时保存多代架构。

```text
source/
  publication/       经审阅可公开的法规目录与全文，提交Git
  releases/current/  唯一当前公开发布包，提交Git
  releases/site-selection.json
                     CI发布选择，提交Git
  library/           本地私有全文库、PDF、OCR结果，Git忽略
  imports/           私有待导入资料，Git忽略
  archive/           按哈希保存的私有原件，Git忽略
  staging/           私有导入暂存库，Git忽略
  master/            旧V3 SQLite母库兼容层，Git忽略
  proposals/         待人工复核提案，Git忽略
```

正式条款—隐患知识关系维护在仓库根目录 `knowledge/`。`source/publication/` 不替代 `knowledge/`：前者负责公开目录和全文授权边界，后者负责稳定ID、版本、条款、隐患和适用关系。

`source/library/fulltext.sqlite3` 是本地私有全文数据库。PDF放进目录并不等于已入库；只有完成哈希去重、文本提取或OCR、题录匹配和人工核验后，才增加全文计数。受版权限制而无法合法取得全文的标准，只登记题录、效力状态、官方入口和 `metadata_only` 状态。

旧V3导入工具暂留在 `tools/pipeline/`，仅用于私有资料导入和全文处理兼容；旧V3公开发布器已移除。公开包统一由 `tools/v4/` 构建。
