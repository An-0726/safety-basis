# 2026-09-21 工程级审计与整改报告

> 状态：审计分支发布候选已完成全量自动 QA；尚待通过 PR 合并 main、Pages 部署及线上复验。

## 一、总体结果

- 审计分支：`audit/engineering-20260920`。
- 最终知识库存：104 laws / 107 lawVersions / 2,993 clauses / 2,053 hazards / 1,923 links / 1,201 evidence / 26 successions / 75 requirements。
- 隐患生命周期：1,680 active / 276 proposed / 97 superseded。
- 最终公开候选包：1,680 hazards / 59 laws / 59 lawVersions / 1,303 clauses / 1,790 links；public proposed=0。
- 最终 QA releaseHash：`bf2418ce9d28737813a62fc2b3f7a51b552b4fba4106121452b0183a3323d5bc`。
- Engineering QA run `35525485280`：自动门禁、comprehensive scanner、分类全量审计、统一包重建/验证、Chromium 桌面/移动端严格验收全部 PASS；scanner 0 ERROR / 1 WARNING。

## 二、主要问题

### P0

1. `knowledge/manifest.json` 与物理库存漂移：manifest 写 2,015 hazards / 1,886 links，但实际目录为 2,051 / 1,922；原门禁未阻断。
2. PR #70 长丰批量导入的 36 个 hazard + 36 个 link 被批量写成 active/direct/verified，多个完全不同隐患共用泛化条款，且 review evidenceRefs 为空。
3. rejected link 仍保持 active lifecycle，导致审核决策与实体生命周期不一致。
4. review binding 按文件名加载部分实体，内部 Stable ID 与转义文件名不一致时会产生假孤儿；missing reference 之前仅打印不阻断。
5. 2 个 active hazard 没有当前可发布的 qualifying direct/fallback 依据，生命周期与发布语义不一致。

### P1

1. 网页筛选 URL、分享链接、浏览器前进/后退和 hazard→law 导航存在状态丢失/跳转错误。
2. 配电柜门隐患把所有柜门机械写成“必须软铜跨接”，未限定“装有电器的可开启门”。
3. 仓储“五距”已有直接条款但关联状态未正确参与正式链。
4. 长丰酒精/稀释剂条目把“必须存入防爆安全柜”写成绝对要求，缺少浓度、危险性、数量和使用方式前提。
5. 部分标题为法条复述式，已对当前 active 主记录收敛；1 条 superseded 历史标题仅保留追溯。

### P2

1. manifest 的 Phase 16 `scope/migrationPhase` 文案长期过期，与当前库存不一致。
2. `ingest_changfeng_full.py` 默认把批量导入直接写成 active/direct/verified，存在再次污染正式库风险。
3. 审计过程中产生的一次性 apply/inspect workflow 不适合长期保留，已清理，改为通用 Engineering QA。

## 三、已完成修改

- 新增 `check_manifest_inventory.py` 并纳入 `validate_all.py` blocking gate：实体物理数量、manifest 计数、hazard lifecycle 三方不一致即失败。
- `check_review_binding.py` 改为按实体内部 ID / review.entityId 加载，并把 missing link/hazard/clause、ID mismatch 纳入阻断。
- 长丰批量导入器默认改为 `proposed + candidate + pending`，不再自动制造正式结论。
- PR #70 36 条全量处置：7 条明确重复/实质重叠项 `superseded + mergedInto`，29 条证据或适用性不足项改为 proposed；对应错误关联退出正式发布。
- 配电柜门 3 条同类记录收口为一个 canonical 记录，2 条重复 ID 保留为 superseded。
- 五距重复隐患再合并 1 条，XF 1131-2014 第6.8条恢复为正式 direct 依据。
- 2 个 active-but-unpublished 隐患收口：五距重复项合并；危险化学品安全管理制度以《危险化学品安全管理条例》第4条恢复直接依据。
- 网页路由/筛选/分享/前进后退/双向导航修复；新增真实 Chromium 验收脚本和回归测试。
- 删除 13 个一次性审计 workflow/迁移脚本/补丁文件；保留长期可手动复用的 Engineering QA。

## 四、法规与隐患修正

### 数据前后对账

| 项目 | 审计前实际物理库存 | 审计后 | 变化 |
|---|---:|---:|---:|
| laws | 103 | 104 | +1 |
| lawVersions | 106 | 107 | +1 |
| clauses | 2,992 | 2,993 | +1 |
| hazards | 2,051 | 2,053 | +2 |
| links | 1,922 | 1,923 | +1 |
| evidence | 1,199 | 1,201 | +2 |
| active hazards | 1,718 | 1,680 | -38 |
| proposed hazards | 246 | 276 | +30 |
| superseded hazards | 87 | 97 | +10 |

