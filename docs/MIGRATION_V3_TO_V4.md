# Safety Basis V3 → V4 字段迁移设计

> 状态：Phase 4 正式设计稿  
> 日期：2026-09-10  
> 前置文档：`docs/ARCHITECTURE_V4_CHAT_FIRST.md`、`docs/GATE_V4.md`  
> 迁移原则：V3 SQLite 只读；Stable ID 优先原样保留；pending 不升级；历史错误不复活；私有来源不泄漏。

---

## 1. Phase 4 目标

本阶段只冻结 V3 → V4 的字段、状态、审阅和证据迁移规则，不反写 `source/master/safety.sqlite3`，不修改 V3 release，不切生产。

真实 V3 基线来自：

```text
source/master/safety.sqlite3
```

已冻结基线：

- laws：160
- law_versions：161
- clauses：2603
- hazards：1125
- links：2298
- evidence：1124
- verification：16159
- sources：24
- source_rows：6155
- law_successions：4

迁移工具未来只读该库，并输出 V4 candidate knowledge。

---

## 2. 总体迁移流水线

```text
V3 SQLite（只读）
  ↓
读取 schema + 数据 + 最新相关 verification
  ↓
实体字段转换
  ↓
Stable ID 保留
  ↓
状态标准化
  ↓
证据分类 / 隐私投影
  ↓
生成 V4 entity JSON
  ↓
对迁移后的 entity 做 canonicalization
  ↓
生成 reviewedContentHash
  ↓
生成 V4 review sidecar
  ↓
Link 额外生成 hazard/clause contextHashes
  ↓
V4 validate + gate
  ↓
迁移报告 / quarantine / pending 队列
```

**绝不允许：**

- 为了让 gate 通过而自动把 pending 改 verified；
- 直接复制 V3 `dependency_hash` 当 V4 review hash；
- 用 r10 release 反向覆盖 SQLite；
- 用角色名称或关键词自动证明 link applicability；
- 把 V3 私有来源路径直接写进公开 `knowledge/`。

---

## 3. Stable ID 规则

### 3.1 原有 ID 原样保留

迁移时以下 ID 原样保留：

- hazard：`H...`
- law：现有 V3 `laws.id`，包括实际存在的 `LF_...`
- lawVersion：现有 `law_versions.id`，包括历史 `L...`
- clause：`C...` 或现有实际 ID
- link：现有 `links.id`，**包括大量真实 `K_...` ID**
- evidence：现有 evidence ID

Phase 2/3 文档里的 `LV_xxx`、`LK_xxx` 只是新建实体的建议格式，不得用于给既有 V3 实体批量改 ID。

### 3.2 新增 ID

V4 正式启用后的新实体可使用：

- law：`LF_<stable>`
- lawVersion：`LV_<stable>`
- clause：`C_<stable>` 或沿用现有 clause 生成策略
- link：`LK_<stable>`
- evidence：`EV_<stable>`
- succession：`LS_<stable>`

具体新 ID 生成算法由实现阶段冻结；必须确定性、不可因文件排序改变。

### 3.3 不因合并删除旧 ID

merged/superseded 实体继续保留旧 ID 和去向，禁止复用旧 ID 给新内容。

---

## 4. V3 `hazards` → V4 hazard

V3 实际字段：

```text
id
title
description
measures
category
conditions
note
mode
status
checked
revision
merged_into
legacy_payload
```

### 4.1 字段映射

| V3 | V4 | 处理 |
|---|---|---|
| `id` | `id` | 原样保留 |
| `title` | `title` | 原样保留，不自动润色 |
| `description` | `description` | 原样保留；后续人工优化另做 Git diff |
| `measures` | `measures` | 原样保留 |
| `category` | `category` | 原样保留/按 V4 字典校验 |
| `conditions` | `conditions` | **按字符串保留**；V3 实际不是数组 |
| `note` | `note` | 保留；公开 projection 是否输出由 allowlist 决定 |
| `mode` | `mode` | 见 4.2 |
| `status` | review/lifecycle 输入 | 不直接写为 V4 verified |
| `checked` | migration metadata | 不作为 V4 真值 |
| `revision` | migration metadata | 不作为 V4 日常 revision |
| `merged_into` | `mergedInto` | 原样保留目标 ID |
| `legacy_payload` | archive only | 不进入正式 knowledge entity |

