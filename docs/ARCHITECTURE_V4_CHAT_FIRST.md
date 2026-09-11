# Safety Basis V4 Chat-first 架构设计

> 状态：Phase 2 正式设计稿（已完成二次架构校验）  
> 日期：2026-09-10  
> 工作分支：`chat-v4`  
> 设计目标：完整保留 V3 有价值知识资产，同时把日常维护入口改造成 Chat 可以直接理解、审阅、修改、验证和提交的 Git-first 知识工程体系。

---

## 1. 设计结论

V4 不推倒 V3 的知识模型，但改变“谁是日常维护入口”和“什么才是发布硬门禁”。

继续保留：

- Stable ID；
- 隐患、法规身份、法规版本、条款、隐患—条款关联分离；
- 同一条款复用；
- jurisdiction 独立建模；
- 新旧法规版本并存；
- law succession；
- 来源/证据可追溯；
- pending 与 verified 隔离；
- release 只读派生；
- 候选 release 与生产选择分离。

关键改变：

1. **Git 中结构化知识文件成为 Chat 的正式维护面。**
2. **SQLite 从日常唯一写入母库降级为 V3 冻结资产、首次迁移来源、批量分析工具和可选派生索引。**
3. **Git commit / PR diff 成为日常版本审计主轴。**
4. **review 只绑定“被审阅实体本身的 canonical 内容 hash”，不再计算跨实体 dependencyHash。**
5. **链式正确性通过逐节点 gate 保证：law、version、clause、link 各自必须通过；上游实体变化不会机械重算所有下游 proof，但会因为上游 review 失效而自然阻断整条链。**
6. **证据原件哈希、归档文件是否还在、复核日期等转为审计增强或软警告，不再默认等同于内容错误。**
7. **完整法规/标准全文不是发布隐患的统一前置条件；已可靠核验的具体条款可以独立使用。**
8. **网站继续读取自动生成的 release，不直接读取维护源。**

一句话定义：

> **Git-first 维护 + Stable-ID 关系知识 + 实体级审阅绑定 + 内容型硬门禁 + 可选证据增强 + 自动 release + 静态网站。**

---

## 2. V3 为什么不原样延续

V3 采用 SQLite 规范化母库、verification proof、entity revision、dependency hash、evidence archive hash 和严格链式 gate。它对本地 Code Agent 很严谨，但对跨轮 Chat 日常维护存在结构性成本：

- Chat 很难把本地 SQLite 事务长期作为稳定、可见的编辑界面；
- 一个小修改可能造成 dependency hash 级联失效；
- evidence 原件搬动、重处理或哈希变化可能把技术一致性失败表现为内容不可发布；
- 每个实体都要求完整 proof/evidence 绑定，简单修改产生大量机械维护；
- 公开知识和私有全文/企业来源耦合过重；
- SQLite、Git、exchange、proof、release 形成多套状态，需要专门 Code Agent 才容易操作。

V4 将能力重新分层：

- **知识真值层**：内容是什么；
- **审阅状态层**：当前内容是否已确认；
- **证据增强层**：核验依据在哪里；
- **发布门禁层**：是否允许进入 release；
- **审计层**：Git 历史、release hash、可选 evidence snapshot/hash。

---

## 3. V4 权威层级

### 3.1 日常正式维护源

```text
knowledge/
```

这是 V4 Chat 日常读写的正式知识区。

### 3.2 V3 SQLite

`source/master/safety.sqlite3` 在切换前仍是 **V3 事实源**，不得删除、覆盖或边迁移边改写。

V4 切换后其角色变为：

- V3 冻结基线；
- 首次迁移来源；
- 对账与回溯来源；
- 批量统计/复杂查询工具；
- 可选生成临时索引。

它不再是 V4 日常新增/修改知识的必经写入口。

### 3.3 release

release 永远是自动派生结果，不能成为第二母库人工维护。

### 3.4 网站 data

manifest、search-index、law-index、hazard/clause shards 均是构建产物，不是知识源。