新增法规链：GB 14784-2013《带式输送机 安全规范》1 个 law、1 个 lawVersion、1 条直接条款（4.1.11 i）和 2 份权威证据。

## 五、近期商贸集团检查补充

1. **粮库输送机急停**：新增正式隐患 `H_BELT_CONVEYOR_ESTOP`。GB 14784-2013 第4.1.11 i）明确：沿人行通道一般设置急停拉绳；输送机长度小于30 m时允许用急停按钮代替，但长度方向任一点至按钮不得大于10 m。没有再写死“必须拉绳”。
2. **烘干燃料 SDS / 警示**：没有在未知燃料种类时强行认定危险化学品；需先确认燃料名称、成分和危险性，再决定 SDS、标签和警示义务。未生成虚假的正式 direct 结论。
3. **动力柜柜门保护连接**：收紧为装有电器的可开启门；采用 GB 50303-2015 第5.1.1条直接依据，合并 2 条重复实体。
4. **化验室酒精**：把原“酒精必须进防爆安全柜”候选改成条件化表述；必须先确认浓度、危险性、单次/总储量、包装和使用方式，再判断限量、密闭、通风、火源控制及是否需要专用柜。
5. **灭火器**：数量不足仍要求按 GB 50140 的场所面积、火灾种类、危险等级、配置单元、保护距离计算后判断；新增“经维修的灭火器未见维修合格证” proposed 候选，未在证据链不完整时强行发布。
6. **纸箱库五距**：XF 1131-2014 第6.8条按 0.3/0.5/0.5/0.3/1 m 的顶距、灯距、墙距、柱距、垛距恢复正式 direct；与第6.6条分类、分堆、限额要求区分展示。

## 六、网页修改

- 保留当前简洁 UI，不做后台式重构。
- 修复 filter 状态进入 URL、分享链接 reload、浏览器 back/forward、hazard-law 双向跳转。
- 本地最终包 Chromium：desktop、mobile 390px、全量已发布 hazard/law/quote/count 校验全部 PASS。
- 审计时线上站点仍为旧 main（1,716 hazards），因此线上 observed defect 仅作为部署前基线；必须在本 PR 合并并 Pages 部署后重新验收。

## 七、自动测试与门禁

- Node 前端测试：PASS。
- Python pipeline 单元测试：PASS。
- `validate_all.py`：PASS。
- `strict_release_audit.py`：PASS，blockerCount=0。
- `validate_publication_integrity.py`：PASS。
- comprehensive scanner：0 ERROR / 1 WARNING；唯一 WARNING 为已 superseded 的历史法条复述式标题，保留历史不改写。
- 统一公开包 build + verify：PASS。
- taxonomy 全量审计：PASS。
- Chromium 严格本地验收：PASS。

## 八、仍无法确认的问题

1. 二道站粮库烘干燃料的具体品名/成分未提供，无法判断其是否属于危险化学品，因此 SDS、化学品标签及警示标识的直接适用条款需待物质确认。
2. 化验室酒精的浓度、单次使用量、最大储存量和包装方式未提供，因此具体储存柜、限量及防火分区要求保留条件化判断。
3. 灭火器维修合格证候选尚未取得足以进入本库正式证据链的官方标准全文证据；目前保持 proposed。

## 九、Git 变更

- 分支：`audit/engineering-20260920`。
- 所有修改均通过普通 fast-forward 提交；未 force push、未重写历史。
- 旧 PR #71 已因与本轮全量审计结论冲突而关闭并留说明。
- `main` 受 ruleset 保护：必须经 PR，required checks 为 `validate`、`build`。

## 十、耗时

- 审计墙钟起点：2026-09-20 18:57（UTC+8，首个隔离工程审计 run）。
- 分支最终候选 QA：2026-09-21 01:20（UTC+8）完成。
- 墙钟约 6 小时 23 分钟；其中包含多次用户中断/恢复、GitHub Actions 排队与浏览器依赖安装。
- 主要阶段：仓库/网页基线约 1 小时；manifest/门禁与数据差额追踪约 1 小时；PR #70 + 商贸专项整改约 40 分钟；全库 QA、回归修复、清理与文档收口约 1 小时；其余时间为中断恢复及 CI/依赖等待。

本报告记录的是合并前发布候选；合并 main、Pages 部署和线上复验结果将在部署完成后补写。