### 4.2 mode 映射

V3 实际主要值：

- `直接适用`
- `条件适用`
- `上位法兜底`
- 空值/少量其他

V4 推荐：

| V3 | V4 |
|---|---|
| `直接适用` | `direct` |
| `条件适用` | `conditional` |
| `上位法兜底` | `fallback` |
| 空/未知 | `unknown` |

`mode=unknown` 可以保留在 knowledge，但不能仅凭该字段进入正式 release；是否阻断由 Gate V4 的 hazard/link 条件决定。

### 4.3 hazard_tags

V3：

```text
hazard_id, kind, value, ordinal
```

实际 kind 包括：

- `keyword`
- `place`
- `aliase`（历史拼写）

映射：

| kind | V4 |
|---|---|
| `keyword` | `keywords[]` |
| `place` | `places[]` |
| `aliase` | `aliases[]` |

按 ordinal 读入后，在 canonical hash 时 `aliases/places/keywords` 作为集合型字段排序；重复值必须由 validator 报错，迁移器不得静默覆盖互相冲突的数据。

### 4.4 hazard lifecycle

- `merged_into != null` → `lifecycle=merged`
- V3 明确失效/废弃 → 对应 inactive/superseded
- 其余可先 `active`

**注意：`status=待核验` 不等于 lifecycle inactive。** 它表示内容审阅状态，不等于这个知识实体不存在。

---

## 5. V3 `laws` + `law_aliases` → V4 law

V3 `laws`：

```text
id
canonical_name
issuer
jurisdiction_code
document_kind
identity_key
identity_status
status
checked
revision
legacy_payload
```

### 5.1 字段映射

| V3 | V4 | 处理 |
|---|---|---|
| `id` | `id` | 原样 |
| `canonical_name` | `canonicalName` | 原样 |
| `issuer` | `issuer` | 原样 |
| `jurisdiction_code` | `jurisdictionCode` | 原样/字典校验 |
| `document_kind` | `documentKind` | 原样/标准化字典 |
| `identity_key` | `identityKey` | 保留为内部去重/校验字段，可不进入公开 release |
| `identity_status` | lifecycle/review hint | 不直接等于 verified |
| `status` | legacyStatus | 不作为法规效力字段 |
| `checked` | migration metadata | 不作为 current review |
| `revision` | migration metadata | 不进入 V4 日常实体版本 |
| `legacy_payload` | archive only | 不进入知识实体 |

V3 实际 `identity_status`：

- confirmed
- provisional
- merged

迁移：

- confirmed：允许尝试生成 identity review，但仍需读取最新 V3 verification；
- provisional：V4 review 默认 pending；
- merged：`lifecycle=merged`，保留 canonical target（若可解析）；不能作为独立当前 canonical law 发布。

### 5.2 law_aliases

`law_aliases(law_id, alias, ordinal)` → `aliases[]`。

---

## 6. V3 `law_versions` → V4 lawVersion

V3 实际字段：

```text
id
law_id
version_key
document_number
official_name
level
scope
effective_date
end_date
validity_status
review_status
source_url
checked
revision
legacy_payload
```

### 6.1 映射

| V3 | V4 |
|---|---|
| `id` | `id` |
| `law_id` | `lawId` |
| `version_key` | `versionKey` |
| `document_number` | `documentNumber` |
| `official_name` | `officialName` |
| `level` | `level` |
| `scope` | `scope` |
| `effective_date` | `effectiveDate` |
| `end_date` | `endDate` |
| `validity_status` | `validityStatus` 标准化 |
| `review_status` | migration hint，不直接决定 verified |
| `source_url` | `sourceUrl` |
| `checked` | migration metadata |
| `revision` | migration metadata |
| `legacy_payload` | archive only |

### 6.2 validityStatus 映射

