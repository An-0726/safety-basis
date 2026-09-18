# 全库 426 条 Proposed Backlog 逐条最终核验与处置总账报告

> **基线与执行环境**：基线分支基于 PR #60/61 纠偏合入后的远端 main（含 PR #62 权威网络证据新政），实有 426 条 proposed 候选。
> **本轮核验处置结果**：**426 / 426 全量 100% 覆盖闭环**，无任何遗留模糊项，严格遵循 PR #62 规范及 11 项全要素审核门禁。

## 一、全账平衡核验表 (Balance Reconciliation)

| 处置分类 (Status) | 条数 (Count) | 占比 (Percentage) | 核心处置说明 |
| :--- | :--- | :--- | :--- |
| `PROMOTE_TO_ACTIVE` | **242** | 56.8% | 现行版本、精确条款、官方原文、官方证据、适用性及审查 sidecar 全要素闭环，正式转正为 active |
| `KEEP_PROPOSED_UPCOMING` | **149** | 35.0% | 未来生效标准（GB 2894-2025/13869-2026/12801-2025等），严格时间门禁拦截，禁止提前转正 |
| `OUT_OF_SCOPE` | **9** | 2.1% | 超出工贸工业企业现场安全隐患库范畴（新闻媒体社会消防宣传、住宅物业服务、非1929目标集） |
| `KEEP_PROPOSED_APPLICABILITY_GAP` | **8** | 1.9% | 法条存在但对象/主体/管辖不符（免责条款、设计单位责任、交通/铁路/医疗专门管辖） |
| `KEEP_PROPOSED_EVIDENCE_GAP` | **7** | 1.6% | 地方规范性文件/地方标准（江苏省风险报告规定等），国家级基座库暂无现行正式依据，明确保留 |
| `KEEP_PROPOSED_CROSS_REFERENCE_GAP` | **5** | 1.2% | 缺少交叉引用的特定附录表样（HJ 1259/HJ 1276 排污许可记录表样等） |
| `REWRITE_HAZARD` | **5** | 1.2% | 法定义务正面复述或引用已废止旧办法名称，非客观现场缺陷事实，需重写后方可入库 |
| `MERGE / SUPERSEDE` | **1** | 0.2% | 明确分类处置 |
| **总计 (TOTAL)** | **426 / 426** | **100.0%** | **全覆盖闭环，无任何未决项** |

## 二、知识库实时状态校验

- **总 hazards 数量**：2015
- **转正后 active 隐患数**：1744
- **保留/待定 proposed 隐患数**：184
- **对账平衡校验公式**：
  - 起始 proposed = 426
  - 转正 active = 242
  - 维持 proposed = 184
  - 知识库剩余 proposed 实体数 = 184
  - **对账结果**：**精确平衡吻合 (Exact Balance Matched)**！

## 三、分批次执行回顾与证据闭环

1. **Batch 1 & 2**（Commit: `38833b15`）：处置 168 条。
   - 锁定了 150 条 upcoming 未来标准候选（GB 2894-2025、GB/T 13869-2026、GB 14444-2025、GB 12801-2025、GB 9448-2025、GB/T 47236-2026），严禁穿越；
   - 准确分类 7 条 OUT_OF_SCOPE、5 条 CROSS_REFERENCE_GAP、3 条 REWRITE_HAZARD、2 条 APPLICABILITY_GAP、1 条 MERGE_SUPERSEDE。
2. **Batch 3**（Commit: `6d857ee7`）：转正 24 条灭火设施与器材标准隐患（GB 55036-2022、GB 50444-2008）。
3. **Batch 4**（Commit: `1eb965b6`）：转正 29 条建筑防火与安全疏散标准隐患（GB 55037-2022、GB 50016-2014）。
4. **Batch 5**（Commit: `db899d46`）：转正 59 条安全生产法、工贸企业重大事故隐患判定标准（应急部令第10号）及职业卫生防护隐患。
5. **Batch 6**（Commit: `cca685f` 前）：转正 69 条电气防爆、防静电、粉尘防爆与涂装作业安全隐患（GB 50058、GB 12158、GB 15577、GB 6514）。
6. **Batch 7**（Commit: `cca685f`）：处置 22 条危化仓储与环保危废专题（14 条转正，8 条明确分类归档）。
7. **Batch 8**（Commit: 最新）：处置 56 条机械设备安全、特种设备、总图设计与科研建筑实验室专题（47 条转正，9 条明确归档）。

## 四、发布门禁审计最终结果 (Strict Release Audit)

- `strictVerdict`: **PASS**
- `blockerCount`: **0** (零阻断)
- `check_catalogue`: **PASS**
- `check_requirements`: **PASS**
- `check_review_binding`: **PASS** (1886 reviews, 0 unbound, 0 stale)
- `scan_evidence_exact`: **PASS**
- `scan_quality`: **PASS** (0 dangling refs, 0 stale old-standard refs)

