# V4.1 Requirement 中间层（Regulation-driven 知识架构核心）

状态：**设计已定稿，2026-09-10 落地第一批**
分支：chat-v4（未切 production）

## 1. 为什么需要 Requirement

V4.1 采用双向知识生产：

```
Hazard-driven： 现场隐患 -> 法规依据
Regulation-driven：完整法规 -> Clause -> Requirement -> Hazard candidate -> Link
```

禁止"一条 Clause = 一条 Hazard"。Clause 是法规原文，Hazard 是现场缺陷事实，
二者之间必须有 **Requirement** 作为"从法规条款中提炼出的、可检查、可判断、
可关联现场场景、但不冒充法规原文的原子义务"中间层。

三层分离原则：
- Clause：法规原文（不可改写）
- Requirement：AI/人工提炼的原子检查义务（可检查、可判断）
- Hazard：现场隐患事实（带缺陷表述）

## 2. Requirement 实体 Schema

文件位置：`knowledge/requirements/RQ_<hash>.json`

```json
{
  "id": "RQ_<22位大写HEX>",
  "lawVersionId": "<LV id>",
  "clauseId": "<C id>",
  "seq": 1,
  "title": "义务标题（条款主题 + 核心义务）",
  "description": "可检查、可判断的义务描述（不得冒充条款原文）",
  "sourceQuote": "来源条款原文摘录（只读，来自 clause.quote）",
  "scope": "适用对象/场所范围",
  "checkItems": ["检查要点1", "检查要点2"],
  "lifecycle": "active",
  "reviewStatus": "pending|verified",
  "reviewedAt": "",
  "reviewer": "",
  "reviewReason": "",
  "canonicalHash": "<sha256>"
}
```

## 3. ID 规则

`RQ_` + sha1(`lawVersionId|clauseId|seq`)[:22].upper()

## 4. canonical hash

复用 `tools/v4/canonical.py` 的 `content_hash()`：对去除 `canonicalHash`
字段后的实体做规范化 JSON（UTF-8、sort_keys、set 字段排序、紧凑分隔符）sha256。
`canonicalHash` 字段本身不参与 hash（防自引用）。

## 5. review / verification 机制

- `reviewStatus=pending`：AI 生成草案，未人工校准
- `reviewStatus=verified`：提炼经人工/专业复核，确认可检查、可判断、无歧义
- Requirement 的 verified 不代表 Link verified：Link 仍需独立 applicability review
- 修改 Clause 或 Requirement 内容后，Requirement 的 canonicalHash 必须重算，
  旧的 verified 状态不得延续（同 review freshness 原则）

## 6. lifecycle

- `active`：现行义务
- `superseded`：来源条款被替代后失效（由 succession 驱动，Phase 13 影响分析输出）
- 不引入"征求意见稿"状态（法规征求意见稿不产生现场义务）

## 7. source Clause 关联

`clauseId` 必须可解析到 `knowledge/clauses/` 中存在的实体；
`lawVersionId` 与 clause.lawVersionId 必须一致（validator 检查）。

## 8. Requirement -> Hazard / Link 关系

- link 实体新增可选字段 `requirementId`（指向 Requirement）
- 语义：link 表达 "Hazard 违反 Requirement（经由 Clause 的法规义务）"
- 一条 Hazard 可关联多个 Requirement（复合义务）；一个 Requirement 可关联多个 Hazard
- 不要求每个 link 都有 requirementId（既有 link 不回溯补字段，新增 link 建议带）

## 9. validator

`tools/v4/check_requirements.py` 检查：
- JSON 可解析、id 唯一、字段齐全
- clauseId / lawVersionId 可解析且一致
- canonicalHash 与现算一致（不一致报 STALE_HASH）
- reviewStatus=verified 时 reviewer/reviewedAt/reviewReason 非空
- lifecycle 枚举合法
- link.requirementId 可解析（若存在）

## 10. migration / build 支持

- `tools/v4/generate_requirements.py`：从 `knowledge/clauses/` 全量生成
  requirement 草案（每 clause 至少 1 条，seq 递增），reviewStatus=pending
- 生成器幂等：已存在的 RQ id 跳过不覆盖
- manifest 新增 batch 记录（requirementsAdded / requirementsCalibrated）

## 11. 文档与验收

- 本文档 + `docs/V4_1_REGULATION_DRIVEN_KNOWLEDGE.md` 为架构权威说明
- Requirement 层的验收指标：
  - 每条 requirement 可检查（checkItems 非空）
  - 不冒充条款原文（description 与 quote 区分）
  - 高覆盖 clause（被 link 引用的 clause 优先校准为 verified）
