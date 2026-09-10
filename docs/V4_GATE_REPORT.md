# V4 Gate Report（2026-09-10）

## 当前判定

**FINAL-ACCEPTANCE STATUS: REVIEW_REQUIRED**

原因不是发现新的内容性 blocker，而是 Phase 16 收口过程中已经修改 `knowledge/manifest.json` 的 Phase/scope 元数据。`tools/v4/build_release.py` 的 `sourceStateHash` 对 `knowledge/**/*.json` 全量计算，因此此前已通过的 candidate 现在只能作为“上一稳定候选快照”，必须在最终知识状态稳定后重新 build 并重跑 Gate/Strict Audit，才能重新声明最终 PASS。

生产状态仍保持：`production=false`，GitHub Pages 正式数据源未切换。

## 当前知识规模

`knowledge/manifest.json` 当前 counts：

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- requirements: 75
- evidence: 567
- successions: 23

## 上一稳定候选快照

路径：`source/releases/v4-candidate-20260910/release.json`

该候选生成时记录：

- publishableHazards: 596
- notPublishableHazards: 116
- eligibleHazards: 596
- eligibleLinks: 666
- Link review: 666 verified / 19 rejected / 0 pending
- sourceStateHash: `6b0adf8953769c5aa84b017ff9b0160ea8b0baddaf1bc35f87b2864c09cee9a7`
- candidate: true
- production: false

当时共享链式 Gate 结果：

- STRUCTURAL: PASS
- CONTENT: PASS
- APPLICABILITY: PASS
- VERSION: PASS
- EVIDENCE: PASS
- RELEASE: PASS

这些 PASS 是有效的历史验收证据，但由于知识目录之后发生了 manifest 元数据变更，**不能直接作为当前最终候选的 sourceStateHash 证明**。

## Shared chained gate

共享链式发布判定由 `tools/v4/release_gate_core.py` 提供，并由 `build_release.py`、`strict_release_audit.py`、`gate_v4.py` 共用。

普通 Gate 与 Strict Gate 的 CONTENT/APPLICABILITY 已统一使用共享链式判定，不再要求每个 verified link review 自己重复挂一份 evidenceRefs；允许沿 clause → lawVersion → law 的已核验证据链复用证据。

## Phase 16 最终 Gate 要求

在最终知识树不再发生修改后必须执行：

1. V4 validator；
2. candidate build；
3. `gate_v4.py`；
4. strict release audit；
5. 再次确认 candidate `sourceStateHash` 与当前 `knowledge/**/*.json` 一致；
6. 再做一次确定性构建比对；
7. 确认 `candidate=true`、`production=false`。

只有上述结果全部满足，本文档的最终状态才能从 `REVIEW_REQUIRED` 改回 `PASS`。

## 发布边界

在用户明确批准前仍然禁止：

- 修改 `main`
- 切换 production
- 切换 GitHub Pages 正式数据源
- 以候选 release 覆盖生产 release
- 修改 V3 冻结 SQLite
- force push

最终总验收由 `docs/V4_FINAL_ACCEPTANCE.md` 统一管理。
