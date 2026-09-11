# Safety Basis V4.1 法规驱动知识生产设计补充

> 状态：规范性设计补充（2026-09-10）
> 适用分支：`chat-v4`
> 作用：补充 `PROJECT_PLAYBOOK.md`、`ARCHITECTURE_V4_CHAT_FIRST.md`、`GATE_V4.md`。
> 原则：在正式合并进上述总设计前，本文件对“完整法规导入、Requirement、隐患生成、搜索召回”相关事项具有同等规范效力；冲突时以更严格的质量门禁为准。

---

## 1. 新增项目主线：双向知识生产

Safety Basis 不再只做“从隐患找法规”，同时支持“从完整法规系统地产生检查知识”。

两条主线并行：

```text
A. Hazard-driven
现场问题 / 图片 / 报告
  → 规范化 Hazard
  → 匹配 Clause
  → Link applicability 核验
  → 输出专业描述、法规原文、整改措施

B. Regulation-driven
完整法规 / 标准
  → Law / LawVersion
  → 全文逐条结构化为 Clause
  → Clause 拆解为原子 Requirement
  → 识别可检查 Requirement
  → 与现有 Hazard 查重 / 复用 / 生成候选
  → 建立 Requirement ↔ Hazard 追溯
  → 建立 Hazard ↔ Clause Link
  → applicability 核验
  → 进入 verified 知识库
```

目标不是“保存一本法规 PDF”，而是把完整法规转化成可检索、可检查、可追溯、可复用的安全知识。

---

## 2. 不采用“一条 Clause = 一条 Hazard”

法规条款与隐患不是一一对应关系。

允许：

- 一个 Clause 产生 0 个 Requirement：定义、立法目的、行政职责、处罚、附则等通常不直接形成现场检查点；
- 一个 Clause 产生多个 Requirement：同一条款可能同时包含防护、联锁、距离、标识、检测等多个独立义务；
- 一个 Requirement 对应多个 Hazard：同一通用义务可在不同设备、场所形成不同现场隐患；
- 一个 Hazard 由多个 Requirement / Clause 支撑。

因此新增中间实体 `Requirement`，把法规原文与 AI 提炼出的“原子检查要求”分离。

---

## 3. Requirement 实体

建议目录：

```text
knowledge/requirements/
knowledge/reviews/requirements/
```

建议最小结构：

```json
{
  "id": "RQ_xxx",
  "clauseId": "C_xxx",
  "subject": "生产经营单位",
  "action": "设置",
  "object": "明显的安全警示标志",
  "conditions": ["有较大危险因素的生产经营场所和有关设施、设备"],
  "exceptions": [],
  "thresholds": [],
  "requirementType": "mandatory",
  "checkable": true,
  "keywords": ["安全警示标志", "危险因素"],
  "lifecycle": "active"
}
```

Requirement 只保存对 Clause 的结构化提炼，不保存伪造的“法规原文”。法规原文仍唯一保存在 Clause.quote。

推荐 `requirementType`：

- `mandatory`：应当 / 必须 / 应；
- `prohibition`：不得 / 禁止；
- `technical_limit`：距离、数值、容量、浓度、时间等限值；
- `configuration`：设施、装置、部件、标识、联锁等配置要求；
- `management`：制度、记录、培训、检查等管理要求；
- `other`。

`checkable=false` 的 Requirement 可以保留用于法规理解，但默认不生成现场 Hazard candidate。

---

## 4. 完整法规导入流水线

获得一部完整法规 / 标准后，按以下顺序处理：

1. 核验 Law 身份：正式名称、文号/标准号、发布机关、jurisdiction；
2. 核验 LawVersion：版本、实施日期、效力状态、替代关系；
3. 按正式层级和 locator 将全文拆成 Clause；
4. 对每个 Clause 保留原文，原文与解释严格分离；
5. 对 Clause 做语义分类；
6. 将包含义务、禁止、技术要求、配置要求、管理要求的 Clause 拆为 0..N 个原子 Requirement；
7. 判断 Requirement 是否可转化为现场检查点；
8. 对可检查 Requirement 搜索现有 Hazard；
9. 优先复用已有 Hazard，必要时补 aliases / keywords；
10. 只有现有 Hazard 无法准确表达时才生成新 Hazard candidate；
11. 建立 Requirement → Hazard 追溯关系和 Hazard → Clause Link candidate；
12. 完成专业 applicability review 后才能进入 verified 发布链。

Clause 初步分类至少区分：

- `purpose`
- `scope`
- `definition`
- `administrative`
- `procedure`
- `penalty`
- `technical_requirement`
- `management_requirement`
- `prohibition`
- `other`

只有具有实际义务/禁止/技术检查意义的内容进入 Requirement → Hazard 主流水线。

---

## 5. Hazard 生成与查重原则

法规驱动产生的新隐患必须先作为 candidate / pending，不得自动 verified。

生成前必须与现有 Hazard 做查重：

- title；
- aliases；
- keywords；
- category；
- places；
- description；
- 已有关联 Clause / Law；
- Requirement 语义。

优先级：

