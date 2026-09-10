# V4 Gate Report（2026-09-10）

## 当前判定

本报告已按 `chat-v4` 最新候选发布包重新同步。候选包仍为非生产状态，production / GitHub Pages 均未切换。

## 当前知识与候选包规模

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- requirements: 75
- Link review: 666 verified / 19 rejected / 0 pending

## Shared chained gate

共享链式发布判定由 `tools/v4/release_gate_core.py` 提供，并由 `build_release.py`、`strict_release_audit.py`、`gate_v4.py` 共用。

最新候选包 `source/releases/v4-candidate-20260910/release.json` 记录：

- publishableHazards: 596
- notPublishableHazards: 116
- eligibleHazards: 596
- eligibleLinks: 666
- production: false
- sourceStateHash: `6b0adf8953769c5aa84b017ff9b0160ea8b0baddaf1bc35f87b2864c09cee9a7`

## Gate verdict

- STRUCTURAL: PASS
- CONTENT: PASS
- APPLICABILITY: PASS
- VERSION: PASS
- EVIDENCE: PASS
- RELEASE: PASS

`gate_v4.py` 的 CONTENT / APPLICABILITY 已与共享链式判定核心对齐，不再使用旧版“所有 verified review 必须各自直接挂 evidenceRefs”的独立判定方式；link review 可以沿 clause → lawVersion → law 的已核验证据链复用证据。

## 发布边界

当前结论仅表示候选 V4 数据通过现有发布门禁，可进入最终验收；不等于已经获得生产切换授权。

仍然禁止在未获用户明确批准前：

- 修改 `main`
- 切换 production
- 切换 GitHub Pages 正式数据源
- 以候选 release 覆盖现有生产 release

## 终审注意事项

- `knowledge/manifest.json` 的 counts 已同步到当前知识规模，但其 `scope` 叙述仍保留早期 68 laws / 662 hazards / 181 links 等旧数字，需要后续做文档一致性清理。
- 最终生产切换前应再次以当时真实 HEAD 运行完整 validator / gate / strict audit，并确认 candidate 的 `sourceStateHash` 与待发布知识状态一致。
