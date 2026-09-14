# 当前架构

## 唯一主线

```text
source/library/ （本地私有证据，不进 Git）
        │ 原件 / PDF / 网页快照 / SQLite / OCR
        │
        ├──────────────┐
        ▼              ▼
knowledge/        source/publication/
正式知识源         公开来源/题录/获准全文
        │              │
        └──────┬───────┘
               ▼
tools/v4/build_unified_release.py
               ▼
source/releases/current/
               ▼
web 当前正式投影
               ▼
GitHub Pages
```

## 职责边界

- `knowledge/`：唯一正式结构化知识源。保存法规身份、真实版本、具体条款、隐患、适用关系和审核记录，实体使用稳定 ID。
- `source/publication/`：公开来源层。保存题录、官方入口和允许公开分发的全文；来源记录不能单独创造第二个正式法规身份。
- `source/library/`：本地私有法规证据库。保存合法取得但不一定允许公开再分发的原件、归档、全文检索数据库和 OCR。
- `source/releases/current/`：唯一当前发布包，是构建结果，不是人工编辑入口。
- `web/`：当前正式用户视图。隐患默认只投影已核验记录；法规页只投影存在正式收录条款的法规版本；纯题录和来源资料由“法规全文”页面承担。
- `tools/pipeline/`：旧 V3 私有导入兼容层。仍被本地全文导入、解析、审阅和测试依赖；在这些依赖迁移前不得删除，但不得用于生成公开主线。

## 部署主线

`main` 是唯一自动部署分支。CI 每次从当前 `knowledge + source/publication + web` 重新构建 `source/releases/current/`，校验 releaseHash 后部署 GitHub Pages。仓库里已有的 `current` 快照不应被当成比源码更高一级的权威数据源。

## 版本与来源模型

正式关系固定为：

```text
法规身份 → 法规版本 → 具体条款 → 原文证据 → 隐患关联 → 审核记录
```

多个官方网页、平台条目或 PDF 可以指向同一法规版本；它们属于来源证据，不应在正式法规页生成多张法规卡。真实不同版本必须保留，并记录生效、替代、废止或 upcoming 状态。

## 已退出主线

旧 V2 `content/`、根 `data/`、根目录静态网站成品、多编号历史发布包、日期版 handoff/final/report、`docs/history/`、迁移期说明和一次性脚本均不再作为当前架构。历史材料从 Git 历史或仓库外私有备份恢复，不在当前目录树重复保存。
