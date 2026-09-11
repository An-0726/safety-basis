# V4.1 Regulation-driven Ingestion Pipeline（法规完整导入流程）

状态：**机制已落地（2026-09-10），Hazard candidate 查重步骤待增量补充**
分支：chat-v4（未切 production）

## 1. Pipeline 全链路

```
Law（法规/标准身份）
  -> LawVersion（具体版本）
  -> Clause（条款原文，逐条入库）
  -> Requirement（AI/人工提炼的原子检查义务）
  -> 与已有 Hazard 查重
     - 命中已有 Hazard：复用（建立 link 候选）
     - 未命中且有现场检查价值：生成新 Hazard candidate
  -> Link（Hazard <-> Clause <-> Requirement 关系）
  -> Review（applicability 专业复核）
  -> Gate（结构/内容/适用性/版本/证据/发布分级）
```

禁止：
- 只摘取用户当前问到的几条（必须完整导入已选定法规）
- 为了"完整"自动把所有条款变成 Hazard
  （只有具备现场安全检查/管理判断价值的条款才提炼为 Requirement，
   Requirement 再按查重决定是否形成 Hazard candidate）

## 2. 已落地组件（chat-v4）

| 步骤 | 组件 | 状态 |
|---|---|---|
| Law/LawVersion/Clause 导入 | `tools/v4/add_catalogue_entities.py` | ✅ 已用（危化品双轨 + 2026 版本链） |
| Clause -> Requirement 生成 | `tools/v4/generate_requirements.py` | ✅ 已用（75 条 clause -> 75 条 RQ 草案） |
| Requirement 校验 | `tools/v4/check_requirements.py` | ✅ 已用 |
| 版本影响分析 | `tools/v4/version_impact.py` | ✅ 已用（13 条 hazard 迁移依据） |
| Requirement -> Hazard 查重 | `tools/v4/match_requirement_hazards.py` | 🔲 待增量实现（见 §4） |

## 3. 数据流约定

- Clause 只存原文（quote 不可改写）
- Requirement.description 是提炼义务（可检查、可判断），不得冒充条款原文
- Requirement 生成后 reviewStatus=pending，经专业校准后 verified
- Requirement 不直接决定 Link：Link 仍需 Hazard-Clause 双向 applicability review

## 4. Requirement -> Hazard 查重（设计）

查重维度（关键词/语义混合，仅出候选，不自动 verified）：
1. 义务主题（title 规范化）
2. 技术对象（设备类型/场所/介质，如"防爆""消防""危化品储存"）
3. 场景短语（places/category）

输出：
- match 候选：requirement 与现有 hazard 可能对应（建议复用，建立 link candidate）
- new 候选：无匹配且有现场检查价值（生成 hazard candidate，lifecycle=candidate）

任何查重结果都不自动落库为 verified：hazard candidate 需走 review 流程。

## 5. 下一步（未在本轮完成）

- match_requirement_hazards.py 查重工具（关键词+语义候选）
- 完整法规逐条导入的第二批（危化品安全法全文 127 条导入为 Clause+Requirement）
- Hazard candidate 的 review / 验收流程文档
