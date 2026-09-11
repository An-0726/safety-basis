# Safety Basis V4 发布门禁设计

> 状态：Phase 3 正式设计稿  
> 日期：2026-09-10  
> 前置架构：`docs/ARCHITECTURE_V4_CHAT_FIRST.md`  
> 原则：门禁首先保证公开内容真实、有效、适用、无隐私泄漏；技术审计能力保留，但不得把纯技术问题机械等同于内容错误。

---

## 1. Gate V4 总结

V4 采用六阶段发布门禁：

```text
Stage 0  文件解析与 canonicalization
Stage 1  Schema / ID / 外键 / 唯一性
Stage 2  Review 当前性绑定
Stage 3  实体级内容门禁
Stage 4  Hazard → Link → Clause → LawVersion → Law 链式门禁
Stage 5  隐私与公开投影门禁
Stage 6  Release 一致性与确定性校验
```

输出分为：

- `BLOCK`：硬门禁失败，不进入正式 release；
- `WARN`：可进入 release，但在 `warnings.json` 和 gate report 中记录；
- `PASS`：通过。

V4 不提供普通的 `--force` 绕过硬门禁。

---

## 2. Canonical JSON 与内容 Hash

### 2.1 为什么必须有 reviewedContentHash

只保存 `decision=verified` 不够。实体在核验后被修改，如果 review 不和当前内容绑定，旧结论会错误继续有效。

V4 因此保留 **实体级内容 hash**，但取消 V3 的通用跨实体 `dependencyHash`。

### 2.2 canonicalization 规范

对每个 entity：

1. JSON 必须 UTF-8；
2. 禁止 duplicate object key；
3. 先按 schema 解析为数据对象；
4. 不把源文件的缩进、空格、对象 key 顺序纳入语义；
5. 对象 key 递归按 Unicode code point 排序；
6. JSON 输出使用 `ensure_ascii=false`、无多余空格、`allow_nan=false`；
7. 字符串内容不自动 trim，不做同义替换，不改变法规原文；
8. 数组默认保留顺序；
9. `aliases`、`places`、`keywords` 属于集合型字段，计算 hash 时按字符串排序，且 validator 要求无重复值；
10. `conditions`、其他叙事数组保持原顺序。

等价 Python 目标语义：

```python
json.dumps(
    canonical_object,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
)
```

### 2.3 reviewedContentHash

```text
reviewedContentHash = sha256(canonical_json(entity).encode("utf-8")).hexdigest()
```

必须是小写 64 位十六进制。

### 2.4 绑定判定

- 当前 entity hash 与 review 中 `reviewedContentHash` 相同：review 可继续使用；
- 不同：`BLOCK_REVIEW_STALE`；
- review 缺 hash：`BLOCK_REVIEW_UNBOUND`。

这属于硬门禁。

---

## 3. 局部语义依赖：Link contextHashes

Phase 3 对 Phase 2 做一项必要精化：

> **取消“全图 dependencyHash”不等于所有 review 都只能看自己。Link 的 applicability 本质上是 hazard 与 clause 的关系判断，因此 link review 必须显式绑定这两个语义上下文。**

link review 示例：

```json
{
  "entityType": "link",
  "entityId": "LK_001",
  "reviewType": "applicability",
  "decision": "verified",
  "reviewedContentHash": "<link hash>",
  "contextHashes": {
    "hazard": "<current hazard hash>",
    "clause": "<current clause hash>"
  },
  "checkedAt": "2026-09-10T00:00:00+09:00",
  "reviewer": "ChatGPT",
  "reason": "条款明确要求……，与该隐患事实条件直接对应",
  "evidenceRefs": ["EV_xxx"]
}
```

判定：

- link 自身 hash 变化 → link review stale；
- hazard 内容变化 → link review stale；
- clause 内容变化 → link review stale；
- lawVersion 日期/效力变化不会机械改 link review，但 lawVersion 自己的 gate 会阻断整条链；
- law 名称/issuer 等变化不会机械改 link review，但 law 自己的 gate 会阻断整条链。

这不是 V3 的通用 dependencyHash，而是 **仅对真正比较两个实体语义的 relation review 做显式上下文绑定**。

---

## 4. Review 通用规范

所有正式 review 至少：

