# V4 Gate（候选发布门禁）

状态：**机制已实现（tools/v4/gate_v4.py），2026-09-10 对 chat-v4 执行**
分支：chat-v4（未切 production）

## 1. Gate 分级

| 级别 | 含义 | 通过条件 |
|---|---|---|
| STRUCTURAL | 结构通过 | check_catalogue / check_requirements / check_review_binding 全绿 |
| CONTENT | 内容通过 | 179 link 全量已审；review 统计可解释；无未处理的结构性质量问题 |
| APPLICABILITY | 适用性通过 | 每条 link 的 role（direct/supporting/fallback）与 clause 覆盖一致 |
| VERSION | 版本通过 | 现行 lawVersion 已确认；被替代版本有 succession；无陈旧标准引用（conditions） |
| EVIDENCE | 证据通过 | evidenceRefs 可解析且与 clause 法规一致（scan_evidence_exact=0） |
| RELEASE | 发布通过 | candidate release 构建成功；V3/V4 差异报告完成；search 回归通过 |

## 2. 不得进入 verified production candidate 的情形（拒绝清单）

- dangling refs（link->hazard/clause、clause->lawVersion、link->requirementId）
- hash stale（review 绑定失配、requirement canonicalHash 失配）
- 无 evidence 的关键结论（verified 但 evidenceRefs 为空）
- applicability pending（未完成专业复核的 link 声称 verified）
- current lawVersion 未确认（effectiveDate 空且未标注 pending）
- 错误 jurisdiction（scope/jurisdictionCode 与法规不符）
- 失效 Clause（lawVersion=superseded 仍被 direct link 引用）
- composite hazard 未处理却声称 direct verified
- 仅靠关键词相似度生成的 link

## 3. 执行

```
python tools/v4/gate_v4.py
```

输出 gate report 到 stdout 与 docs/V4_GATE_REPORT.md。
RELEASE 级为人工确认项（Phase 17 最终由用户决策是否切 production）。
