# 接手说明

先读根目录 `AGENTS.md`、技能库当前 `ROUTING.md` 和公共规则；以下快照不能替代再次读取远端 main 与 Actions。

<!-- CURRENT_STATE_BEGIN -->
## 当前统一状态（2026-09-26，本维护增量待远端验收）

`knowledge/manifest.json`：**107 laws / 110 law versions / 3,000 clauses / 2,127 hazards / 1,959 links / 1,209 evidence / 26 successions / 75 requirements**；生命周期 **1,706 active / 324 proposed / 97 superseded**。

本分支已验证本地公开包 `releaseHash=13479ca8932aef06fddc53b8f3685f175c4db01c4a7dade95b0b230379fd95a7`。本地 Gate 构建的公开范围：**1,706 hazards / 62 laws / 62 law versions / 1,336 clauses / 1,825 links / public proposed 0**，`asOf=2026-09-26`。这不是本增量已经公网部署的声明；本批 PR、main Actions、Pages 与 Online Verify 必须在部署后另行记录。

最近实际核实的旧线上快照：main `72fd38489a54e8797da4a757690c1ab9f241b040`（PR #82），Validate `36170580281` 与 Build/Pages/Online Verify `36170580283` 均成功；旧公开包 **1,704 hazards / 61 laws / 61 law versions / 1,333 clauses / 1,822 links**，`releaseHash=c144beeaa60ed4ff4fbb3dc3ec1da92d45103cdd82cab6c29c6e8bcf57d73a90`。旧数据/构建规则提交 `7231cd24c9a971123c44f972537e528fa855469a` 与本次核验的 main 快照不是同一个概念。

本批新增 **6 个隐患实体（1 active、5 proposed）**，另将既有气瓶防倾倒候选 **1 条转正**；新增 **2 laws / 2 versions / 4 clauses / 4 links / 7 evidence**。供应方说明书义务不替代使用单位义务；一般报警故障不自动认定为重大事故隐患。

2026 全量项目任务**尚未完成**：已登记 **43 份来源载体**、形成 **782 条原始记录行**；其中 **45 条完成细分处置**、**12 条排除**、**725 条仍待逐条审核**。45 条形成 55 项处置记录，已定位 **39 个不同 canonical 实体**（既有 active 13、既有 proposed 17、沿 superseded/mergedInto 归并 3、真缺口 6）；另有 6 个细分事项待事实或依据核实。该39个不是782条记录的最终去重数，计数分类不重复相加。

来源纠错：某审阅稿“110项符合”附有预填且未经现场核实说明，不能作为现场零隐患证明；某原始评分表与另一来源70条描述完全相同，已隔离归属冲突；往年事实、正向表述却扣分、纯照片镜像、未见标志不等于未检等均不直接转为现场隐患。源文件未渲染、未生成预览、未转换格式。

审计与恢复：[FIELD_SOURCE_AUDIT_20260926](FIELD_SOURCE_AUDIT_20260926.md)，机器计数见 `docs/field-source-progress-20260926.json`，逐项去向见 `docs/field-source-disposition-20260926.jsonl`。私有源文件标识、原始文本及企业/个人信息不进入 GitHub。
<!-- CURRENT_STATE_END -->

## 恢复顺序

先重新核对 main、manifest、当前线上 releaseHash 和最新 Actions；再读取本批审计、来源处置文件及私有恢复包。继续处理725条尚未逐条审核的原始行；不能重新将43份载体或782行视为新的缺口。保留S041来源归属隔离，核实S012/S014日期；补查未完成的项目正式版本选择和专家现场记录，不以文件修改日期证明项目年份。

优先复用全库 active/proposed/superseded，沿mergedInto回到当前实体。本批叉车钥匙候选虽找到官方检索引文，原页抓取失败，尚未达到本库正式证据要求。5个新候选均不公开；已有配电柜积尘、岗位规程、吊具载荷标识等候选也不得因别名补充自动转正。

所有个人信息、企业到来源的私有映射只放私有交接材料。未经用户明确允许，不渲染、预览或转换原文件。新的阶段开始和结束都记录北京时间、累计耗时、已完成与剩余范围。