```json
{
  "entityType": "clause",
  "entityId": "C014",
  "reviewType": "text",
  "decision": "verified",
  "reviewedContentHash": "...",
  "checkedAt": "2026-09-10T00:00:00+09:00",
  "reviewer": "ChatGPT",
  "evidenceRefs": ["EV_xxx"],
  "locator": "第二十八条",
  "reason": "..."
}
```

### 4.1 decision

允许：

- `verified`
- `pending`
- `rejected`
- `superseded`

只有 `verified` 可以支撑正式发布。

### 4.2 reviewer

正式 verified review 必须非空。

### 4.3 checkedAt

必须是带时区 ISO 8601。

### 4.4 evidenceRefs

是否强制取决于 review 类型：

| reviewType | evidenceRefs |
|---|---|
| hazard/content | 可选 |
| law/identity | 至少 1 个 authoritative evidence |
| lawVersion/version | 至少 1 个 authoritative evidence |
| clause/text | 至少 1 个 authoritative evidence |
| link/applicability | 可复用 clause evidence；至少要有明确 reason，建议至少 1 个 evidenceRef |

### 4.5 locator

- clause text review：硬要求；
- law/lawVersion：可以是文号、标题、公告页、版本定位；
- link applicability：可不单独设 locator，但 `reason` 必须具体。

---

## 5. Evidence 等级

### Tier A：authoritative-public

政府、立法机关、标准发布机关、官方标准信息页或其他明确官方公开来源。

可用于 law、lawVersion、clause 的硬门禁核验。

### Tier B：authoritative-private

合法持有的标准原件、购买版 PDF、内部授权原件等。

公开仓库仅保留：

- citation；
- locator；
- opaque `privateRef`；
- `publiclyRedistributable=false`。

Tier B 可以支撑硬门禁，但原件不得进入公开 release。

### Tier C：secondary

搜索摘要、第三方转载、博客、论坛、AI 生成内容等。

可以辅助定位，但 **不能单独支撑 law/version/clause verified**。

### Evidence 技术字段

下列默认为 WARN，不直接使内容失效：

- snapshot 文件找不到；
- snapshot sha256 不匹配；
- archiveOk=false；
- official URL 暂时 404/超时；
- 本地全文库没有整份文件。

前提是原 review 已绑定当前内容，并且存在足够的 authoritative evidence 元数据/历史核验依据。

---

## 6. Law 硬门禁

Law 表示法规/标准身份。

### BLOCK

- ID 非法/重复；
- canonicalName 为空；
- documentKind 为空或不在字典；
- issuer 为空；
- jurisdictionCode 非法；
- law review 不存在；
- law review decision != verified；
- reviewedContentHash 不匹配；
- identity review 没有 authoritative evidence；
- 当前 law 已 merged/superseded，但仍作为独立 canonical identity 发布且无目标关系；
- 与另一 active law 存在不可解释的 identityKey 冲突。

### WARN

- 别名为空；
- official URL 暂时不可访问；
- 没有本地 snapshot。

---

## 7. LawVersion 硬门禁

### 基础 BLOCK

- `lawId` 不存在；
- `versionKey` / `officialName` 为空；
- `effectiveDate` 无效；
- validityStatus 非法；
- version review 不存在/非 verified；
- reviewedContentHash 不匹配；
- 没有 authoritative evidence；
- 同一 law 下存在冲突的 active versionKey/版本身份。

### asOf 判定

#### active

作为当前 hazard 依据必须：

```text
effectiveDate <= asOf
AND (endDate is null OR asOf < endDate)
```

否则 BLOCK。

#### upcoming

可以进入“法规目录/即将生效”区域，但：

- `effectiveDate > asOf`；
- 不得支撑当前 hazard 链；
- 如果 `effectiveDate <= asOf` 仍标 upcoming：BLOCK，要求先复核效力。

#### repealed

可保留历史查询，不得支撑当前 hazard。

#### unknown

不得支撑当前 hazard；可以留在知识库 pending。

### documentNumber

法律等可能不存在传统标准号。是否强制由 documentKind schema 决定，不能一刀切要求所有 lawVersion 都必须有标准号。

---

## 8. Clause 硬门禁

### BLOCK