---

## 4. 目标目录

```text
knowledge/
  manifest.json
  hazards/
    H001.json
  laws/
    L001.json
  law-versions/
    LV_xxx.json
  clauses/
    C001.json
  links/
    LK_xxx.json
  successions/
    LS_xxx.json
  reviews/
    hazards/
    laws/
    law-versions/
    clauses/
    links/
  evidence/
    EV_xxx.json
  provenance/
    public/

private/                 # 概念目录，不进入公开 Git
  evidence/
  source-index/
  enterprise-material/

releases-v4/
  <releaseId>/
    release.json
    gate-report.json
    warnings.json
    site/

tools/v4/
  validate.py
  gate.py
  build_release.py
  build_site.py
  migrate_v3.py
  compare_v3_v4.py

docs/
  CHAT_HANDOFF.md
  ARCHITECTURE_V4_CHAT_FIRST.md
  GATE_V4.md
  MIGRATION_V3_TO_V4.md
```

迁移期不删除现有 `source/`、`content/`、`data/` 或 `tools/pipeline/`。

---

## 5. 文件格式：一实体一 JSON

V4 正式维护源优先使用 UTF-8 pretty-printed JSON，每个核心实体一个文件。

理由：

- Chat/GitHub 可直接读改；
- JSON 语义明确；
- diff 小、冲突面小；
- Stable ID 可直接作为文件名；
- Python 标准库即可解析；
- 一个实体损坏不会拖垮整个大文件；
- Git 历史天然记录变化。

不使用单一 `master.json`；1000+ hazard、2600+ clause 会导致巨大 diff 和高冲突。

Excel 继续作为批量查看、导入/导出和人工审阅界面，但不是第二事实源。

---

## 6. 核心实体

### 6.1 hazard

```json
{
  "id": "H015",
  "title": "配电箱前操作空间不足",
  "description": "……",
  "measures": "……",
  "category": "电气安全",
  "conditions": ["……"],
  "places": ["生产车间"],
  "keywords": ["配电箱", "操作空间"],
  "aliases": [],
  "mode": "general",
  "lifecycle": "active",
  "mergedInto": null
}
```

核验状态不混进 hazard 内容文件，而在 review sidecar 中维护。

### 6.2 law

```json
{
  "id": "L001",
  "canonicalName": "……",
  "documentKind": "法律",
  "issuer": "……",
  "jurisdictionCode": "CN",
  "aliases": []
}
```

同一法规身份只建一次。

### 6.3 law version

```json
{
  "id": "LV_xxx",
  "lawId": "L001",
  "versionKey": "2021修正",
  "officialName": "……",
  "documentNumber": "……",
  "effectiveDate": "2021-04-29",
  "endDate": null,
  "validityStatus": "active",
  "sourceUrl": "https://……"
}
```

`validityStatus` 标准值：`active`、`upcoming`、`repealed`、`unknown`。

版本效力与内容审阅分开。

### 6.4 clause

```json
{
  "id": "C014",
  "lawVersionId": "LV_xxx",
  "articlePath": "第二十八条",
  "quote": "……法规原文……",
  "sourceUrl": "https://……"
}
```

规则：

- 必须指向明确 lawVersion；
- 同一版本同一定位不得存在互相冲突的 active clause；
- 没有可靠原文保持 pending，不编造；
- 不要求先取得整部标准全文才能保存/核验一个可靠条款。

### 6.5 link

```json
{
  "id": "LK_xxx",
  "hazardId": "H015",
  "clauseId": "C014",
  "role": "direct",
  "priority": 100,
  "jurisdictionCode": "CN",
  "applicability": "……适用条件……",
  "lifecycle": "active"
}
```

link 是最重要的语义实体之一。

“条款原文正确”不等于“该条款适用于这个隐患”。关联适用性必须独立审阅，禁止只靠关键词、同法规或同章节自动 verified。

### 6.6 succession

继续保留法规版本替代关系：`replaces`、`partially_replaces`、`amends`、`supersedes`、`related`。

