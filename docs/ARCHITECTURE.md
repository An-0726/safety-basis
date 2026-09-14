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
法规身份/版本       不创造第二套法规身份
条款/隐患/关联
审核记录
        │              │
        └──────┬───────┘
               ▼
当前日期链式 Gate
               ▼
tools/v4/build_unified_release.py
               ▼
source/releases/current/ 〔生成物，Git 忽略〕
               ▼
GitHub Pages / dist/local public
```

## 职责边界

- `knowledge/`：唯一正式结构化知识源，保存法规身份、真实版本、具体条款、隐患、适用关系和审核记录；
- `source/publication/`：公开来源层，保存题录、官方入口和允许公开分发的全文；它不单独创造正式法规身份；
- `source/library/`：本地私有法规证据库，保存原件、归档、全文检索数据库和 OCR，不进 Git；
- `source/releases/current/`：当前正式站构建产物，**不再提交 Git**，CI/本地按需重建；
- `web/`：当前公开界面源码；
- `tools/pipeline/`：仍被私有导入/审阅使用的 V3 兼容层，不参与正式公开发布主线。

## 正式投影

正式隐患必须满足：active 隐患 + 通过审核 + 至少一个当前有效的 direct/fallback 关联。

正式法规索引不是 `source/publication/law-index.json` 的复制，而是：

```text
正式隐患
  → Gate 通过的正式关联
  → 正式条款
  → 条款实际引用的 knowledge/law-version
  → knowledge/law 法规身份
```

因此 publication 里的目录项、官方平台记录、未来版本和零条款资料仍可存在于“法规全文/资料库”，但不会自动变成正式法规卡。

## 时间效力

当前依据按发布包 `asOf` 判断。只有 `validityStatus=active`、已经到 `effectiveDate` 且未过 `endDate` 的版本才能支撑当前正式隐患。`upcoming` 可保留用于衔接和查阅，但实施日前不能作为当前依据。

## 发布成品为什么不进 Git

以前 `source/releases/current/` 作为提交快照存在，会产生“knowledge 已更新，但仓库里的 current 还是上一版”的双版本问题。现在 Git 只保存权威源和构建代码；GitHub Actions 每次从 `main` 现场重建、校验后部署，本地 `tools/build_local_release.py` 也先重建再组合私有全文。

历史发布结果由 GitHub Actions artifact / Git commit 的源数据状态追溯，不在当前树长期堆多份成品。

## 2026-09-14 当前正式基线

本地严格 Gate 现场重建结果：1,409 条正式隐患、55 个实际引用法规版本、1,193 条正式条款、1,524 个正式关联；519 条 proposed 候选仍在 knowledge 后台，正式包不发布候选。

## 已退出主线

旧 V2 `content/`、根 `data/`、根目录静态网站成品、多编号历史发布包、已提交的 current 快照、日期版 handoff/final/report、`docs/history/` 和旧公开 V3 发布器均退出当前主线。历史从 Git 或仓库外私有备份恢复。