- `lawVersionId` 不存在；
- `articlePath` 为空；
- `quote` 为空；
- 同一 lawVersion + articlePath 存在两个冲突 active clause；
- text review 不存在/非 verified；
- reviewedContentHash 不匹配；
- locator 为空；
- 没有 Tier A/B authoritative evidence；
- quote 与 review 所核对的定位不一致；
- 明确只拿到了摘要/转述，却把 quote 标为法规原文；
- 旧版条文被挂到新版 lawVersion；
- 标准条号/条款号无法确认却标 verified。

### 不要求

- 不要求整份法规/标准全文已经导入全文库；
- 不要求 evidence snapshot 文件当前仍存在；
- 不要求公开 URL 一定可重新下载（私有合法原件可支撑）。

### quote 原则

`quote` 是法律/标准原文，不做 AI 润色。

解释文字、适用说明必须放 link applicability / note，不得混入 quote。

---

## 9. Hazard 硬门禁

### 内容 BLOCK

- ID 非法/重复；
- title 为空；
- description 为空；
- measures 为空；
- category 为空；
- mode 非法；
- lifecycle != active 且仍试图进入当前发布；
- mergedInto 非空但仍作为独立 active hazard 发布；
- content review 不存在/非 verified；
- reviewedContentHash 不匹配；
- 公开文本含企业名称、内部项目路径、个人敏感信息或受限原件内容。

### 法规链 BLOCK

hazard 至少需要 **1 条可发布的 qualifying link**。

qualifying role：

- `direct`
- `fallback`

`supporting` 不能单独支撑一个 hazard 进入 release。

一个 hazard 可以有其他 pending/失败 link；这些 link 被排除并记录 WARN，**不因为一个附加 link 未完成就把已有可靠依据的 hazard 整体杀掉**。

如果没有任何 qualifying link 通过完整链式 gate，则 hazard BLOCK。

---

## 10. Link 硬门禁

建议 role 字典：

- `direct`：直接、明确的定性/整改依据；
- `supporting`：补充说明；
- `fallback`：没有更直接专项条款时使用的上位法/通用义务兜底。

### BLOCK

- `hazardId` 不存在；
- `clauseId` 不存在；
- role 非法；
- applicability 为空；
- lifecycle != active；
- applicability review 不存在/非 verified；
- reviewedContentHash 不匹配；
- `contextHashes.hazard` 与当前 hazard hash 不匹配；
- `contextHashes.clause` 与当前 clause hash 不匹配；
- reason 为空或只是“关键词相似/同一法规”等无法说明适用性的模板结论；
- jurisdiction 与 hazard 使用场景明确冲突；
- 关联的是 upcoming/repealed/unknown version，却试图支撑当前 hazard；
- clause 本身 gate 不通过；
- lawVersion/law gate 不通过。

### fallback 额外要求

`role=fallback` 时 review.reason 必须明确：

- 它为什么是兜底依据；
- 当前没有采用更直接条款的原因或适用边界。

不要求系统证明“全世界不存在更强标准”，但不能把明显宽泛的上位法伪装成直接技术条款。

---

## 11. 链式 Gate

对每条 candidate link：

```text
link
  → clause
    → lawVersion
      → law
```

同时 link review 的 `contextHashes` 检查 hazard + clause。

### Link eligible

仅当：

```text
link PASS
AND clause PASS
AND lawVersion PASS for current support
AND law PASS
```

### Hazard eligible

仅当：

```text
hazard PASS
AND exists(link where link eligible AND role in {direct, fallback})
```

### 多 link 策略

- 通过的 link 进入 release；
- pending/failed link 不进入 release；
- 失败 link 进入 gate report；
- 不因附加 supporting link 失败而阻断已有可靠 direct/fallback link 的 hazard。

这与 V3 “所有 active link 错误聚合后可能整条 hazard 阻断”的逻辑不同，避免低价值附加关联拖累已经可靠的核心依据。

---

## 12. Succession 与法规更新

法规更新不直接批量改 hazard 文本。

当新版本生效：

1. 新增/确认新 lawVersion；
2. 建立 succession；
3. 旧 version validityStatus 改为 repealed 或 endDate 更新；
4. 旧 version review 因内容变化 stale，重新确认版本状态；
5. 使用旧 version 的 link 在 current-support gate 自动失败；
6. 针对受影响 link 逐条评估是否可迁移到新 clause；
7. 不允许仅替换标准号并沿用旧 quote。

