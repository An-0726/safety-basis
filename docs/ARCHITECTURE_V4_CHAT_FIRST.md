# Safety Basis V4 Chat-first 架构设计

> 状态：Phase 2 正式设计稿  
> 日期：2026-09-10  
> 工作分支：`chat-v4`  
> 设计目标：在完整保留 V3 有价值知识资产的前提下，把日常维护入口改造成 Chat 可以直接理解、审阅、修改、验证和提交的 Git-first 知识工程体系。

---

## 1. 设计结论

V4 不推倒 V3 的知识模型，但改变“谁是日常维护入口”和“什么才是发布硬门禁”。

V3 的核心优点继续保留：

- Stable ID；
- 隐患、法规身份、法规版本、条款、隐患—条款关联分离；
- 同一条款复用而不是在每个隐患里重复复制；
- 国家、江苏、南京等 jurisdiction 独立建模；
- 新旧法规版本并存；
- 证据与来源可追溯；
- release 是只读派生结果；
- 生产选择与候选 release 分离。

V4 的关键改变：

1. **Git 中的结构化知识文件成为 Chat 的正式维护面。**
2. **SQLite 从“日常唯一写入母库”降级为 V3 冻结资产、迁移来源、批量分析工具和可选派生索引，不再要求每次日常修改都经本地事务脚本。**
3. **Git commit / PR diff 取代大量手工 revision、change_set 和 dependency_hash，作为日常版本审计主轴。**
4. **发布硬门禁只拦内容正确性、法规效力、条款定位、关联适用性、字段完整性和隐私泄漏等真正影响公开质量的问题。**
5. **证据文件哈希、归档文件是否还在、复核日期、技术依赖 hash 等保留为审计增强或软警告，不再默认等同于内容错误。**
6. **完整法规/标准全文不是发布隐患的前置条件。** 已可靠核验的具体条款可以独立使用；全文库继续作为可选私有证据资产。
7. **网站继续吃自动生成的 release，不直接读取维护源。**

一句话定义 V4：

> **Git-first 维护 + Stable-ID 关系知识 + 独立审阅状态 + 内容型硬门禁 + 可选证据增强 + 自动 release + 静态网站。**

---

## 2. 为什么 V3 不直接原样延续

V3 当前采用 SQLite 规范化母库、verification proof、entity revision、dependency hash、evidence archive hash 和严格链式 gate。该设计对本地 Code Agent 很严谨，但对跨轮 Chat 日常维护有几个结构性问题：

- Chat 很难把本地 SQLite 事务作为长期、稳定、可见的日常编辑界面；
- 一次很小的实体修改可能导致 dependency hash 大面积失效；
- evidence 原件搬动、重处理或哈希变化可能把“技术一致性失败”表现为“内容不能发布”；
- 每个实体都要求完整 proof/evidence 绑定，使简单修改产生大量机械性维护；
- 公开知识和私有全文/企业来源耦合过重；
- 本地脚本、SQLite、Git 和 release 之间存在多套状态，需要专门 Code Agent 才容易安全操作。

V4 不否定 V3 的审计价值，而是把这些能力重新分层：

- **知识真值层**：回答“内容是什么、依据是什么、适用于什么场景”；
- **审阅状态层**：回答“这个实体/关联是否已确认”；
- **证据增强层**：回答“核验时看过什么、在哪里、是否有快照”；
- **发布门禁层**：只决定能否公开；
- **审计层**：Git 历史、release hash、可选 snapshot hash 用于追溯，不反过来机械否定已核实内容。

---

## 3. V4 权威层级

### 3.1 正式维护源

V4 正式维护源拟放在：

```text
knowledge/
```

它是 Chat 日常读写的结构化知识区。

### 3.2 V3 SQLite 的地位

`source/master/safety.sqlite3` 在迁移完成前仍是 **V3 事实源**，不得删除、覆盖或改写；进入 V4 后其角色变为：

- V3 冻结基线；
- V3 → V4 首次迁移来源；
- 对账与回溯来源；
- 批量统计/复杂查询工具；
- 必要时生成临时索引。

V4 正式切换后，日常新增或修改知识不再要求先写 SQLite 再导出 Git 文件。

### 3.3 release 的地位

`releases/` 或迁移期 `source/releases/` 仍然只保存 **自动派生、不可人工作为第二母库维护** 的发布快照。

### 3.4 网站数据的地位

`data/manifest.json`、search index、law index、hazard/clause shards 仍是构建产物，不是知识源。

