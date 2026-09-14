# 待审核候选处理手册

## 候选是什么

`lifecycle=proposed` 的候选不是废数据，也不是已核验法规依据。它表示隐患字段已经进入库并可以检索，但正式依据链还没有完成，或者原记录需要合并、补版本、补条款或补证据。

网页上的“待审核候选”必须按下面的状态处理：

- `workbook_revised_pending_clause_rebind`：新版整改表已经改过字段，但还没有绑定精确的官方条款、原文证据和适用性审核。
- `basis_catalog_only`：只有法规题录，没有具体条款原文。
- `basis_name_unresolved`：法规身份、编号或版次还不能确定。
- `same_title_review`：与已有隐患同名或高度相似，需要先合并判断。

## Chat接手后的固定流程

1. 读取候选隐患的 `id`、`proposalStatus`、`sourceRow`、直接依据和适用条件。
2. 从 `knowledge/law-versions/` 和 `source/publication/law-index.json` 确认标准编号、版次、发布日期、实施日期和替代关系。
3. 在 `source/library/fulltext.sqlite3` 或获准的官方文本中定位具体条款；OCR只能用于定位，正式引用必须回看原PDF或官方原文。
4. 创建或复用 `knowledge/clauses/` 条款，保存逐字 `quote`、`articlePath`、`lawVersionId` 和来源。
5. 创建 evidence、clause review、hazard review 和 direct link review；核对隐患对象、条款义务、整改动作和适用范围。
6. 只有链式门禁通过后，才把候选转为 `lifecycle=active`；否则继续保持候选并写明缺口。
7. 运行 `validate_all.py`、`strict_release_audit.py`、`verify_unified_bundle.py`，再重建发布包。

## 不能做的事

- 不能把“依据条款要点（修订，非原文摘录）”当成法规原文。
- 不能仅凭标准名称、搜索摘要或文件名生成正式条款。
- 不能把尚未实施的新标准标成“现行有效”；可以按用户要求登记为最新版本，但必须保留 `upcoming` 状态。
- 不能把候选数量直接报成已核验数量。

当前新版整改批次：1926条在线，其中1409条正式、517条候选。候选详情和状态在发布包的 hazard 记录中，当前处理逻辑由 `tools/v4/build_unified_release.py` 和本手册共同定义。
