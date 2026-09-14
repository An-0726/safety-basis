# source 目录说明

`source/` 只承载来源资料、本地私有处理支撑和当前发布包，不再同时保存多代公开架构。

```text
source/
  publication/       经审阅可公开的法规题录、官方入口与获准全文，提交 Git
  releases/current/  唯一当前公开发布包，提交 Git；禁止人工修数据
  releases/site-selection.json
                     当前发布包哈希选择
  mappings/          本地 Excel/台账导入映射，tools/pipeline/imports.py 仍在使用
  schemas/           本地 V3 兼容数据库/审阅处理所需 SQL schema 与字典

  library/           本地私有法规原件、全文 SQLite、OCR，Git 忽略
  imports/           私有待导入资料，Git 忽略
  archive/           按哈希保存的私有原件，Git 忽略
  staging/           私有导入暂存库，Git 忽略
  master/            旧 V3 SQLite 兼容层，Git 忽略
  proposals/         待人工复核提案，Git 忽略
```

## 当前职责

正式法规—条款—隐患关系只维护在根目录 `knowledge/`。`source/publication/` 只负责公开来源与授权边界，不替代 `knowledge/`，也不得因为同一法规存在多个官方来源就在正式法规页生成多个法规身份。

`source/library/fulltext.sqlite3` 是本地私有全文检索数据库。PDF 放进目录不等于已入库；只有完成哈希去重、文本提取或 OCR、题录/版本匹配和必要核验后才增加全文计数。受版权限制而无法合法公开的标准，只登记题录、效力状态和官方入口。

## 为什么 `mappings/` 和 `schemas/` 还保留

它们不是第二套法规库：

- `tools/pipeline/imports.py` 默认读取 `source/mappings/registry.json`，用于识别不同 Excel/台账布局并路由到本地暂存数据库；
- `source/schemas/` 为仍在使用的 V3 私有导入/审阅兼容工具提供数据库结构和字典；
- 这些兼容工具只服务本地资料处理，不得用于生成公开主线。

等本地导入能力全部迁移到新工具、测试和实际私有库都不再依赖它们后，才能连同对应 `tools/pipeline/` 模块一起删除。在此之前，不能为了目录简洁而单独删掉配置或 schema。

## 已退出的东西

旧公开 V2/V3 发布器、根 `data/`、`content/`、多编号历史发布包和日期版交接资料均已退出当前主线。历史需要时从 Git 历史或仓库外备份恢复，不再复制回当前 `source/`。
