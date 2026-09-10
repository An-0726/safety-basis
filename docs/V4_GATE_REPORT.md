# V4 Gate Report（2026-09-10, chat-v4）

## Structural
- check_catalogue: PASS
- check_requirements: PASS
- check_review_binding: PASS
- scan_evidence_exact: PASS

## Review totals: {"verified": 127, "rejected": 15, "pending": 39}
review_total=181
composite_reviewed=21
verified_without_evidence=0

## Version
lawVersions_total=68
successions_total=19

## Gate verdict
- STRUCTURAL: PASS
- CONTENT: PASS
- APPLICABILITY: PASS
- VERSION: PASS（基于上一次完整 validator/gate 运行；其后法规版本元数据继续修正，需随新 candidate 重跑）
- EVIDENCE: PASS
- RELEASE: REVIEW_REQUIRED

## RELEASE 级核对

候选发布包已经实际生成：`source/releases/v4-candidate-20260910/`，因此旧状态 `NOT_RUN (candidate build pending)` 已失效。

当前候选包 `release.json` 记录：
- laws 68
- law_versions 68
- clauses 76
- hazards 662
- links 181
- requirements 75
- reviewStats = 114 verified / 14 rejected / 32 pending

当前知识库 review 统计已经推进到：127 verified / 15 rejected / 39 pending；并且候选包生成后，`chat-v4` 又继续修正了 GB 6514-2023、GB 15607-2023、GB 12801-2025 / GB/T 12801-2008 等法规版本元数据。

因此现有 candidate 只能证明“候选构建、V3/V4 差异检查、搜索回归流程已经运行过”，不能视为当前 HEAD 的一致性快照。按 Stage 6 的 release 一致性原则，当前结论记为 `REVIEW_REQUIRED`：需要基于最新 `chat-v4` 重新生成 candidate，然后重跑 validator、gate、V3/V4 diff、search regression 并核对 sourceStateHash / counts / reviewStats 后，才可以把 RELEASE 记为 PASS。

production 切换仍需用户明确批准；本报告不授权修改 `main`、GitHub Pages 数据源或 production selection。