| V3 | V4 |
|---|---|
| `现行有效` | `active` |
| `即将生效` | `upcoming` |
| `已废止` / 明确失效 | `repealed` |
| `待核验` / 空 / 无法确认 | `unknown` |

不得依据当前日期自动把 `unknown` 猜成 active。

### 6.3 review_status

V3 的 `review_status` 可能是：

- 已核验
- legacy_inherited
- pending/staging 等

它只是迁移线索。

**V4 lawVersion review 必须依据最新相关 verification + evidence + 当前迁移内容生成。** `review_status=已核验` 本身不够。

### 6.4 空日期

V3 中确有历史记录缺失日期。迁移时：

- 空值保留为 `null`；
- review 置 pending/unknown；
- 不用发布日期、年份或名称推测有效日期。

---

## 7. V3 `clauses` → V4 clause

V3：

```text
id
law_version_id
article_path
quote
source_url
status
checked
identity_status
revision
legacy_payload
```

映射：

| V3 | V4 |
|---|---|
| `id` | `id` |
| `law_version_id` | `lawVersionId` |
| `article_path` | `articlePath` |
| `quote` | `quote` |
| `source_url` | `sourceUrl` |
| `status` | review hint |
| `checked` | migration metadata |
| `identity_status` | locator hint |
| `revision` | migration metadata |
| `legacy_payload` | archive only |

重要事实：当前大量 clause `identity_status=confirmed_locator`，但只有少部分 `status=已核验`。

所以：

> **locator 已确认 ≠ 条款原文已核验。**

迁移器不得仅凭 `confirmed_locator` 生成 `decision=verified`。

`quote` 必须原样迁移，不做语言优化。

---

## 8. V3 `links` → V4 link

V3 实际字段：

```text
id
hazard_id
clause_id
role
priority
applicability
jurisdiction_code
status
revision
legacy_payload
```

### 8.1 字段映射

| V3 | V4 |
|---|---|
| `id` | `id`，原样保留，包括 `K_...` |
| `hazard_id` | `hazardId` |
| `clause_id` | `clauseId` |
| `role` | `role` + `legacyRole` |
| `priority` | `priority` |
| `applicability` | `applicability` |
| `jurisdiction_code` | `jurisdictionCode` |
| `status` | lifecycle/review hint |
| `revision` | migration metadata |
| `legacy_payload` | archive only |

### 8.2 真实 role 不能三值硬套

V3 实际出现大量角色，例如：

- `primary`
- `直接依据`
- `候选直接依据`
- `直接标准`
- `上位法兜底`
- `补充依据`
- `优先直接标准`
- `直接强制标准`
- `条件适用直接依据`
- `上位法依据`
- 其他少量自定义值

V4 knowledge role 允许迁移期增加：

- `direct`
- `supporting`
- `fallback`
- `unclassified`

映射建议：

| V3 role | V4 role |
|---|---|
| 明确“直接依据/直接标准/直接强制标准/优先直接标准/条件适用直接依据” | `direct` |
| `补充依据` | `supporting` |
| `上位法兜底` / `上位法依据` | `fallback` |
| `primary`、候选、其他语义不够明确 | `unclassified` |

所有迁移项保留：

```json
"legacyRole": "原始值"
```

### 8.3 `unclassified` 的发布行为

- 可以存在于 knowledge；
- 默认 review=pending；
- **不能成为 qualifying link**；
- 必须经过人工/AI 逐条适用性复核后，才能改为 direct/supporting/fallback。

### 8.4 为什么 `primary` 不能自动 direct

历史 r8 事故中大量 link 使用 `primary`。目前 V3 中既有大量已失效 `primary`，也有少量仍为已核验的 `primary`。

因此：

> role 文本不能证明关联正确。

迁移时 `primary` 一律先 `unclassified`，除非有明确的可信后续重验记录可以证明当前 link 的 applicability。

### 8.5 lifecycle

- `status=已失效` → `lifecycle=inactive`
- 其他存在的 link → `active`，但 active 不代表 verified

inactive link 保留历史，不进入当前 release。

---

