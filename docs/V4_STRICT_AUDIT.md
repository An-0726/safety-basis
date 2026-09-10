# V4 Strict Release Audit Report

> 最后同步：2026-09-10
> Phase 16 最终验收状态：`REVIEW_REQUIRED`

## 说明

本文件原先记录的是较早的 74 laws / 85 clauses / 209 links / 162 eligible hazards 快照，已经不能代表当前 V4 知识规模。该旧统计已停止作为当前验收依据。

## 上一稳定候选的严格审计结果

在 `knowledge/manifest.json` 本轮元数据修正之前，最新稳定 candidate 的共享链式严格审计结果为：

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- releaseBlockers: 0
- eligibleHazards: 596
- eligibleLinks: 666
- link review: 666 verified / 19 rejected / 0 pending
- strict verdict: PASS
- candidate `sourceStateHash`: `6b0adf8953769c5aa84b017ff9b0160ea8b0baddaf1bc35f87b2864c09cee9a7`
- production: false

## 为什么当前不能直接继续写 PASS

`tools/v4/build_release.py` 对 `knowledge/**/*.json` 全量计算 `sourceStateHash`。Phase 16 本轮已经修正 `knowledge/manifest.json` 的 `migrationPhase` 和 `scope`，因此上一稳定候选的 hash 只对应修改前知识树。

这不代表新发现了法规内容错误，也不代表原 strict audit 失效；它表示**最终候选必须重新构建并重新执行严格审计**，才能形成当前 HEAD 对应的最终验收证据。

## 最终严格审计通过条件

最终 candidate 稳定后必须确认：

1. `releaseBlockers == 0`；
2. 所有公开 hazard 都至少有一条通过共享链式 Gate 的 direct/fallback link；
3. 不存在当前公开链引用 repealed/upcoming/unknown LawVersion；
4. rejected/pending/supporting-only 链不会被错误当作发布依据；
5. candidate `sourceStateHash` 与当前 `knowledge/**/*.json` 一致；
6. `candidate=true` 且 `production=false`；
7. 普通 Gate 与 Strict Gate 对 CONTENT/APPLICABILITY/RELEASE 的结论一致。

## 当前结论

- 历史稳定候选：`PASS`
- Phase 16 当前最终候选：`REVIEW_REQUIRED — rebuild + rerun required`
- production：未切换

最终验收总表见 `docs/V4_FINAL_ACCEPTANCE.md`。
