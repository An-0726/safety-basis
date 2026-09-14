# 当前交接说明

> **AI / Codex / 新聊天窗口先读根目录 [`AGENTS.md`](../AGENTS.md)。**
> `AGENTS.md` 是“当前做到哪、下一步是什么”的唯一实时接手记忆；本文件只保留给人的简短交接摘要。历史批次、旧 final/latest/日期版不留在当前树，追溯看 Git。

## 1. 当前唯一体系

本地工作仓库：`D:\ESH\ESH_Codex\work\safety-basis\`

- `knowledge/`：唯一正式结构化知识源；
- `source/publication/`：公开题录、官方入口、获准全文；
- `source/library/`：本地私有法规证据库，Git 忽略；
- `source/releases/current/`：运行时生成物，Git 忽略；
- `web/`：网站源码；
- `tools/v4/build_unified_release.py`：正式发布构建器。

正式引用仍须遵守“法规身份 → 适用版本 → 具体条款 → 逐字原文 → 官方/原始证据 → 适用性审核”。AI 摘要、搜索摘要、OCR、TXT/HTML、Excel 条款要点不得替代法规原文。

## 2. 当前发布基线（2026-09-14）

- 正式隐患：1,409；
- 实际引用法规版本：55；
- 正式条款：1,193；
- 正式关联：1,524；
- `proposed`：512，仅 `knowledge/` 后台，公网 0；
- knowledge 库存：96 个法规身份、97 个版本、2,843 条条款、2,014 个隐患实体、1,547 个关联。

正式站只发布当前日期 Gate 通过的 active 隐患；`upcoming` 尚未实施版本不得提前支撑当前正式隐患；publication 不再制造第二套正式法规卡。

## 3. 当前实际任务

当前不是继续堆前端，也不是先大量回绑候选；正在做的是：

**本地私有法规母库 `source/library/` 的实体级只读体检与去重设计。**

云盘直读已确认 `fulltext.sqlite3` 与 archive / incoming / inventory 等都已同步。SQLite 当前已核：170 documents、215,326 检索段、166 个唯一文件 SHA、4 组同 SHA 重复 document；FTS5 倒排索引完整性有损坏提示，但仅在副本上测试过 rebuild，工作母库尚未写入。

详细事实、限制和精确 `NEXT ACTION` 只维护在 [`AGENTS.md`](../AGENTS.md)，不要在这里再复制一套不断分叉的进度。

## 4. 接手规则

任何新窗口：

1. 读 `AGENTS.md`；
2. 再读 `README.md` 和需要的专项文档；
3. 按 `AGENTS.md` 的 `CURRENT MISSION / NEXT ACTION` 继续；
4. 未完成只读核验前，不删私有原件、不改名、不写 SQLite；
5. 实质阶段结束前必须把结果和下一步写回 `AGENTS.md`；
6. 架构、数据口径、发布规则变化时再同步更新 README/HANDOFF；
7. Git 改动走分支 → PR → CI → main，不直接把高风险变更硬写 main。

## 5. 禁止事项

不得提交私有 PDF/SQLite/OCR 到 GitHub；不得手改发布包；不得为了界面整洁重编号稳定 ID；不得按标题相似直接删法规/隐患；不得把“最新发布”自动等同“当前适用”；不得重新创建多个 final/latest/日期版交接文件。