---

## 13. Soft Warning

以下默认 WARN：

- evidence snapshot 缺失；
- evidence snapshot hash mismatch；
- archiveOk=false；
- official URL 当前访问失败；
- reviewDue 到期；
- reviewedCommit 未填写；
- 全文库缺整份原文；
- aliases/keywords 较少；
- supporting link pending；
- 存在历史 inactive link；
- evidence 仅有私有引用、无法公开展示原件。

WARN 必须写入：

```text
releases-v4/<releaseId>/warnings.json
releases-v4/<releaseId>/gate-report.json
```

不能静默吞掉。

---

## 14. 隐私与公开投影硬门禁

### 14.1 原则

正式 release 采用字段 allowlist，而不是把 knowledge 文件整份复制出去。

### 14.2 禁止进入 release

- Windows/Linux/macOS 本地绝对路径；
- Google Drive 私有文件 URL/ID（除非明确标记为公开发布资料）；
- 私有 `privateRef`；
- 企业名称、项目名称、客户名称等不应公开的来源信息；
- 员工/联系人个人信息；
- 内部备注；
- 付费标准整份正文；
- 受版权/许可限制的附件原文；
- 私有报告正文；
- API key、token、账号信息。

### 14.3 Private evidence 的公开投影

可以公开：

- 标准名称/编号；
- 条款号；
- 经允许公开的短引用/必要条款文本（需遵循许可）；
- “经合法持有原件核验”等说明。

不得公开：

- privateRef；
- 文件路径；
- 原件下载位置；
- 整份受限内容。

---

## 15. Release 构建失败条件

只要出现任一情况，整个 candidate build 失败：

- schema 无法解析；
- duplicate ID；
- broken foreign key；
- canonicalization 不确定；
- review 引用不存在实体；
- release 内包含 BLOCK entity/link；
- release graph 引用缺失；
- 当前 hazard 没有 qualifying link；
- private leak；
- releaseHash 自校验失败；
- 同一输入重复构建产生不同 canonical release。

单个知识库里的 pending entity **不导致整个 build 失败**；它只是不进入 release。

这意味着 V4 允许“库里有大量待核验内容，同时网站只发布可靠子集”。

---

## 16. Deterministic Release

release 构建必须确定性：

- entity 按 Stable ID 排序；
- link 按 priority + ID 排序；
- object key canonical 排序；
- build timestamp 不进入 releaseHash，或使用明确 `asOf`；
- `releaseHash` 计算时先移除/置空 releaseHash 字段；
- 相同 sourceCommit + asOf + knowledge 内容必须得到相同 releaseHash。

建议：

```text
sourceCommit = 当前 Git commit SHA
sourceTreeHash = canonical knowledge tree hash（可选）
releaseHash = sha256(canonical release without releaseHash)
```

---

## 17. Gate Report

每次候选构建输出：

```json
{
  "releaseId": "candidate-...",
  "asOf": "2026-09-10",
  "sourceCommit": "...",
  "counts": {
    "knowledgeHazards": 1125,
    "eligibleHazards": 0,
    "blockedHazards": 0,
    "warnings": 0
  },
  "blocked": [],
  "warnings": [],
  "privacy": {
    "passed": true,
    "findings": []
  }
}
```

实际数量不得硬编码，示例只是结构。

每个 BLOCK/WARN 至少记录：

- code；
- entityType；
- entityId；
- message；
- relatedIds；
- remediation。

---

## 18. 建议错误码

### Schema / Graph

- `BLOCK_JSON_INVALID`
- `BLOCK_DUPLICATE_KEY`
- `BLOCK_SCHEMA`
- `BLOCK_DUPLICATE_ID`
- `BLOCK_FOREIGN_KEY`

### Review

- `BLOCK_REVIEW_MISSING`
- `BLOCK_REVIEW_NOT_VERIFIED`
- `BLOCK_REVIEW_UNBOUND`
- `BLOCK_REVIEW_STALE`
- `BLOCK_REVIEW_CONTEXT_STALE`
- `BLOCK_EVIDENCE_NOT_AUTHORITATIVE`

### Legal

