# 知识库可重建对账（2026-11-08）

读取正式knowledge和现有release_gate_core；按Gate发布集合逐ID对账。优先级为补证工作排序，不是现场风险评级或重大隐患结论。

本文件为机器产物；证据核验、实施前线上版本与本次修复解释见 [收口报告](KNOWLEDGE_CLOSEOUT.md)。

## 源库与公开投影

|对象|源库数量|当前发布投影|
|---|---:|---:|
|隐患记录|2172|1766|
|法源版本|160|106|
|条款|3255|1514|
|关联|2313|1951|

H lifecycle：active 1777 / proposed 265 / superseded 130。active中有 11 条没有通过完整发布链。

## 候选的当前缺口分类

|主要缺口|数量|
|---|---:|
|适用性或条款审核待补|17|
|尚无精确条款关联|136|
|原文证据缺失或引用未解析|2|
|原依据或关联已拒绝，须重新对题核验|110|

主分类互斥用于计数；每条记录还保留全部 gapCodes、关联/条款/版本/法规Gate理由及证据状态，不能把单一主分类当成完整法律审查。

## active而未发布的逐ID原因

|稳定ID|标题|主要原因|
|---|---|---|
|`H_1B474A2ABA0E23143E2FE451`|镁废屑袋装储存未单层存放、存在堆垛存放|BLOCK_REVIEW_NOT_VERIFIED:rejected；BLOCK_CLAUSE_TEXT:clause_gate_failed|
|`H_409ABC97960D46FBBF6AA54D28`|微型消防站缺少物品 清单和检查记录|BLOCK_REVIEW_NOT_VERIFIED:pending；BLOCK_LINK_APPLICABILITY:link_not_active|
|`H_68196C0A0FBDDAF0354E0F71`|进行检修和抢修作业时未携带氨气检测仪（检测报警设备）|BLOCK_REVIEW_NOT_VERIFIED:rejected；BLOCK_CLAUSE_TEXT:clause_gate_failed|
|`H_6F7D6D7E28DD423B9F40AF8218`|在燃气、空气或氧气的混气管路与燃烧器之间,未设阻火器|BLOCK_REVIEW_NOT_VERIFIED:pending；BLOCK_LINK_APPLICABILITY:link_not_active|
|`H_8C14C2BD0D4A4EF1B42FDC8C2E`|机加工废屑未配备专用收集容器或清理不及时|BLOCK_REVIEW_NOT_VERIFIED:rejected；BLOCK_CLAUSE_TEXT:clause_gate_failed|
|`H_B552B08A4FD28A8770CDC2BB`|存在有毒、缺氧等高风险检修抢修作业时未按风险配备和使用适用的呼吸防护装备|BLOCK_REVIEW_NOT_VERIFIED:rejected；BLOCK_CLAUSE_TEXT:clause_gate_failed|
|`H_BF7AA7549F8E1B94012882C9`|粉尘废屑未优先采用机械压块压实处理，干式储存未桶装加盖或袋装封口密闭|BLOCK_REVIEW_NOT_VERIFIED:rejected；BLOCK_CLAUSE_TEXT:clause_gate_failed|
|`H_C1CE3A649721387F1FC0F7BE`|粉尘废屑未冷却至常温即入库存放，或不同种类混装、与氧化物/过氧化物/酸/爆炸品/易燃物品同场所存放|BLOCK_REVIEW_NOT_VERIFIED:rejected；BLOCK_CLAUSE_TEXT:clause_gate_failed|
|`H_CE94D2ACC8C544BCA0FB0AA026`|有高处坠落危险的作业部位未配置扶梯平台、围栏和系挂装置|BLOCK_CLAUSE_TEXT:clause_gate_failed；BLOCK_VERSION_EXPIRED:active_past_endDate|
|`H_D98B4749D74246E2A3825D5B09`|液化石油气气瓶间缺失少“严禁烟火”、“易燃易爆” 等安全警示标志|BLOCK_REVIEW_NOT_VERIFIED:pending；BLOCK_LINK_APPLICABILITY:link_not_active|
|`H_F0D64F91542E4B0399D83D670D`|每个堆间,未留有搬运通道|BLOCK_REVIEW_NOT_VERIFIED:pending；BLOCK_LINK_APPLICABILITY:link_not_active；BLOCK_REVIEW_NOT_VERIFIED:rejected|

每项最小补证动作与确切K/C/LV链在同日JSON的 `activeExcluded` 中；没有删除或改写这些稳定ID。

## 2026-10-16→2026-11-08的逐ID版本投影变化

### hazards

- 新增：无。
- 移出：无。

### links

- 新增：`K_CLOSEOUT_H_89016FC0F3E849C2B8B8755C35_C_CMA_2026_AMENDED_13`、`K_CLOSEOUT_H_89016FC0F3E849C2B8B8755C35_C_CMA_2026_AMENDED_17`。
- 移出：`K_REBUILD_H_89016FC0F3E849C2B8B8755C35_C_CMA44_2025_13`、`K_REBUILD_H_89016FC0F3E849C2B8B8755C35_C_CMA44_2025_17`。

### clauses

- 新增：`C_CMA_2026_AMENDED_13`、`C_CMA_2026_AMENDED_17`。
- 移出：`C_CMA44_2025_13`、`C_CMA44_2025_17`。

### lawVersions

- 新增：`LV_CMA_LIGHTNING_MANAGEMENT_2026_AMENDED`。
- 移出：`LV_CMA_LIGHTNING_MANAGEMENT_2025`。

## succession与效力待办

逐条检查 27 个succession，完整关系、旧条款、受关联active H、当前发布旧版H及旧代号文本线索在JSON中。部分替代不按整部废止处理，历史note命中不自动判错。

|当前观察|版本/关系|最小动作|
|---|---|---|
|无新增结构/日期预警|—|保持按日复核|

## 产物与复现

- 全量候选JSONL：每个proposed恰好一行，含稳定ID、证据链、条件、优先分和具体补证动作。
- 优先队列Markdown：前40项，便于人工领取。
- 对账JSON：库存、公开集合、排除原因、逐ID日期差异与全部succession。
- `--check`：比较生成文件与当前源库，产物过期或有覆盖/计数错误时非零退出；不会更新审核、修改知识或放宽发布。

知识源指纹：`5694986120f36d4ed4e4f0a3ff7cfe1f49e6bf39cdd476716617eb5de746d606`。验证错误数：0。