## 9. V3 `law_successions` → V4 succession

V3：

```text
old_version_id
new_version_id
relation
scope
effective_date
verification_id
```

V4：

```json
{
  "id": "LS_xxx",
  "oldVersionId": "...",
  "newVersionId": "...",
  "relation": "replaces",
  "scope": "...",
  "effectiveDate": "..."
}
```

V3 实际 relation 目前包括：

- `replaced_by`
- `partial_replaced_by`

因为 V3 字段方向已经明确为 old → new，V4 标准化：

| V3 | V4 | 语义 |
|---|---|---|
| `replaced_by` | `replaces` | newVersion replaces oldVersion |
| `partial_replaced_by` | `partially_replaces` | newVersion partially replaces oldVersion |

迁移报告必须同时保留 `legacyRelation`，避免方向歧义。

`verification_id` 不直接进入 succession entity，可作为 migration audit/source review reference。

---

## 10. V3 `evidence` → V4 evidence

V3：

```text
id
official_url
retrieved_at
snapshot_ref
sha256
page
locator
```

### 10.1 映射

| V3 | V4 | 处理 |
|---|---|---|
| `id` | `id` | 原样保留 |
| `official_url` | `url` | 保留，但需重新分类 evidence tier |
| `retrieved_at` | `retrievedAt` | 保留 |
| `snapshot_ref` | private migration metadata | **不直接写入公开 knowledge** |
| `sha256` | `snapshotSha256` 可选 | 仅技术审计，不是内容硬门禁 |
| `page` | `page` | 保留 |
| `locator` | `locator` | 保留 |

### 10.2 Evidence Tier 不能按非空 URL 自动判定

迁移器必须分类：

- 官方政府/发布机构公开页面 → Tier A `authoritative-public`；
- 合法持有但不可公开原件 → Tier B `authoritative-private`；
- 第三方/辅助来源 → Tier C `secondary`。

`official_url` 字段历史上叫“official”，但迁移不能只凭字段名相信来源权威性。

### 10.3 snapshot_ref 隐私处理

V3 `snapshot_ref` 可能包含本地/私有归档位置。

公开 `knowledge/evidence` 中禁止直接暴露。

如需保留关联，生成不可逆/不含路径语义的 `privateRef`，映射表仅保存在私有迁移报告中。

---

## 11. V3 verification → V4 review

V3 verification：

```text
id
entity_type
entity_id
entity_revision
dependency_hash
check_type
result
reviewer
model
checked_at
review_due_at
evidence_id
reason
supersedes
```

V3 `verification_details`：

```text
verification_id
locator
public_fields_reviewed
action_id
```

### 11.1 相关 check_type

现有 V3 语义：

| entity_type | check_type |
|---|---|
| law | `identity` |
| law_version | `version` |
| clause | `text` |
| hazard | `content` |
| link | `applicability` |

只把这些“当前内容核验”类型迁成 V4 current review。

其他历史审计记录进入 migration audit，不直接成为发布 review。

### 11.2 最新记录选择算法

为了与 V3 当前 `load_proofs()` 的实际语义一致：

1. 按 SQLite `rowid` 升序读取 verification；
2. 只看 entity_type 对应的正式 check_type；
3. 同一 `(entity_type, entity_id)` 后出现的相关 verification 覆盖前者作为“当前 V3 结论候选”；
4. **最新结果不是 passed，则 V4 review 不得 verified**；
5. 即使最新结果 passed，也必须继续通过本迁移文档的额外安全条件。

不依赖 `supersedes` 字段完整性来寻找当前记录，因为 V3 当前代码实际采用“最后相关 row 覆盖”的行为。

### 11.3 result 映射

| V3 result | V4 decision |
|---|---|
| passed + 所有迁移安全条件满足 | `verified` |
| failed | `rejected` 或 `pending`（按原因） |
| pending/缺失 | `pending` |
| 实体已失效/被替代 | `superseded` 或不生成 current review |

### 11.4 V3 revision/dependency_hash

- `entity_revision`：写入私有 migration audit，仅作追溯；
- `dependency_hash`：写入私有 migration audit，仅作追溯；
- **都不复制为 V4 `reviewedContentHash`。**

