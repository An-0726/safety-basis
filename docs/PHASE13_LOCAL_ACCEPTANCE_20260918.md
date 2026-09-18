# 私有母库本地最终版验收报告 (Phase 13)

- 验收日期：2026-09-18
- 验收环境：Windows 本机真实运行时 (`D:\ESH\ESH_Codex\work\safety-basis\`)
- 验收母库：`source/library/fulltext.sqlite3`
- 验收工具：`tools/build_local_release.py`、`tools/v4/verify_unified_bundle.py`

## 一、真实私有 SQLite 母库审计与不变量验证

| 检验项 | 构建前数值 | 构建后数值 | 结论 |
|---|---|---|---|
| 文件 SHA-256 | `4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f` | `4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f` | **PASS (零修改)** |
| 文件大小 (bytes) | `106958848` | `106958848` | **PASS (无变化)** |
| 文件修改时间 (mtime) | `2026-09-17T18:11:19.831234` | `2026-09-17T18:11:19.831234` | **PASS (未触碰)** |
| PRAGMA integrity_check | `["ok"]` | `["ok"]` | **PASS** |
| documents 记录数 | `171` | `171` | **PASS (171 份全量原件载体)** |
| fulltext_fts 全文段落数 | `215464` | `215464` | **PASS (215,464 段)** |
| paragraphCountSum | `215464` | `215464` | **PASS (完全一致)** |
| 逐 document mismatch | `0` | `0` | **PASS (零偏差)** |

## 二、当前最新正式业务发布状态与本地构建验收

- 最新正式生命周期：**1,494 active / 429 proposed / 92 superseded (共 2,015 hazards)**
- 公开正式发布范围：**1,494 hazards / 58 law versions / 1,266 clauses / 1,610 links**
- 公开 proposed 候选数：**0** (429 条候选全部严格隔离在知识库后台，未泄露至公网)
- Publication 来源关系：**69 canonical documents (11 full_text + 58 link_only)**
- 最终 releaseHash：`bb65650ba5e6730d1f2f4dbd950f1ff2d7bc09c8458422d471824722c3f9c31d`
- 本地最终版输出：`dist/local/` (统一门户 `index.html`、公开站点 `public/`、私有全文检索 `fulltext/`)
- 本地构建耗时：`25.41s`，退出码：`0`。