法规更新优先改版本关系和 link 状态，不在大量 hazard 文本里机械替换标准号。

---

## 7. Review sidecar：实体级内容绑定

V4 review 记录当前审阅结论，并**必须绑定被审阅实体当前 canonical 内容**。

示例：

```json
{
  "entityType": "clause",
  "entityId": "C014",
  "decision": "verified",
  "reviewType": "text",
  "reviewedContentHash": "<canonical entity sha256>",
  "checkedAt": "2026-09-10T00:00:00+09:00",
  "reviewer": "ChatGPT",
  "evidenceRefs": ["EV_xxx"],
  "locator": "第二十八条",
  "note": "与官方文本逐字核对"
}
```

推荐 `decision`：

- `verified`
- `pending`
- `rejected`
- `superseded`

### 7.1 reviewedContentHash 是硬绑定

validator/gate 对实体重新 canonicalize 后计算 hash：

- 当前 hash = `reviewedContentHash`：review 可以使用；
- 当前 hash ≠ `reviewedContentHash`：review 立即视为 stale，实体不能按 verified 发布。

这样解决“实体改了但旧 review 仍放行”的漏洞。

### 7.2 为什么不恢复 V3 dependencyHash

V4 **只 hash 本实体，不 hash 跨实体依赖图**。

例如：

- C014 文本修改 → 只让 C014 的 review stale；
- H015 review 和 LK001 review 不被机械改写；
- 但发布 H015 时链式 gate 必须经过 C014，因此 H015 仍会被自然阻断；
- C014 复核后，整条链恢复，无需重新制造所有下游 dependency hash。

这保留安全性，同时消除 V3 大面积级联失效。

可选字段 `reviewedCommit` 可以额外记录核验时 Git commit，但不是 reviewedContentHash 的替代品。

---

## 8. Evidence：内容证据与技术归档分离

### A. 官方公开证据

```json
{
  "id": "EV_xxx",
  "type": "official-web",
  "url": "https://……gov.cn/……",
  "locator": "第二十八条",
  "retrievedAt": "2026-09-10T00:00:00+09:00"
}
```

### B. 私有合法原件

适用于购买标准、内部持有 PDF 等。公开 Git 只记录最小元数据和私有引用 ID，不放原件、不放企业路径、不放受限全文：

```json
{
  "id": "EV_private_xxx",
  "type": "private-source",
  "citation": "GB XXXX-XXXX 第 X.X 条",
  "privateRef": "PRIVATE-EVIDENCE-001",
  "publiclyRedistributable": false
}
```

### C. 二手/辅助来源

可用于找线索、解释和交叉比对，但不得单独支撑关键法规原文 verified。

`sha256`、snapshotRef、archiveOk 可继续作为可选证据字段。

---

## 9. Fulltext 的角色

`fulltext.sqlite3` 和历史全文归档保留，但 V4 明确：

> **全文是检索/证据能力，不是每条隐患进入网站的统一硬门槛。**

只要：

- 法规身份正确；
- 版本正确且在 asOf 有效；
- 具体条款定位正确；
- 条款原文可靠；
- hazard—clause 适用性确认；

即可发布该依据。

这避免付费标准、扫描 PDF、OCR 或官方仅公开部分内容时拖死整个知识生产流程。

---

## 10. V4 门禁架构原则

Phase 3 单独形成 `docs/GATE_V4.md`；本节冻结原则。

### 10.1 硬门禁

至少包括：

- JSON/schema 合法；
- Stable ID 唯一；
- 外键完整；
- 内容文件与 review 的 `reviewedContentHash` 一致；
- hazard 公共字段完整；
- law identity verified；
- law version verified 且效力明确；
- asOf 日期处于有效期间；
- clause text/locator verified；
- link applicability verified；
- hazard 至少一个可用 link；
- 待核验内容不进入正式 release；
- 已失效 link 不支撑当前 hazard；
- upcoming 版本实施日前不作为当前隐患定性依据；
- 私有企业资料、内部路径、受限全文不得泄漏。