---

## 4. 建议目录结构

V4 目标目录：

```text
knowledge/
  manifest.json
  hazards/
    H001.json
    H002.json
  laws/
    L001.json
    LF_xxx.json
  law-versions/
    LV_xxx.json
  clauses/
    C001.json
    C002.json
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

private/                 # 不进入公开仓库；仅作为概念目录
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

迁移期不立刻删除现有 `source/`、`content/`、`data/` 或 `tools/pipeline/`。

---

## 5. 为什么采用“一实体一 JSON 文件”

V4 维护源优先使用 UTF-8、pretty-printed JSON，每个核心实体一个文件。

原因：

- Chat 和 GitHub 都能直接读取和修改；
- JSON 语义明确，不依赖本地数据库驱动；
- 每次修改 diff 小，冲突范围有限；
- Stable ID 可以直接作为文件名；
- 可用 JSON Schema 或 Python 标准库严格校验；
- 不要求引入 YAML 解析器；
- 一个实体损坏不会让整批 JSONL 无法定位；
- Git 历史天然记录每个实体的变化。

不采用“一个超大 master.json”，因为 1000+ 隐患和 2600+ 条款会让 Chat 每轮修改成本、冲突风险和 diff 噪声过高。

不采用 Excel 作为 V4 唯一母库，因为多实体关系、Stable ID、历史版本、外键和多人/多 AI 并发修改仍不适合 Excel 直接承担。

Excel 可以继续作为查看、批量审阅和导入/导出界面，但不是第二事实源。

---

## 6. 核心实体模型

### 6.1 hazard

示例：

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

V4 不把“已核验”直接混进 hazard 内容文件。核验状态放 review sidecar，避免内容状态和内容本身互相污染。

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

`validityStatus` 推荐标准值：

- `active`
- `upcoming`
- `repealed`
- `unknown`

法规版本状态与“内容是否核验”继续分开。

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

硬规则：

- 必须指向明确 lawVersion；
- 同一版本同一定位不得存在两个互相冲突的 active clause；
- 没有可靠原文就保持 pending，不编造；
- 不要求为了保存这一条 clause 先取得整部标准全文。

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

link 是 V4 最重要的语义实体之一。

“条款原文正确”不等于“该条款适合这个隐患”。因此关联适用性必须独立审阅，禁止仅因关键词、法规名称或同一章节而自动升级为 verified。

### 6.6 succession

继续保留法规版本替代关系，支持：

- replaces
- partially_replaces
- amends
- supersedes
- related

这样法规更新时优先改版本关系和 link 状态，不在几百个 hazard 文本里机械改标准号。

---

## 7. Review sidecar：用“当前审阅结论”替代复杂 proof 绑定

V4 把当前审阅结论放在独立 sidecar：

```json
{
  "entityType": "clause",
  "entityId": "C014",
  "decision": "verified",
  "reviewType": "text",
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

V4 不要求 sidecar 自带 `entityRevision + dependencyHash` 才能生效。原因是 Git commit 已经承担了内容版本历史；validator 可以检查 review 引用对象是否存在，gate 只看当前 review 是否足够支持发布。

如果后续确有必要，可以在 review 中增加可选 `reviewedCommit`，用 Git commit SHA 精确指向核验时版本，但它应是增强审计，不是所有数据日常更新的机械前置条件。

---

## 8. Evidence：证据保留，但不再强制“全文原件 + 哈希”

V4 evidence 设计分三级：

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

适用于购买标准、内部持有 PDF 等。

公开 Git 中只记录最小元数据和私有引用 ID，不放原件、不放企业路径、不放受限全文：

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

可作为找线索、比对或解释，但不得单独支撑关键法规原文 verified。

`sha256`、snapshotRef、archiveOk 等字段可以继续存在，但改为可选增强字段。

---

## 9. Fulltext 在 V4 中的角色

`fulltext.sqlite3` 和历史全文归档不删除。

但 V4 明确：

> **全文是证据能力和检索能力，不是每条隐患进入网站的统一硬门槛。**

只要：

- 法规身份正确；
- 版本正确且当前有效；
- 具体条款定位正确；
- 条款原文已可靠核对；
- hazard—clause 适用性已确认；

即可发布该依据。

这解决付费标准、扫描 PDF、OCR 难题或官方网页只公开部分条款时，整个知识库被“全文未完成”拖死的问题。

---

## 10. V4 门禁分层原则

Phase 3 将单独形成 `docs/GATE_V4.md`，本文件只冻结架构原则。

### 10.1 硬门禁：内容与公开安全

硬门禁至少覆盖：

- JSON/schema 合法；
- Stable ID 唯一；
- 外键完整；
- hazard 公共字段完整；
- law identity 已确认；
- law version 效力明确且在 asOf 日期有效；
- clause 定位和原文已确认；
- link 适用性已确认；
- hazard 至少有一个可用依据 link；
- 禁止待核验内容混入正式 release；
- 禁止私有企业资料、内部路径、受限全文泄漏；
- 禁止已失效 link 支撑当前 hazard；
- 禁止 upcoming 版本在实施日前作为当前违法/隐患定性依据。

### 10.2 软门禁：审计增强

默认只警告：

- evidence snapshot 丢失；
- snapshot hash 不一致；
- reviewDue 到期；
- official URL 临时失效；
- evidence 没有本地归档副本；
- reviewedCommit 未记录；
- 技术索引需要重建；
- 可选全文缺失。

### 10.3 绝不能放软的项

与旧“分级门禁方案”相比，V4 明确以下不能因为“技术上麻烦”而放软：

- clause 是否是真实原文；
- clause locator 是否准确；
- law version 是否有效；
- hazard—clause 是否确实适用；
- 是否存在私有信息泄漏。

---

## 11. Git 作为 V4 审计主轴

V4 每次知识修改都应体现为小范围 Git diff。

推荐流程：

```text
读取 CHAT_HANDOFF
  ↓
定位目标实体文件
  ↓
读取关联 law/version/clause/link/review
  ↓
修改少量 knowledge 文件
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

Git 历史天然提供：

- 谁改了什么；
- 哪次 commit 改的；
- 修改前后 diff；
- 可回滚版本；
- PR/Review 记录。

因此不再需要为每个普通文本字段变化额外制造一套与 Git 重复的变更流水账。

---

## 12. Chat 日常操作规范

每一轮 Chat 开工必须：

1. 读取 `docs/CHAT_HANDOFF.md`；
2. 确认当前分支和 HEAD；
3. 确认上轮任务是否完整结束；
4. 只读取本轮涉及的知识实体和关联实体；
5. 修改后运行 validator；
6. 涉及可发布内容时运行 gate；
7. 不直接改 `main`；
8. 不直接改生产 selection；
9. 更新 handoff 再结束。

这使跨聊天续建不依赖模型记忆。

---

## 13. 并发与冲突策略

V4 采用一实体一文件后，并发冲突主要限制在实际同时修改同一实体的场景。

规则：

- 每个任务使用独立分支或明确工作分支；
- 不在多个 AI 中同时直接修改同一个 entity file；
- 批量任务先输出候选结果，不直接一次提交数千条 verified；
- 合并前 validator 必须重新运行；
- 发生冲突时按实体语义审阅，不使用“最后写入覆盖”；
- 任何批量核验都必须保留 pending，而不是为了提高通过率自动强配。

r8 的质量事故被视为 V4 的反例：批量生成大量关联和共享证据不能替代逐条适用性判断。

---

## 14. Release V4

建议 V4 release 继续采用关系 graph，但缩减 proof 技术负担：

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

`releaseHash` 继续保留，因为它对“这次网站发布的到底是哪一包内容”非常有价值。

`sourceStateHash` 可由 Git tree/commit 或 canonical knowledge tree hash 替代，不再绑定 SQLite 全库事务状态。

---

## 15. 网站兼容策略

V4 第一阶段不要求重写网站前端。

迁移器/构建器可将 `safety-release-v4` 适配为现有前端需要的：

- schemaVersion=2 manifest；
- search-index；
- law-index；
- hazard shards；
- clause shards。

优点：

- 先替换维护架构，不同时重写数据层和 UI；
- V3/V4 可以用相同网站页面做 A/B 对比；
- 生产切换风险小；
- 未来再单独升级前端契约。

---

## 16. V3 → V4 迁移原则

Phase 4 才写正式字段映射；Phase 5 才做只读迁移原型。

当前先冻结以下原则：

1. V3 Stable ID 原样保留，除非有明确冲突；
2. 不把 V3 pending 自动升级为 verified；
3. r8 批量错误结论不得恢复；
4. V3 verification 历史可以归档，但迁移到 V4 时只提炼“当前可依赖审阅结论”，不强行复制全部 dependency hash；
5. evidence 保留可用 metadata，私有原件不进入公开 Git；
6. law succession 必须保留；
7. merged entity 保留旧 ID 和去向；
8. r10 用作候选发布对比样本，不取代 SQLite 作为 V3 迁移事实源；
9. 首次迁移必须是只读导出，禁止边迁移边修改 V3 SQLite；
10. V4 首批 release 必须与 V3 r10 做逐项差异报告。

---

## 17. V4 最小工具链

目标不是继续扩张工具数量，而是把核心流程收敛到少数可理解工具：

### `validate.py`

负责：

- JSON 解析；
- schema；
- ID；
- foreign key；
- duplicate；
- lifecycle；
- law/version/clause/link 图完整性；
- 隐私字段检查。

### `gate.py`

负责：

- 当前法规效力；
- review decision；
- clause text/locator；
- link applicability；
- hard/soft gate 分类。

### `build_release.py`

只从通过硬门禁的 knowledge graph 生成 release。

### `build_site.py`

把 release 转为网站 manifest/index/shards。

### `migrate_v3.py`

只读读取 V3 SQLite，输出 V4 candidate knowledge；不反写 V3。

### `compare_v3_v4.py`

比较：

- 实体数量；
- Stable ID；
- 字段差异；
- link 差异；
- release inclusion 差异；
- 可能的数据丢失。

---

## 18. 不再作为 V4 日常必需品的 V3 机制

以下机制不直接删除历史，但不再作为 V4 日常主流程的必要前置：

- 每次编辑都走 SQLite exchange/propose/apply；
- 每个实体都维护整数 revision；
- 每个核验都必须计算 dependency hash；
- 每次发布都要求 evidence archive 文件存在且哈希完全一致；
- 每条发布内容都要求完整法规/标准全文已归档；
- 用大量本地临时 Python 修复脚本作为正常业务流程；
- Excel 作为必须经过的中间状态。

它们需要时仍可以作为专项工具使用。

---

## 19. 必须继续保留的 V3 机制

以下不能因为“Chat-first”而简化掉：

- Stable ID；
- law 与 lawVersion 分离；
- clause 归属于具体版本；
- hazard 与 clause 多对多；
- link 适用性；
- law succession；
- pending / verified 明确隔离；
- release 不等于生产；
- 私有/公开严格隔离；
- 原始来源可追溯；
- 不编造法规原文；
- 不把 upcoming 当 active；
- 不把旧版条文冒充新版条文；
- 不因批量匹配置信度高就自动升级为 verified。

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

> **Phase 2、Phase 3、Phase 4 可以继续在 `chat-v4` 做文档和独立 V4 设计；Phase 5 进入真实迁移代码前，必须先解决 Drive 未推送历史与 GitHub 的安全对账。**

不能在当前 `chat-v4` 上假装其旧源码就是最新 V3 源码，然后直接重构生产代码。

---

## 21. Phase 2 验收标准

本设计稿完成以下问题的明确回答，即 Phase 2 可视为完成：

- V4 谁是日常正式维护源：**Git-first `knowledge/`**；
- SQLite 是否删除：**否，保留为 V3 冻结/迁移/查询资产，但不再作为 V4 日常写入口**；
- Stable ID 是否保留：**保留**；
- law/version/clause/link 关系是否保留：**保留**；
- verification 是否原样保留：**不原样照搬，拆为 review + evidence + Git audit**；
- dependency hash 是否继续硬门禁：**否**；
- evidence archive hash 是否继续硬门禁：**默认否**；
- clause text、locator、version validity、link applicability 是否硬门禁：**是**；
- 完整全文是否发布前强制：**否**；
- release hash 是否保留：**是**；
- 网站是否立即重写：**否，先用 adapter 保持兼容**；
- 是否立即迁移数据：**否，Phase 4 映射、Phase 5 只读原型后再决定**；
- 是否切生产：**否，必须用户另行批准**。

---

## 22. 下一步

Phase 2 完成后，下一轮进入：

**Phase 3：`docs/GATE_V4.md`**

重点把本文件的门禁原则落成可执行检查矩阵，明确：

- entity/type 级硬门禁；
- 软警告；
- upcoming/repealed 版本处理；
- 私有标准证据；
- review sidecar 判定；
- link applicability；
- release 构建失败条件；
- 隐私扫描；
- 用户手工 override 的边界。

Phase 3 仍不做大规模正式数据迁移。