# V4 Phase 16 Final Acceptance Inventory

> 生成基线：`chat-v4` commit `0a7673149c012cf39238e019c05626ef11e8c285`
> 生成方式：`tools/v4/final_acceptance_inventory.py`
> CI run：`34456894682`
> artifact：`10143845362` / `v4-final-acceptance-0a7673149c012cf39238e019c05626ef11e8c285`
> 当前用途：Phase 16 终审库存，不等同于生产发布批准。

## Summary

```json
{
  "counts": {
    "laws": 75,
    "lawVersions": 75,
    "clauses": 88,
    "hazards": 712,
    "links": 735
  },
  "eligibleHazards": 645,
  "eligibleLinks": 716,
  "requirementReviewStatus": {
    "verified": 55,
    "pending": 20
  },
  "linkReviewDecision": {
    "verified": 716,
    "rejected": 19
  },
  "supportingVerifiedLinks": 11,
  "activeHazardsWithoutQualifyingLink": 0,
  "supersededOrMergedHazards": 67
}
```

## 本轮关键纠正

上一版库存曾显示 `eligibleHazards=596`、`eligibleLinks=666`、`activeHazardsWithoutQualifyingLink=49`。Phase 16 复核发现这不是知识树真实缺口，而是 `tools/v4/release_gate_core.py` 的 review sidecar 索引错误：新式 review 同时具有自身 `id=RV_*` 与被审核实体 `entityId` 时，旧加载逻辑优先按 review 自身 id 建索引，而发布门禁后续按 hazard/link/clause/law 的实体 id 查找，导致一批实际已核验的 review 被误判为缺失。

commit `0a767314...` 将普通实体与 review 的加载规则分离：普通实体继续按自身 `id`；review 专门按 `entityId` 建索引，旧 sidecar 无 `entityId` 时才以文件名兜底。修复后全量 V4 Final Acceptance CI 成功，机器库存恢复为 645 个 eligible hazards、716 个 eligible links，当前 active hazard 中没有因“缺 qualifying direct/fallback link”被排除的条目。

这项纠正只修复门禁读取逻辑，没有修改 `knowledge/**/*.json`，没有新增或自动通过任何法规依据，也没有修改 `main` 或生产网站。

## Active hazards without qualifying direct/fallback link

当前机器链式门禁结果：**0**。

注意：`0` 只表示当前 645 个 active hazard 均至少存在一条通过技术链式 Gate 的 direct/fallback link；它**不等于 645 条隐患的法规适用性已经完成最终人工专业终审**。Phase 16 仍必须继续处理下面的语义复核队列，尤其是过泛的 fallback、地方频次义务、旧标准引用和替代关系，禁止因为机器 Gate 全绿而自动宣布法规终审完成。

## Verified supporting links

当前仍有 11 条 verified supporting link。`supporting` 只能作为补充说明，不能单独使 hazard 获得发布资格：

1. `K_2933E4BAE83454CB7EAB5C` → `H_C1CE3A649721387F1FC0F7BE`
2. `K_2D5D8E4F99C3E4588904DC` → `H_46A4349273C34D2992F88B202F`
3. `K_2DC831138A211E52DEEEFD` → `H_6D5EBB4E642F489C9717AED728`
4. `K_4E50636899132D39A208CE` → `H_B62D5B7BB22E4F398116A27DBD`
5. `K_732967C834ACF1013A4F05` → `H_54D18AD4CE504AD2A8F3967B1F`
6. `K_83571F5B278BC9BFECC131` → `H_560D75081D1F4B42BEB642811A`
7. `K_9E8D807315E740BAC846B6` → `H_8941ECA792B945179F517D5278`
8. `K_B023B253B1A5FED1781FC0` → `H_409EF7D84AB8469C91AEC3385C`
9. `K_B610A592D9545D785B5273` → `H_4164E28510AC475EA9FB48337C`
10. `K_B8ADE8F014895A81A0DB0C` → `H_7C95508E54324EB7971918F1E5`
11. `K_FB1036509AD15909DCBDDC` → `H_6706FA04BB344FA59ED6251058`

## Superseded / merged hazards

当前共 **67** 条。它们保留用于历史追溯，不进入当前公开投影，除非后续 lifecycle 复核发现数据错误。

## Technical acceptance snapshot

commit `0a767314...` 的 V4 Final Acceptance CI：

- integrated validator: PASS
- candidate build: PASS
- six-stage Gate: STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE 全 PASS
- strict audit: PASS
- release blockers: 0
- search regression: PASS
- deterministic candidate build: PASS
- knowledge mutation check: PASS
- candidate-only boundary: PASS (`candidate=true`, `production=false`)
- eligible hazards: 645
- eligible links: 716
- candidate sourceStateHash: `545a828e653fe634754d50699c7e321448dbac25396500b15c1a015f1a0e0e5f`

## Remaining semantic queues

当前机器发布链已经完整，但 Phase 16 尚未完成。仍需人工专业终审：

- pending Requirements: 20
- stale old-standard refs in hazard fields: 14
- partial-replaced standard hazard hits: 12
- obligation-restatement candidates: 11
- links to merged hazards: 9
- 江苏地方具体义务：H046（主要负责人季度全面检查）、H048（年度全面风险辨识）等需核直接地方条款，不能仅以泛化全国法替代具体频次义务
- H049 事故后组织抢救、及时如实报告应核精确直接法条，不能由应急预案义务替代
- H043 仓储消防培训应继续确认是否存在更直接的消防专项依据；现有安全生产教育培训条款不能因为技术 Gate 通过就自动视为最佳依据
- H052-H055、H058、H065、H067、H069、H079 等高价值条目继续做现行版本与适用性专业终审

## 终审原则

机器 Gate 只回答“当前数据链是否满足既定发布规则”，不替代法规专业判断。下一阶段仍按隐患逐条检查监管对象、适用范围、版本时效、条款义务、直接程度和地方/国家关系；证据不足时保持待复核，不为提高覆盖率强行通过。
