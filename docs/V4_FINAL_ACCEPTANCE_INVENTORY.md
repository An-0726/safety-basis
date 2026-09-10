# V4 Phase 16 Final Acceptance Inventory

> 生成基线：`chat-v4` commit `cd29037630c9f52688692ab3f9212bd7dc9fde9d`
> 生成方式：`tools/v4/final_acceptance_inventory.py`
> CI run：`34453384587`
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
  "eligibleHazards": 596,
  "eligibleLinks": 666,
  "requirementReviewStatus": {
    "verified": 55,
    "pending": 20
  },
  "linkReviewDecision": {
    "verified": 716,
    "rejected": 19
  },
  "supportingVerifiedLinks": 11,
  "activeHazardsWithoutQualifyingLink": 49,
  "supersededOrMergedHazards": 67
}
```

说明：716 条 link review 的 `verified` 是 review 层统计；真正通过完整 hazard → link → clause → lawVersion → law 链并可参与发布判定的 link 为 666 条。不得混用两个口径。

## Active hazards without qualifying direct/fallback link

这些项目当前均不进入公开 release。它们不是自动判定为错误，而是 Phase 16 必须逐条做专业归类：补直接依据、保留为 pending/backlog、转 supporting、确认非隐患/历史项，或在证据不足时继续排除。禁止为了提高覆盖率批量建链。

1. `H035` | 专项安全与EHS | 有机废气治理系统与主体装置之间未设置阻火器（防火阀）
2. `H038` | 专项安全与EHS | 废气治理风机选型与处理介质不匹配
3. `H042` | 安全管理 | 建设项目安全设施施工单位资质或同步施工不符合要求
4. `H043` | 消防安全 | 仓储场所未开展消防安全教育培训
5. `H046` | 安全管理 | 江苏生产经营单位主要负责人未按要求组织季度安全生产全面检查
6. `H048` | 安全管理 | 江苏生产经营单位主要负责人未按要求组织年度全面安全风险辨识
7. `H049` | 应急与事故管理 | 生产安全事故发生后主要负责人未及时组织抢救并如实报告
8. `H052` | 消防安全 | 仓储物品与照明灯之间安全距离不足
9. `H053` | 消防安全 | 仓储物品与墙之间安全距离不足
10. `H054` | 消防安全 | 仓储堆垛与柱之间安全距离不足
11. `H055` | 消防安全 | 仓储堆垛之间安全距离不足
12. `H056` | 专项安全与EHS | 实验室气体管道完整性或检维修空间不符合要求
13. `H057` | 电气安全 | 粉尘场所配电线路敷设未防止积尘影响
14. `H058` | 消防安全 | 仓储场所在岗人员消防安全教育频次不足
15. `H059` | 消防安全 | 仓储场所防雷与接地系统设置或检测不到位
16. `H065` | 危险化学品与危险物质 | 易燃气体与助燃气体同库储存
17. `H067` | 消防安全 | 仓储场所消防重点岗位未接受专项消防培训
18. `H069` | 消防安全 | 库房堆垛顶部与楼板或屋顶间距不足
19. `H070` | 专项安全与EHS | 活性炭吸附床超温未报警或未联动降温
20. `H071` | 电气安全 | 电气作业前未熟悉作业环境并采取相应防护措施
21. `H076` | 专项安全与EHS | 喷漆室通风系统不符合安全要求
22. `H077` | 专项安全与EHS | 强酸、强碱等实验室未就近设置应急洗眼器或喷淋设施
23. `H078` | 专项安全与EHS | 危险废物产生单位未对相关工作人员开展培训
24. `H079` | 安全管理 | 建设项目初步设计阶段未同步开展安全设施设计
25. `H080` | 专项安全与EHS | 高风险实验室未形成独立防护单元或防火分隔不符合要求
26. `H_004D8F2994DD43D1A2F418386F` | 安全管理 | 门窗未向外开启
27. `H_01ADBFD09A994DCBA4FDF6B868` | 电气安全 | 用电产品的绝缘未符合相关标准规定
28. `H_02E90FC3EF2AC0B2A8FE6504` | 安全管理 | 危险化学品仓库未配备有专业知识的技术人员，库房及场所未设专人管理
29. `H_05248294EEDD496B9A57C50C91` | 电气安全 | 抛丸机区域电气不符合防爆要求
30. `H_052508D94A934DA88563BD06C0` | 安全管理 | 对生产中易产生静电的设备和管道未采取消除静电的措施
31. `H_05E3463E093546EF9631C3773D` | 电气安全 | 照明及各类电气设备未为防爆型
32. `H_06280C62983C4FB2837C0CF2BC` | 安全管理 | 机械设备安全防护装置未能将人员身体、手指、手臂和服装等与危险零件隔离
33. `H_07093A790D744FDBB7125B8AD3` | 消防安全 | 车间、铝粉危废库未配备铝金属专用灭火器材
34. `H_076F5EC8768049A3A3917ABB1D` | 应急与事故管理 | 建设工程卫生学评估及突发公共卫生事件应急救援预案要求未落实
35. `H_08C1576EE4824ED8BE0CDD56DF` | 总图与建筑 | 灭火器摆放不稳固或铭牌未朝外
36. `H_095F0B8A265A45FFAED1B3902F` | 消防安全 | 企业一组灭火器设置区域距离焊接明火地点较近且未采取安全措施
37. `H_0974E0DD140546B9943A71BC4A` | 安全管理 | 危险性较大的重要生产设备设计、制造和检验资质要求未落实
38. `H_0B44B29CA3794AEF82EC7CE4F5` | 安全管理 | 工业企业选址未避开自然疫源地
39. `H_0D7B747137B74DEEA766A4DA5E` | 危险化学品与危险物质 | 储漆室外未设置人体静电消除装置
40. `H_0D8FC0AC95BE4E09908AD3A154` | 涂装安全 | 调漆作业使用可以发生火花的铁质工具
41. `H_0F065B25BAC84C329610C8FBF8` | 粉尘防爆 | 产尘、有害气体或其他毒物生产设备密闭、吸收、净化、排放措施不符合要求
42. `H_0FB29D1573D544FE8FACE3CE27` | 安全标志 | 仓库未按要求设置“易燃物品，严禁烟火”等醒目标识
43. `H_108B10FED8E24D248155616659` | 涂装安全 | 过滤式回收装置清粉和系统阻力自动检测/停机功能不符合要求
44. `H_1094F237782E4FC9A7D58CA44E` | 粉尘防爆 | 铝粉危废库房通风、氢气报警、防水防潮措施缺失
45. `H_1201F11443914660BCC291055B` | 危险化学品与危险物质 | 化学危险品建筑物、区域内吸烟和使用明火问题
46. `H_1251ED2287FB47B6BDED9292D1` | 总图与建筑 | 防雷建构物外部防雷及防雷电电涌侵入措施缺失
47. `H_128CF6B2AEFB46EA98D63BE037` | 安全管理 | 排放腐蚀性气体的排气筒未采用防腐设计
48. `H_14FF17559BF1415B9F0007905D` | 应急与事故管理 | 铸造用熔炼炉、精炼炉、保温炉未设置紧急排放和应急储存设施
49. `H_1507C0C16EB84487BA78230E0D` | 安全标志 | 管线缺少相关标识

## Verified supporting links

这 11 条本身可以作为补充信息，但 `supporting` 不能单独使 hazard 获得发布资格：

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

当前共 67 条。它们保留用于历史追溯，不应进入当前公开投影，除非后续生命周期复核发现数据错误。

其中本轮新增确认：`H_A73EC0543AA24DF583F70E566B` 的正文为“未见与办公生活区域混杂布置情况”，属于正向事实而不是隐患；已保留 Stable ID 并转为 `superseded`，其原 direct link 保持 `rejected`。

## Technical acceptance snapshot

最新 `chat-v4` commit `cd290376...` 的 V4 Final Acceptance CI：

- integrated validator: PASS
- dangling refs: 0
- stale link review hash: 0
- stale hazard context hash: 0
- stale clause context hash: 0
- exact evidence mismatch: 0
- six-stage Gate: STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE 全 PASS
- strict audit: PASS, blockerCount=0, warningCount=60, excludedCount=105
- search regression: 20/20 PASS
- deterministic candidate build: PASS
- knowledge mutation check: PASS
- candidate-only boundary: PASS (`candidate=true`, `production=false`)
- candidate `sourceStateHash`: `545a828e653fe634754d50699c7e321448dbac25396500b15c1a015f1a0e0e5f`

## Remaining semantic queues

自动扫描仍提示以下候选，必须人工语义终审，不能因为 CI 为绿就自动视为内容正确：

- stale old-standard refs in hazard fields: 14
- obligation-restatement candidates: 11
- links to merged hazards: 9
- partial-replaced standard hazard hits: 12
- full-replaced standard hazard hits: 0
- pending Requirements: 20
- active hazards without qualifying direct/fallback: 49

这些队列是 Phase 16 后续工作的真实输入。
