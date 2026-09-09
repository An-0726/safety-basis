# 数据架构第一阶段验收

日期：2026-09-09。工作分支：`data-verify-batch-003`。

第一阶段架构已形成完整闭环。内容核验仍会持续，但新增来源、整理、去重、核验和网站构建不再需要修改网站 JSON，也不依赖某一份 Excel 的列布局或固定行数。

## 权威数据与目录

```text
source/imports/                 任意多个新 Excel、CSV、旧 JSON；私有
source/archive/<sha256>/        不可变原件；私有
source/staging/intake.sqlite3   原始行、导入批次、候选和错误；私有
source/master/safety.sqlite3    唯一正式知识母库；私有
source/library/                 法规原件和全文索引；私有
source/exchange/                多 Sheet Excel 工作副本；私有
source/proposals/               待审提案与回执；私有
source/mappings/                多布局字段映射与自动路由；入 Git
source/schemas/                 母库 DDL、交换契约和显示字典；入 Git
source/releases/<releaseId>/    只含已通过门禁的静态网站包；入 Git
source/releases/site-selection.json  CI 当前检查的候选发布包；入 Git
```

SQLite 保存 `hazards`、`laws`、`law_versions`、`clauses`、`links`、`sources`、`source_rows`、`provenance`、`evidence`、`verification` 及追加式审计。法规身份和法规版本分开，同一法规只建一个身份；同一版本的同一条款只建一条。隐患与条款是多对多关系。

## Excel 工作入口

`exchange.py export` 从最新母库生成工作簿。可编辑 Sheet 是“隐患库、法规库、法规版本、条款库、依据关联”；“隐患标签、法规别名、替代关系、原始来源、核验记录、来源关联、来源定位、字典”只读。显示字典由 `source/schemas/dictionaries.json` 统一维护。

工作簿不是第二份母库。编辑行必须带稳定 ID、基础 revision 和 `update` 操作；回收先生成差异提案，再在单个事务中应用。内容变化自动增加 revision 并使旧核验失配。新增实体、合并和身份修订使用各自的受控提案接口，不能靠插行或改状态绕过规则。

## 多来源导入与去重

`imports.py` 使用 `source/mappings/registry.json` 按 Sheet 和表头唯一匹配布局。新布局只增加 mapping。每个文件先以 SHA-256 归档；每个原始行保留文件、Sheet、行号或 JSON Pointer。相同文件和相同解析配置重复导入幂等。

去重分三层：文件哈希去重、候选规范化哈希聚合、知识实体相似召回后审阅合并。文本相似只产生建议。合并保留 survivor ID、旧 ID 去向、全部来源和审计记录。现场“符合”保留原事实、隐患描述为空；法规依据和原文照常保留，通用隐患模板另行派生。

## 核验与发布

核验分别作用于法规身份、法规版本、条款、隐患和依据关联。通过记录绑定对象 revision、依赖哈希、官方证据及复核日期。母库允许长期存在“原始数据、待整理、待核验、已核验、已失效”；发布包中待核验始终为零。

已公布但尚未实施的版本可进入独立法规目录，并显示实施日期；它在实施前不能支撑当前隐患。法规废止或版本变化只修改法规版本和替代关系，门禁沿 `version → clause → link → hazard` 统一计算影响。

生成候选网站包：

```text
python tools/pipeline/manage.py site --as-of YYYY-MM-DD --output source/releases/NEW_RELEASE
python tools/pipeline/manage.py verify-site --output source/releases/NEW_RELEASE
```

审阅私有 `<release>.review.json` 的新增、撤下和阻断差异后，更新 `source/releases/site-selection.json` 中的目录名和 `releaseHash`。`prepare_site.py` 会重新校验文件集合、哈希和发布当日门禁，只把选定公开包复制到新的托管目录。GitHub Actions 在分支和 PR 上构建可下载 artifact；正式 Pages 发布仅在 `main` 上手动运行工作流，合并本身不会自动上线。

当前候选是 `reviewed-20260909-r4`：121 个已核验法规版本、25 个已核验隐患、21 个被公开隐患引用的条款、25 个关联；15 部全文、106 个官方入口。其发布差异仍需审阅，`deployed=false`，生产网站尚未切换。

## 以后新增数据

1. 把文件放入 `source/imports/`。
2. 运行统一导入，查看未匹配布局、解析错误和去重建议。
3. AI 分组整理候选并生成入库、合并或修订提案；审阅后应用到母库。
4. 按法规版本复用官方证据，分别核验版本、条款、隐患和关联。
5. 一条 `manage.py site` 命令生成网站候选包；审阅差异并更新选择文件。
6. 分支 CI 验证；合并后在 `main` 手动发布。

`content/`、旧 batch、旧 ID 和旧 `data/` 暂时冻结保留，用于来源追溯、迁移对账和生产回退。长期淘汰人工编辑 `content/*.json`、`data/*.json`、`search-index.json`、`law-index.json` 的流程；待生产切换稳定后再归档旧构建入口，不删除历史数据。

内容层剩余工作不是架构缺口：法规候选仍有待核、检查候选仍需批量拆解和适用性核验。它们可以按法规版本和候选分组委派，子任务只产出提案，正式母库由单一提交器串行写入。