### 10.2 软警告

默认不阻断：

- evidence snapshot 丢失；
- snapshot hash 不一致；
- reviewDue 到期；
- official URL 临时失效；
- evidence 没有本地归档副本；
- reviewedCommit 未记录；
- 可选全文缺失；
- 技术索引需要重建。

### 10.3 绝不能放软

- 条款是否是真实原文；
- locator 是否准确；
- 法规版本是否有效；
- hazard—clause 是否确实适用；
- review 是否对应当前实体内容；
- 是否存在隐私/受限内容泄漏。

---

## 11. Git 审计主轴

V4 每次知识修改都应形成小范围 Git diff：

```text
读取 CHAT_HANDOFF
  ↓
定位实体及关联实体
  ↓
修改 knowledge 文件
  ↓
旧 review 因 reviewedContentHash 不匹配自动 stale
  ↓
必要时重新核验并更新 review
  ↓
validate
  ↓
gate candidate
  ↓
生成候选 release
  ↓
校验 diff / counts / privacy
  ↓
提交工作分支
  ↓
更新 CHAT_HANDOFF
```

Git 历史提供修改人、commit、前后 diff 和回滚能力，因此不再为普通文本变化维持一套与 Git 重复的 change_set 体系。

---

## 12. Chat 日常操作规范

每轮必须：

1. 读 `docs/CHAT_HANDOFF.md`；
2. 确认分支/HEAD；
3. 确认上轮任务状态；
4. 只加载本轮需要的实体和关联；
5. 修改后运行 validator；
6. 涉及发布内容时运行 gate；
7. 不直接改 `main`；
8. 不直接改生产 selection；
9. 更新 handoff 后结束。

跨聊天续建由仓库状态驱动，不依赖模型记忆。

---

## 13. 并发与批量质量

- 每个任务使用独立工作分支或明确共享工作分支；
- 不让多个 AI 同时无协调修改同一实体；
- 批量任务先产出候选，不直接一次升级数千条 verified；
- 合并前重跑 validator/gate；
- 冲突按实体语义审阅，不做最后写入覆盖；
- 不确定内容保持 pending；
- 禁止共享一个 evidence/模板结论冒充逐条适用性核验。

r8 质量事故是明确反例。

---

## 14. Release V4

建议结构：

```json
{
  "formatVersion": "safety-release-v4",
  "asOf": "2026-09-10",
  "sourceCommit": "<git commit>",
  "releaseHash": "<sha256>",
  "graph": {
    "hazards": [],
    "laws": [],
    "lawVersions": [],
    "clauses": [],
    "links": []
  },
  "reviewSummary": {},
  "warnings": []
}
```

`releaseHash` 继续保留，用于确定网站实际发布的是哪一包。

V3 `sourceStateHash` 可由 Git tree/commit 或 canonical knowledge tree hash 替代，不再绑定 SQLite 全库事务状态。

---

## 15. 网站兼容策略

V4 第一阶段不重写前端。

构建器将 V4 release 适配为现有前端需要的：

- schemaVersion=2 manifest；
- search-index；
- law-index；
- hazard shards；
- clause shards。

这样先更换维护架构，再单独决定是否升级 UI，降低生产切换风险。

---

## 16. V3 → V4 迁移原则

Phase 4 写字段映射；Phase 5 做只读原型。当前冻结：

1. V3 Stable ID 原样保留，除非明确冲突；
2. V3 pending 不自动升级；
3. r8 批量错误结论不得恢复；
4. V3 verification 历史归档保留，但迁入 V4 时提炼当前有效 review，不复制全部 dependencyHash；
5. 首次生成 `reviewedContentHash` 时必须基于迁移后 canonical entity 内容计算；
6. evidence 保留可用 metadata，私有原件不进入公开 Git；
7. law succession 保留；
8. merged entity 保留旧 ID 和去向；
9. r10 是候选发布对比样本，不取代 SQLite 作为 V3 迁移事实源；
10. 首次迁移只读导出，不反写 V3 SQLite；
11. V4 首批 release 必须和 V3 r10 做逐项差异报告。