V4 `reviewedContentHash` 必须在完成 V4 entity 字段转换后重新计算：

```text
sha256(canonical_json(migrated_v4_entity))
```

### 11.5 review 字段

| V3 | V4 |
|---|---|
| `entity_type` | `entityType` |
| `entity_id` | `entityId` |
| `check_type` | `reviewType` |
| `result` | `decision` |
| `reviewer` | `reviewer` |
| `model` | `model` 可选 |
| `checked_at` | `checkedAt` |
| `review_due_at` | `reviewDue`，soft warning |
| `evidence_id` | `evidenceRefs[]` |
| `reason` | `reason` |
| details.locator | `locator` |
| details.public_fields_reviewed | `publicFieldsReviewed` 迁移元数据 |

### 11.6 hazard public fields

如果 hazard 的历史 review 没有确认公开字段，V4 不能仅凭历史 `status=已核验` 自动生成可公开 verified review。

迁移器应：

- 若最新可信 review 已明确覆盖当前公开字段 → 可生成 verified；
- 否则 review=pending，并进入“公开字段复核”队列。

---

## 12. Link review 的首次生成

这是迁移中风险最高的部分。

### 12.1 基础要求

要生成 V4 `link/applicability` verified review，至少：

1. link 当前不是 `已失效`；
2. 最新相关 V3 applicability verification = passed；
3. hazard 和 clause 均存在；
4. 该 link 不属于已知 r8 错误恢复范围；
5. reason/applicability 能支持真实语义关系；
6. 如果无法确认上述任一项 → pending。

### 12.2 r8 隔离

r8 已知存在批量错误关联/共享证据质量事故，后续大量 link 被回滚为 `已失效`。

迁移规则：

- `links.status=已失效` 永远不恢复为 active verified；
- 历史 r8 的 passed verification 不得覆盖后续失效状态；
- `role=primary` 不作为可信标记；
- 当前仍“已核验”的 link 若来源于同一事故链，必须有可信的后续 reverify / gate 修复 / r10 纳入等证据才能迁为 verified；
- 无法精确证明后续重验的，宁可 pending。

**不以单一时间戳硬编码识别 r8。** 应综合 link 当前状态、已知 rollback/reverify 成果和迁移审计来源。

### 12.3 contextHashes

生成 link review 前：

```text
contextHashes.hazard = sha256(canonical_json(current migrated hazard))
contextHashes.clause = sha256(canonical_json(current migrated clause))
reviewedContentHash = sha256(canonical_json(current migrated link))
```

三个 hash 均来自迁移后的 V4 实体，不来自 V3 dependency_hash。

---

## 13. V3 sources / source_rows / provenance

### 13.1 V3 字段

`sources` 包含：

```text
id, sha256, original_name, media_type, byte_size, visibility,
storage_ref, source_commit, created_at
```

`source_rows` 包含：

```text
id, source_id, sheet, row_number, json_pointer, raw_payload
```

`provenance` 包含：

```text
id, entity_type, entity_id, source_row_id, field_path, transform_run_id
```

### 13.2 公私分层

V4 不把整个 V3 来源层复制到公开 Git。

#### 私有迁移档案保留

完整保留：

- original_name
- storage_ref
- raw_payload
- sheet/row
- 企业/项目来源
- 文件 SHA
- 原始报告定位

它们继续位于 V3 私有 archive / 私有 migration report。

#### 公开 provenance 最小投影

公开 knowledge 仅允许保存不泄密的来源引用，例如：

```json
{
  "entityType": "hazard",
  "entityId": "H015",
  "sourceRefs": ["SRC_PUBLIC_001"]
}
```

`SRC_PUBLIC_001` 不能反推出本地路径、企业名称或私有文件 ID。

### 13.3 raw_payload

绝不直接复制到公开 knowledge/release。

---

## 14. V3 审计表的处理

以下 V3 表/记录主要属于历史事务和工具审计：

