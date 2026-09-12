# 人工复核工作簿适配提案草稿

日期：2026-09-11  
提案 ID：`HEXP_cfaa7d2de8270dcbb2dc8d08d1`  
状态：`DRAFT_REVIEW_ONLY`  
`applyAllowed`：`false`

## 来源与基线

- 输入：`D:/Desktop/Safety_Basis_隐患库专业复核_ChatGPT.xlsx`，`隐患明细` 634 行。
- 对照：远端 `main` knowledge 快照 `f0acc76ef4813f5e684378dc3252ed1708fbebcf`。
- 634/634 hazard、839/839 link、163/163 clause、42/42 law-version 读取成功，抓取错误 0。
- 选择远端主线作为对照基线，因为工作簿的 634 个稳定 ID 全部存在于该快照，而本地母库是不同版本；本地 SQLite 未写入。

## 提案内容

- 490 条记录有核心字段变化，144 条无核心字段变化。
- 变更字段计数：标题 210、专业描述 295、整改措施 196、适用条件 365；主题和场所 0。
- 每条变更包含远端原值、工作簿新值、稳定 ID、远端 JSON 路径、现有关联 ID、direct clause ID 和映射信号。
- 草稿只更新工作簿已有的 hazard 核心字段，不创建、删除或修改法规、条款、依据关联。

## 待人工处理标记

| 标记 | 数量 |
|---|---:|
| `basis_unmatched` | 60 |
| `quote_unmatched` | 28 |
| `no_active_direct_link` | 32 |
| `not_publishable` | 3 |
| `basis_blank` | 2 |

标记可能重叠。依据/原文匹配是去空白后的文本信号，不是法规现行性、适用性、隐患判定或审批结论。所有标记在解决前不得转为正式 apply 提案。

## 文件

逐条原值/新值和映射信息见同目录的 `hazard_excel_review_proposal_draft_20260911.json`。该 JSON 是项目审阅材料，不是 `tools/pipeline/exchange.py` 的 exchange-v2 输入，不能直接调用 `exchange.py apply`。