---

## 17. 最小工具链

### `validate.py`

负责 JSON/schema、ID、外键、duplicate、lifecycle、图完整性、reviewedContentHash 和隐私字段检查。

### `gate.py`

负责法规效力、review decision、条款文本/定位、link applicability、hard/soft 分类。

### `build_release.py`

只从通过硬门禁的 graph 生成 release。

### `build_site.py`

把 release 转成网站 manifest/index/shards。

### `migrate_v3.py`

只读 V3 SQLite，输出 V4 candidate knowledge，不反写 V3。

### `compare_v3_v4.py`

比较实体数量、Stable ID、字段、link、release inclusion 和数据丢失。

---

## 18. 不再作为日常必需的 V3 机制

历史保留，但不再作为 V4 日常前置：

- 每次编辑必须 SQLite exchange/propose/apply；
- 每实体整数 revision；
- 跨实体 dependencyHash；
- evidence archive 文件存在且哈希完全一致才允许发布；
- 完整法规/标准全文已归档才允许发布具体可靠条款；
- 大量本地临时修复脚本作为正常业务流程；
- Excel 必须作为中间状态。

注意：**实体级 `reviewedContentHash` 仍是 V4 硬门禁。** 它解决审阅陈旧问题，但不会产生跨图级联。

---

## 19. 必须保留的 V3 机制

- Stable ID；
- law / lawVersion 分离；
- clause 属于具体版本；
- hazard / clause 多对多；
- link applicability；
- law succession；
- pending / verified 隔离；
- release ≠ production；
- 私有/公开隔离；
- 来源可追溯；
- 不编造法规原文；
- upcoming ≠ active；
- 旧版条文不得冒充新版；
- 批量置信度不得自动升级为 verified。

---

## 20. 当前版本安全约束

截至本设计稿：

- Drive 本地 V3：`data-verify-batch-003 @ ecd76fa...`；
- GitHub 远端同名分支：`2b895ea...`；
- `chat-v4` 创建自远端旧基线；
- `main` 更旧；
- 最新候选 release 为 r10；
- 生产 selection 仍为 r4。

因此：

> **Phase 2/3/4 可以在 `chat-v4` 做独立设计；Phase 5 进入真实迁移代码前，必须解决 Drive 未推送历史与 GitHub 的安全对账。**

不能假装 `chat-v4` 当前旧源码就是最新 V3 源码后直接重构生产代码。

---

## 21. Phase 2 验收结论

本设计明确回答：

- V4 日常正式维护源：**Git-first `knowledge/`**；
- SQLite：**保留，但不再作为 V4 日常写入口**；
- Stable ID：**保留**；
- law/version/clause/link：**保留**；
- verification：**重构为 review + evidence + Git audit**；
- review 与当前内容绑定：**使用实体级 reviewedContentHash，硬门禁**；
- 跨实体 dependencyHash：**取消**；
- evidence archive hash：**默认软警告**；
- clause text / locator / version validity / link applicability：**硬门禁**；
- 完整全文：**不是统一硬门禁**；
- releaseHash：**保留**；
- 网站：**先 adapter 兼容，不立即重写**；
- 数据迁移：**Phase 4 映射、Phase 5 只读原型之后**；
- 生产切换：**必须用户批准**。

Phase 2 架构设计完成。

---

## 22. 下一步

进入 **Phase 3：`docs/GATE_V4.md`**。

Phase 3 要把上述原则落成可执行矩阵，明确：

- 各实体硬门禁；
- reviewedContentHash 规范与 canonicalization；
- 软警告；
- upcoming/repealed；
- 私有标准证据；
- review sidecar；
- link applicability；
- release 失败条件；
- 隐私扫描；
- 用户 override 边界。

Phase 3 仍不做大规模正式数据迁移。