# V4 Phase 16 Final Acceptance Inventory

> Generated from the current `knowledge/` tree by `tools/v4/final_acceptance_inventory.py`.

## Summary

```json
{
  "counts": {
    "laws": 79,
    "lawVersions": 79,
    "clauses": 129,
    "hazards": 712,
    "links": 781
  },
  "eligibleHazards": 643,
  "eligibleLinks": 743,
  "requirementReviewStatus": {
    "verified": 75
  },
  "linkReviewDecision": {
    "verified": 743,
    "rejected": 25,
    "superseded": 13
  },
  "supportingVerifiedLinks": 11,
  "activeHazardsWithoutQualifyingLink": 1,
  "supersededOrMergedHazards": 68
}
```

## Active hazards without qualifying direct/fallback link

These remain outside the public release until individually adjudicated. They are not automatically errors, but Phase 16 must classify them before final acceptance.

1. `H_1F19FA1B951D46C1971E9B59B4` | 安全管理 | 门窗,未朝外开启

## Verified supporting links

1. `K_2933E4BAE83454CB7EAB5C` -> `H_C1CE3A649721387F1FC0F7BE` | 粉尘废屑未冷却至常温即入库存放，或不同种类混装、与氧化物/过氧化物/酸/爆炸品/易燃物品同场所存放
2. `K_2D5D8E4F99C3E4588904DC` -> `H_46A4349273C34D2992F88B202F` | 危险化学品试剂间内可燃气体报警器接线处护套线腐蚀脱落,未采用防爆挠性管连接
3. `K_2DC831138A211E52DEEEFD` -> `H_6D5EBB4E642F489C9717AED728` | 危险化学品库房内使用非防爆接线盒
4. `K_4E50636899132D39A208CE` -> `H_B62D5B7BB22E4F398116A27DBD` | 对有视线障碍的灭火器设置点,未设置指示其位置的发光标志
5. `K_732967C834ACF1013A4F05` -> `H_54D18AD4CE504AD2A8F3967B1F` | 喷漆房内的可燃气体报警仪电源线路不符合防爆规范
6. `K_83571F5B278BC9BFECC131` -> `H_560D75081D1F4B42BEB642811A` | 四楼危险化学品试剂间内电气线路未敷设在钢管内
7. `K_9E8D807315E740BAC846B6` -> `H_8941ECA792B945179F517D5278` | 车间内一处灭火器前有杂物遮挡
8. `K_B023B253B1A5FED1781FC0` -> `H_409EF7D84AB8469C91AEC3385C` | 标志贮存的化学危险品,未有明显的标志,标志,未符合GB190的规定。同一区域贮存两种或两种以上不同级别的危险品时,未按最高等级危险物品的性能标志
9. `K_B610A592D9545D785B5273` -> `H_4164E28510AC475EA9FB48337C` | 高温室缺少“当心烫伤”安全警示标志
10. `K_B8ADE8F014895A81A0DB0C` -> `H_7C95508E54324EB7971918F1E5` | 车间内部分电箱未张贴安全警告标志
11. `K_FB1036509AD15909DCBDDC` -> `H_6706FA04BB344FA59ED6251058` | 生产设备易发生危险的部位未有安全标志。安全标志的图形、符号、文字、颜色等均必须符 合 GB2893 、 GB2894 、 GB6527.2 、GB15052 等标准规定

## Superseded / merged hazards

Count: 68. These are retained for traceability and should remain excluded from the current public projection unless lifecycle review finds a data error.
