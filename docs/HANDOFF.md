# 交接说明

新接手者先读根 `README.md`，然后只从以下入口工作：

- 改知识关系：`knowledge/`
- 改公开目录或公开全文：`source/publication/`
- 处理本地原件与全文：`source/library/`
- 构建公开站点：`tools/v4/build_unified_release.py`
- 验证发布包：`tools/v4/verify_unified_bundle.py`

不要从旧发布目录、根 `data/`、临时报告或Excel导出反向覆盖正式知识源。不要将私有PDF、企业资料或受版权限制全文提交Git。

本地迁移期备份位于：

`D:\ESH\ESH_Codex\archive\safety-basis-private-backup-20260913\`

该目录包含旧发布包、旧说明、迁移报告、临时工作文件和原 `source/exchange/`。它不是运行依赖，仓库在没有该目录时也必须能构建和验证。

## 2026-09-13 Excel回灌进度

`隐患库最终修订交付版_20260913.xlsx` 已完成第一阶段处理：

- 250个已存在于 `knowledge/hazards/` 的隐患已应用字段更新；Excel“场所”写入适用条件，原有 `places` 检索标签保留。
- 1264个新ID已全部写入 `knowledge/hazards/` 并生成处置结果：私有全文/条款候选388条、私有全文依据311条、法规目录命中475条、依据名称待核验83条、同名复核5条、重复/合并2条；关联提案315条，其中2条尚未解析。
- 其中已有969条完成正式条款、全文/目录证据和关联审核，已转为 `lifecycle=active`；剩余295条以 `lifecycle=proposed` 的“待审核候选”状态进入当前公开发布包，可搜索、可查看，但不能直接作为正式依据。
- 现有实体更新后已刷新审核哈希和关联上下文；当前发布包哈希见 `source/releases/site-selection.json`。
- 提案和处置文件位于 `source/proposals/excel-20260913/`，该目录Git忽略。新候选必须完成条款定位、关联审查和发布门禁后才能入库。
