# 当前架构

## 唯一主线

数据从 `knowledge/` 和 `source/publication/` 汇合，由 `tools/v4/build_unified_release.py` 生成 `source/releases/current/`。

```text
knowledge/ ──条款、隐患、核验关系──┐
                                  ├─ tools/v4 ─ source/releases/current ─ GitHub Pages
source/publication/ ─目录、公开全文─┘

source/library/ ─私有PDF、全文SQLite、OCR（不进Git）
```

## 职责边界

- `knowledge/`：唯一正式知识源。实体使用稳定ID，内容与适用关系分别核验。
- `source/publication/`：唯一公开出版源。保存216项已审阅目录和允许公开分发的全文集合。
- `source/library/`：本地私有完整版。保存合法取得但不一定允许公开再分发的原件和全文索引。
- `source/releases/current/`：唯一当前公开发布包，是构建结果，不是人工编辑入口。
- `tools/pipeline/`：旧V3私有导入兼容工具。只保留全文、解析、审阅和交换等仍被本地资料处理依赖的模块；旧公开发布器已移除，不得用它生成公开主线。

## 已退出主线

旧V2 `content/`、根 `data/`、根目录静态网站成品、多编号历史发布包、迁移期说明与一次性脚本均不再作为当前架构。历史材料在Git历史及本地备份中可恢复。
