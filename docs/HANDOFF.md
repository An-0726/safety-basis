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
- 1264个新ID没有直接写入正式知识源，已全部生成处置结果：309条已定位到现有知识条款并生成315条关联提案，856个仅匹配法规目录，90个依据名称仍需定位，7个重复/同名合并审查项。
- 这1264条现在已登记为 `knowledge/hazards/` 中的 `lifecycle=proposed` 提案实体；它们不进入当前公开发布，待条款、适用性和关联审核完成后再转为active。
- 现有实体更新后已刷新审核哈希和关联上下文；当前发布包哈希见 `source/releases/site-selection.json`。
- 提案和处置文件位于 `source/proposals/excel-20260913/`，该目录Git忽略。新候选必须完成条款定位、关联审查和发布门禁后才能入库。