```text
复用现有 Hazard
  > 给现有 Hazard 补 aliases / keywords
  > 必要时拆分现有过宽 Hazard
  > 最后才新增 Hazard
```

禁止为了“覆盖整部法规”而机械制造大量同义、近义、不可执行的 Hazard。

---

## 6. Requirement 的 Review 与门禁

Requirement 属于 AI/人工对 Clause 的结构化解释，因此必须独立 review。

推荐 review：

```json
{
  "entityType": "requirement",
  "entityId": "RQ_xxx",
  "reviewType": "semantic-extraction",
  "decision": "pending",
  "reviewedContentHash": "...",
  "contextHashes": {
    "clause": "<current clause hash>"
  },
  "reviewer": "...",
  "reason": "...",
  "evidenceRefs": ["... "]
}
```

正式 verified Requirement 至少满足：

- 来源 Clause 已通过 text gate；
- reviewedContentHash 与 Requirement 当前内容一致；
- `contextHashes.clause` 与当前 Clause hash 一致；
- Requirement 没有改变原条款中的主体、条件、否定词、例外、数值或单位；
- 不把解释性推断包装成原文义务；
- `checkable=true` 时应能明确说明实际检查对象/行为。

Clause 变化后，相关 Requirement review 必须 stale。

Requirement verified 不等于 Hazard → Clause Link verified；适用关系仍必须独立审阅。

---

## 7. 法规更新时的影响分析

完整法规导入不仅用于新增知识，也用于版本更新。

新 LawVersion 导入后应自动产生影响清单：

- 新增 Clause；
- 删除/失效 Clause；
- 文本变化 Clause；
- 新增/变化 Requirement；
- 受影响 Hazard；
- 受影响 Link；
- 疑似需要废止/替换的旧依据。

不得用“新标准号替换旧标准号”代替逐条影响分析。

---

## 8. 搜索能力：不得退化

V4 最终网站必须保留并增强当前生产站的扩展检索体验。

### 8.1 多字段召回

搜索词不要求出现在 Hazard.title 中。

至少以下字段共同参与 search-index：

- Hazard ID；
- title；
- aliases；
- keywords；
- category；
- places；
- 关联 Law 名称 / aliases；
- Clause locator / articlePath；
- 可公开的 Requirement keywords / object / action。

例如：条目标题是“用电设备周围安全通道或工作空间不足”，只要 aliases 或 keywords 含“配电箱”，搜索“配电箱”必须能够召回该条目。

### 8.2 相关度排序

不得退化为“命中即乱序”或“只按标题精确包含”。

排序原则至少保持：

```text
标题精确匹配
> 标题前缀/包含
> aliases
> keywords
> category / places
> Requirement 检查词
> 关联法规名称 / 条款
```

具体分值可由实现调整，但高价值字段的相对优先级必须稳定，并通过回归测试锁定。

### 8.3 规范化

搜索应继续进行：

- Unicode NFKC 规范化；
- 大小写统一；
- 常见中文/英文标点归一；
- 多空格归一。

后续可增加受控同义词词典和轻量 typo tolerance，但语义相似度只能用于“候选召回/排序”，不得因此改变 verified 状态或法规适用结论。

### 8.4 搜索回归门禁

V4 发布前必须维护一组固定搜索回归用例，至少覆盖：

- 标题直接命中；
- 别名命中；
- 关键词命中；
- 现场口语命中专业标题；
- 法规名称反查隐患；
- 同义词扩展；
- 多条件筛选后仍保持相关度排序。

V4 搜索效果不得低于当前生产站的有效基线。

---

## 9. 与当前 Phase 的衔接

本设计不推翻已经迁移的 642 条 Hazard，也不要求立即为历史 Hazard 全量反向补 Requirement。

当前继续：

- 642/642 conservative verified Hazard 已完成；
- 179 条 Link candidate 可以继续做 applicability review；
- Requirement 层作为 V4.1 新增正式模型，从后续“完整法规导入/法规更新”开始使用；
- 对现有 verified Clause，可在后续批次逐步回填 Requirement，不阻塞当前 Link 复核；
- Phase 7 的法规与标准核验框架必须纳入完整法规结构化、Requirement 提取和版本影响分析；
- Phase 9 Validator / Phase 10 Gate 必须增加 Requirement schema、hash、contextHash 和追溯校验；
- Phase 11～16 网站构建和验收必须增加搜索回归门禁。

---

## 10. 最终质量原则

1. 法规全文可以批量拆 Clause，但不得批量把 AI 解释直接 verified；
2. Clause → Requirement 可以批量生成 candidate，但必须保留原文追溯；
3. Requirement → Hazard 必须先查重，优先复用；
4. Hazard → Clause Link applicability 必须独立核验；
5. 法规原文、AI 提炼、现场隐患三层严格分开；
6. 搜索可以宽召回，但 verified 必须严门禁；
7. 找不到可靠结论时保持 pending；
8. 完整法规的价值以“被转化成多少可靠、可执行、可追溯的检查知识”衡量，而不是以生成了多少条 Hazard 衡量。
