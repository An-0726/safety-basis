# 主线未出现在工作簿的 78 条 hazard

日期：2026-09-11  
对照快照：远端 `main`，`f0acc76ef4813f5e684378dc3252ed1708fbebcf`

逐条读取结果：远端 `knowledge/hazards` 共 712 条，工作簿覆盖 634 条，交集 634 条，主线独有 78 条。

- 78/78 的 `lifecycle` 明确为 `superseded`。
- 78 条没有额外的 `status`、`reviewStatus`、`publishable` 或 `stage` 字段值。
- 关系字段进一步核对：56 条有 `mergedInto`，21 条有 `replacedBy`，1 条没有显式替代/合并目标。
- 56 条 `mergedInto` 目标均存在于远端树；21 条记录共列出 50 个 `replacedBy` 目标，目标均存在于远端树，其中 46 个目标位于工作簿，4 个目标不在工作簿。
- 因此，这 78 条不是当前工作簿遗漏的 active hazard；但替代/合并关系仍属于来源元数据，不能仅据此自动删除、恢复或重建记录。
- 该结果解释了主线 knowledge 的 712 条来源 hazard 与工作簿 634 条之间的数量差异之一；它不单独解释 manifest 的 632/637 发布计数差异。

完整 78 条 ID、标题、分类、关系字段和远端路径见同目录 `main_only_hazards_relationships_20260911.json`；原始字段盘点见 `main_only_hazards_review_20260911.json`。本次没有删除、恢复、合并或修改这些记录。