- `BLOCK_LAW_IDENTITY`
- `BLOCK_VERSION_UNKNOWN`
- `BLOCK_VERSION_NOT_EFFECTIVE`
- `BLOCK_VERSION_EXPIRED`
- `BLOCK_CLAUSE_LOCATOR`
- `BLOCK_CLAUSE_TEXT`
- `BLOCK_CLAUSE_DUPLICATE`

### Applicability

- `BLOCK_LINK_APPLICABILITY`
- `BLOCK_LINK_ROLE`
- `BLOCK_NO_QUALIFYING_BASIS`

### Privacy

- `BLOCK_PRIVATE_LEAK`
- `BLOCK_RESTRICTED_CONTENT`

### Warning

- `WARN_EVIDENCE_URL_UNAVAILABLE`
- `WARN_EVIDENCE_ARCHIVE_MISSING`
- `WARN_EVIDENCE_HASH_MISMATCH`
- `WARN_REVIEW_DUE`
- `WARN_FULLTEXT_MISSING`
- `WARN_PENDING_AUXILIARY_LINK`

---

## 19. Override 边界

### 19.1 不允许普通 override 的硬门禁

以下不能通过命令行 `--force` 或 AI 自行决定绕过：

- 未核验/陈旧 review；
- clause 原文或定位不确定；
- version 效力不确定；
- link applicability 未核验；
- broken foreign key；
- duplicate/conflicting clause；
- private leak；
- 受限全文泄漏；
- upcoming/repealed 被用于当前定性。

### 19.2 可确认的软警告

用户可以接受 soft warnings 后发布候选，例如：

- 官方 URL 暂时打不开；
- snapshot 文件丢失；
- reviewDue 已到；
- 完整全文库缺失。

但接受 WARN 不会把 pending 内容升级为 verified。

### 19.3 人工特殊发布

V4 初始版本不设计自动 hard override 文件。

如果未来确需特殊场景，必须单独设计、用户明确批准，并保证：

- 不覆盖 canonical knowledge；
- 有明确过期时间；
- release 显式标记 overridden；
- 非内容真实性/隐私类问题才可能考虑。

---

## 20. 与 V3 Gate 的差异

| 项目 | V3 | V4 |
|---|---|---|
| 日常事实源 | SQLite | Git knowledge JSON |
| entity revision | 硬绑定 | Git 历史替代 |
| dependencyHash | 通用跨图硬绑定 | 取消 |
| entity 内容当前性 | revision + dependencyHash | reviewedContentHash |
| link 语义上下文 | dependencyHash | hazard/clause contextHashes |
| evidence archive hash | 硬门禁 | WARN |
| 完整全文 | 流程耦合较强 | 非统一硬门禁 |
| 多 link | active link 错误可能整体拖累 | 只发布通过 link；至少 1 qualifying basis |
| pending 数据 | 留母库但严格链可能高成本 | 留 knowledge，不进 release |
| 隐私 | release projection | allowlist + privacy hard gate |

V4 不是“放松核验”，而是把门禁重新对准真正的内容风险。

---

## 21. Phase 3 验收结论

本文件已经冻结：

- canonical JSON；
- reviewedContentHash；
- Link contextHashes；
- review 通用字段；
- evidence 等级；
- law / lawVersion / clause / hazard / link 的硬门禁；
- current/upcoming/repealed/unknown 行为；
- 多 link 发布策略；
- succession 更新行为；
- soft warnings；
- 隐私 allowlist；
- release fail 条件；
- deterministic release；
- error code；
- override 边界。

Phase 3 设计完成。

---

## 22. 下一步

进入 **Phase 4：V3 → V4 字段映射设计**。

下一份正式文档：

`docs/MIGRATION_V3_TO_V4.md`

Phase 4 必须逐表/逐字段说明：

- V3 SQLite 字段 → V4 entity JSON；
- V3 verification → V4 review；
- V3 evidence → V4 evidence；
- 哪些字段保留、重命名、派生、废弃；
- Stable ID 规则；
- link contextHashes 初次如何生成；
- V3 pending/invalid/merged 如何迁移；
- r8 错误记录如何隔离；
- r10 如何用于迁移后 release 对比而不是作为迁移事实源。

Phase 4 仍只做设计，不反写 V3 SQLite。