- change_sets / change events
- catalog_actions / catalog events
- master_actions
- review_actions
- source_sync_actions
- migration_runs / conflicts
- exchange/proposal 历史
- legacy payload/action 表

迁移规则：

- 不转换为每个 V4 entity 的必需字段；
- 保留在 V3 冻结 SQLite/私有归档；
- Phase 5 输出一份 migration audit summary，记录使用了哪些 V3 资产；
- V4 后续普通变更由 Git commit/PR 作为主要审计历史。

---

## 15. 状态迁移矩阵

### 15.1 hazard

| V3 | V4 entity | V4 review |
|---|---|---|
| 已核验 + 最新可信 content pass | active | verified candidate |
| 已核验但 review 绑定/公开字段不足 | active | pending |
| 待核验 | active | pending |
| 待整理 | active/staging | pending |
| merged_into 非空 | merged | superseded/pending |

### 15.2 clause

| V3 | V4 |
|---|---|
| 已核验 + 最新 text pass + evidence 有效 | verified candidate |
| confirmed_locator 但 text 未核验 | pending |
| 待核验 | pending |
| 冲突定位/原文 | rejected/pending + quarantine |

### 15.3 link

| V3 | V4 |
|---|---|
| 已失效 | inactive，不生成 qualifying review |
| 已核验 + 可信后续 applicability pass | active + verified candidate |
| 已核验但 r8/来源无法排除风险 | active + pending |
| 待核验 | active + pending |
| role 不明确 | role=unclassified + pending |

### 15.4 lawVersion

| V3 | V4 |
|---|---|
| 现行有效 + version review可信 | active + verified candidate |
| 即将生效 + review可信 | upcoming + verified candidate，但不能当前支撑 hazard |
| 待核验/空 | unknown + pending |
| 已废止 | repealed + historical |

---

## 16. Quarantine 机制

迁移时不能“要么导入，要么丢弃”。以下进入：

```text
migration-output/quarantine/
```

建议分类：

- `r8-link-risk.jsonl`
- `role-unclassified.jsonl`
- `review-evidence-missing.jsonl`
- `law-version-date-unknown.jsonl`
- `clause-conflict.jsonl`
- `private-provenance-blocked.jsonl`
- `id-or-foreign-key-conflict.jsonl`

每条至少：

```json
{
  "entityType": "link",
  "entityId": "K_...",
  "reasonCode": "R8_REVIEW_NOT_TRUSTED",
  "sourceState": "已核验",
  "action": "migrate_as_pending"
}
```

Quarantine 不等于删除；它是“保留但禁止自动升级”的安全区。

---

## 17. Migration Manifest

Phase 5 每次原型迁移必须生成：

```json
{
  "formatVersion": "safety-v3-v4-migration-v1",
  "sourceDatabaseSha256": "7086...",
  "sourceSchemaVersion": 3,
  "sourceGitRef": "drive:data-verify-batch-003@ecd76fa...",
  "generatedAt": "...",
  "counts": {
    "source": {},
    "migrated": {},
    "verifiedCandidates": {},
    "pending": {},
    "quarantined": {}
  },
  "rulesVersion": "MIGRATION_V3_TO_V4.md@<commit>"
}
```

不得把 `generatedAt` 参与实体内容 hash。

---

## 18. V4 输出树

Phase 5 原型先输出到隔离目录，不直接写正式 `knowledge/`：

```text
migration-output/v4-candidate/
  knowledge/
    hazards/
    laws/
    law-versions/
    clauses/
    links/
    successions/
    reviews/
    evidence/
    provenance/public/
  quarantine/
  reports/
    migration-manifest.json
    field-loss-report.json
    id-report.json
    review-report.json
    privacy-report.json
```

验收后才决定是否提升到正式 `knowledge/`。

---

## 19. 字段丢失检查

迁移器必须输出 `field-loss-report.json`。

每个 V3 业务字段只能落入以下一种状态：

- `preserved`
- `renamed`
- `normalized`
- `derived`
- `archived_private`
- `deprecated_with_reason`

不允许 `silently_dropped`。

特别检查：

