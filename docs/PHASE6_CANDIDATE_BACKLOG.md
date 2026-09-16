# PHASE 6 候选证据回绑 backlog

> 核验基准日：2026-09-16。本报告是 `knowledge/` 的机械状态盘点，不是法规现行性结论，也不执行候选转正。
> 所有记录继续保持 `lifecycle=proposed`；正式转正必须另行完成法规身份、适用版本、具体条款、逐字原文、原始证据和适用性审核。

## 盘点结论

- 候选总数：**519**（目标集内 512，目标集外 7）。
- **513** 条没有任何现有关联；**6** 条只有已拒绝关联（共 8 条）。
- hazard review：缺失 **346**，已核验 **169**，已拒绝 **4**。
- 本批没有任何记录被标记为可直接转正；本工具没有修改 `knowledge/`、SQLite、私有母库或发布包。

## 按 backlog 阶段

| 机械分组 | 数量 |
| --- | --- |
| catalog_only_no_qualifying_link | 7 |
| non_target_scope_review_no_qualifying_link | 1 |
| rejected_links_need_rebind | 6 |
| workbook_revised_no_qualifying_link | 505 |

分组含义：

- `workbook_revised_no_qualifying_link`：工作簿修订候选，尚未建立 direct/fallback 关联。
- `catalog_only_no_qualifying_link`：只有法规题录/入口线索，尚未完成身份、版本、条款和关联链。
- `non_target_scope_review_no_qualifying_link`：目标外候选，尚无关联，先做范围复核。
- `rejected_links_need_rebind`：现有关联已被拒绝，须按拒绝原因重绑或拆分对象。

## 按 proposalStatus

| proposalStatus | 数量 |
| --- | --- |
| basis_catalog_only | 7 |
| knowledge_extra_non_target_pending_scope_review | 7 |
| workbook_revised_pending_clause_rebind | 505 |

## 按 hazard review 状态

| 状态 | 数量 |
| --- | --- |
| hazard_review_missing | 346 |
| hazard_review_rejected | 4 |
| hazard_review_verified | 169 |

## 目标外 7 条候选

| ID | 标题 | 分组 | hazard review | 关联数 |
| --- | --- | --- | --- | --- |
| H_02FEFD347E114E1E979C9589AF | 生产经营单位未急预案分为综合应急预案、专项应急预案和现场处置方案 | rejected_links_need_rebind | hazard_review_rejected | 1 |
| H_0647B65088564B789D64080EF1 | 按照国家标准、行业标准配置消防设施、器材,设置消防安全标志。 | rejected_links_need_rebind | hazard_review_rejected | 1 |
| H_1F19FA1B951D46C1971E9B59B4 | 门窗,未朝外开启 | rejected_links_need_rebind | hazard_review_verified | 1 |
| H_23D109AF79FF0519BCD1837EC6_1 | 未尽量选用自动化程度高的设备 | non_target_scope_review_no_qualifying_link | hazard_review_verified | 0 |
| H_3A5DEC6C74244A949CE3BC9A42 | 空压机房内配电柜柜门未保持常闭状态 | rejected_links_need_rebind | hazard_review_verified | 1 |
| H_5B89D7164D2C4B6E983663B009 | 具备与本单位所从事的生产经营活动相未的安全生产知识和管理能力 | rejected_links_need_rebind | hazard_review_rejected | 2 |
| H_6E7E9CD077AD4918962EBA6EAE | 当不可避免时,必须具有可靠的防洪、排涝措施 | rejected_links_need_rebind | hazard_review_rejected | 2 |

## 下一批执行边界

1. 优先从 `workbook_revised_no_qualifying_link` 中按法规/设备/作业主题分批，逐项回到官方原文或合法保存的原始证据。
2. 对 `rejected_links_need_rebind` 先读取 `reasonCodes` 和上下文，必要时修订隐患对象或拆分对象；旧 rejected 记录不删除。
3. 每个候选必须同时满足 hazard review、law/lawVersion、clause、evidence、link applicability 的门禁后，才可另开转正批次。
4. 任何条款号、版本效力、替代关系或官方原文无法核准时，保持 `proposed` 并标记 `待核`。

机器明细见 [`docs/phase6-candidate-backlog.jsonl`](phase6-candidate-backlog.jsonl)。