- hazard.note
- conditions
- legacy role
- law identity_key
- source provenance
- verification reason/locator
- law succession scope
- private evidence locator

---

## 20. r10 的角色

r10 是 **迁移后发布行为的对比基线**，不是迁移事实源。

正确顺序：

```text
V3 SQLite
  → V4 candidate knowledge
  → V4 Gate
  → V4 candidate release
  → compare V4 release with V3 r10
```

禁止：

```text
r10
  → 反推完整 V4 knowledge
```

因为 r10 只包含通过 V3 gate 的发布子集，不包含 1125 hazard / 2603 clause 的完整母库状态。

### 必须比较

- r10 的 242 hazard 是否在 V4 中有对应 Stable ID；
- r10 的 269 links 在 V4 是否保留/为什么变化；
- V4 少于 r10：逐项解释是 V4 更严格、迁移缺失还是错误；
- V4 多于 r10：逐项解释是 V4 技术软门禁释放、后续核验还是错误放行；
- clause quote 不得发生无理由变化；
- lawVersion 不得被错误替换。

---

## 21. Phase 5 原型验收条件

进入正式 `knowledge/` 前至少：

1. V3 SQLite 全程只读；
2. Stable ID 100% 对账，无静默重编号；
3. 核心业务字段无静默丢失；
4. 所有外键可解析或明确 quarantine；
5. r8 已失效 link 不复活；
6. V3 pending 不自动 verified；
7. V4 review hash 来自迁移后实体；
8. link contextHashes 正确；
9. private source/raw payload/path 未进入公开 candidate；
10. deterministic 重跑结果一致；
11. V4 validator/gate 通过结构检查；
12. 与 r10 的差异报告完整；
13. 未修改 site-selection；
14. 未修改 main。

---

## 22. Phase 4 对前两阶段的必要修正

真实数据库检查后，对 Phase 2/3 示例作以下正式精化：

### A. hazard.conditions

V3 实际是文本，不是数组。

V4 初始迁移保持字符串；未来若要结构化为数组，必须另做显式 schema migration，不能在 V3 → V4 首迁时擅自拆分。

### B. hazard.note

V3 有 `note` 字段，V4 必须保留。是否公开由 release allowlist 决定。

### C. link ID

现有 Stable ID 包括 `K_...`，必须保留。`LK_...` 仅供未来新增。

### D. link role

V4 迁移期必须允许 `unclassified`；Gate V4 中 qualifying role 仍只有 direct/fallback，unclassified 不能发布为依据。

### E. lawVersion 日期

历史空日期保持 null/unknown，不推测。

### F. clause locator 与 text review 分离

`confirmed_locator` 不能替代 `text=verified`。

这些精化在实现 Phase 5 时优先于早期示例字段形式。

---

## 23. Phase 4 验收结论

已完成：

- hazards/hazard_tags 字段映射；
- laws/law_aliases 字段映射；
- law_versions 字段与效力映射；
- clauses 字段映射；
- links 字段、Stable ID、角色归一化；
- succession 方向映射；
- evidence 公私分层；
- verification → review 当前记录选择；
- reviewedContentHash 首次生成规则；
- link contextHashes 生成规则；
- sources/source_rows/provenance 隐私迁移；
- audit 表归档策略；
- pending/verified/inactive/merged 状态矩阵；
- r8 quarantine；
- migration manifest；
- 字段丢失报告；
- r10 对比策略；
- Phase 5 验收条件。

**Phase 4 设计完成。**

---

## 24. 下一步与工程阻塞

下一阶段是 **Phase 5：只读迁移原型**。

但在把真实迁移代码写入 `chat-v4` 前，仍存在已冻结的版本安全阻塞：

```text
Drive 最新 V3: ecd76fa...
GitHub remote V3: 2b895ea...
```

Phase 5 必须先选择一种不覆盖 Drive 的安全方式取得最新 V3 工具/仓库状态，或明确把原型实现成“完全独立、只读当前冻结 SQLite、与 V3 源码无耦合”的迁移器。

在解决该边界前，不从 `chat-v4` 的旧 V3 源码直接重构生产流水线。
