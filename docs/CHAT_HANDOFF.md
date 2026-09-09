# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（Chat 自动续建第 3 阶段）  
> 每轮必须先读本文件，再核对 GitHub 与 Google Drive 真实状态；发生冲突时，以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前 Phase

- Phase 1：V3 基线冻结 —— **完成**
- Phase 2：V4 Chat-first 架构设计 —— **完成**
- Phase 3：V4 发布门禁设计 —— **完成**
- 下一阶段：Phase 4 —— **V3 → V4 字段映射设计**

当前仍不做大规模正式数据迁移，不切生产。

---

## 当前工作分支

`chat-v4`

本轮 Phase 3 主要提交：

- `6bfc734c49cd89a415b22b03f11c165f7cca66aa`：新增 `docs/GATE_V4.md`

Phase 2 主要提交：

- `86d41f8959052ca06cf87b8760d2b1208973c321`：建立 `docs/ARCHITECTURE_V4_CHAT_FIRST.md`
- `8e5598f268659030c9f256e071eb288ec4f9b9f9`：采用实体级 `reviewedContentHash`，取消 V3 通用 dependencyHash 级联

注意：`chat-v4` 最初从 GitHub 远端 `data-verify-batch-003 @ 2b895ea...` 建立，它是当前 V4 文档/规划工作面，不代表 Drive 最新 V3 源码已同步到 GitHub。

---

## 版本安全基线

### Drive 最新 V3

工作分支：`data-verify-batch-003`

本地 ref：

`ecd76fa521c7a3af8bf1341481bb6588dac1ef37`

### GitHub 远端 V3

`data-verify-batch-003`：

`2b895ea961f771cb469a86ca0155c586edf4df52`

GitHub 当前无法解析 `ecd76fa...`，说明 Drive 含尚未推送的后续历史。

**禁止用 GitHub 旧状态覆盖 Drive。**

### GitHub main

`11a98ca3fa379a9e8a92549ba94dcc074297be1f`

禁止直接修改 `main`。

---

## V3 冻结资产

### `source/master/safety.sqlite3`

- 110,002,176 bytes
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- integrity_check：`ok`
- schemaVersion：3
- laws：160
- law_versions：161
- clauses：2603
- hazards：1125
- links：2298
- sources：24
- source_rows：6155
- verification：16159
- evidence：1124
- law_successions：4
- candidate_admissions：1428

状态：

- hazards：已核验 662；待核验 461；待整理 2
- clauses：已核验 95；待核验 2508
- links：已核验 790；已失效 1502；待核验 6
- law_versions：现行有效 156；即将生效 2；待核验 3

### `source/library/fulltext.sqlite3`

- 21,864,448 bytes
- SHA-256：`8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`
- integrity_check：`ok`
- documents：65
- FTS records：16,863

### 最新候选 release

`reviewed-20260909-r10`

- releaseHash：`dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`
- hazards：242
- laws：148
- law_versions：150
- clauses：52
- links：269

r8 是历史质量事故版本，不得恢复；r10 只是候选。

### 当前生产选择

`source/releases/site-selection.json` 仍指向 `reviewed-20260909-r4`。

**不得自行切 r10 或 V4。**

---

## Phase 2 已冻结的 V4 架构

正式文件：`docs/ARCHITECTURE_V4_CHAT_FIRST.md`

核心：

1. V4 日常正式维护源：Git-first `knowledge/`。
2. 一实体一 UTF-8 pretty JSON。
3. SQLite 保留为 V3 冻结/迁移/查询资产，不再是 V4 日常写入口。
4. Stable ID 保留。
5. law / lawVersion / clause / hazard / link / succession 保留。
6. review 与 entity 分离。
7. review 用 `reviewedContentHash` 绑定当前实体内容。
8. 取消 V3 通用跨图 dependencyHash。
9. evidence archive hash、完整全文等不再统一作为发布硬门禁。
10. 网站先通过 adapter 兼容现有 schemaVersion=2 前端。
11. releaseHash 保留。
12. 不切生产。

---

## Phase 3 已冻结的 Gate V4

正式文件：`docs/GATE_V4.md`

### 六阶段门禁

1. JSON 解析 / canonicalization
2. Schema / ID / 外键 / 唯一性
3. Review 当前性绑定
4. 实体级内容 gate
5. Hazard → Link → Clause → LawVersion → Law 链式 gate
6. 隐私投影 + release 一致性/确定性

### canonical review 绑定

`reviewedContentHash = sha256(canonical_json(entity))`

规则：

- review missing / not verified / hash mismatch 均 BLOCK；
- JSON 格式空格、对象 key 顺序不影响 hash；
- 法规原文字符串不做 trim/润色；
- aliases/places/keywords 作为集合型字段排序后参与 canonical hash。

### Phase 3 对 Phase 2 的重要精化

**Link applicability review 必须额外保存局部 `contextHashes`：**

```json
{
  "hazard": "<current hazard hash>",
  "clause": "<current clause hash>"
}
```

原因：link 核验本质是在判断 hazard 与 clause 的语义适用性。

因此：

- link 自己变化 → link review stale；
- hazard 变化 → 相关 link review stale；
- clause 变化 → 相关 link review stale；
- lawVersion/law 变化不制造通用 dependencyHash，但由它们自己的链式 gate 阻断。

这是局部、明确的语义依赖，不是恢复 V3 全图 dependencyHash。

### Evidence 等级

- Tier A：authoritative-public，可支撑硬门禁
- Tier B：authoritative-private，可支撑硬门禁，但原件/路径不公开
- Tier C：secondary，只能辅助，不能单独支撑 law/version/clause verified

### 硬门禁核心

不能放软：

- clause 原文真实性
- clause locator
- law identity
- lawVersion 效力与 asOf 日期
- review 与当前内容绑定
- link applicability
- 外键/ID/重复冲突
- upcoming/repealed 被用于当前隐患
- 私有/受限内容泄漏

### 软警告核心

默认 WARN：

- evidence snapshot 丢失
- snapshot hash mismatch
- archiveOk=false
- official URL 临时失效
- reviewDue 到期
- reviewedCommit 缺失
- 完整全文缺失

### 多依据策略

V4 与 V3 的重要差异：

- 通过的 link 才进入 release；
- pending/failed 附加 link 被排除并记录；
- 不因为一个辅助 link 没完成就拖死已有可靠依据的 hazard；
- hazard 至少需要一条 qualifying basis：`direct` 或 `fallback`；
- `supporting` 不能单独支撑 hazard 发布。

### fallback

上位法/通用义务兜底允许使用，但 review.reason 必须解释兜底原因和适用边界，不能把宽泛上位法伪装成直接技术条款。

### Override

V4 初始版本不提供普通 `--force` 绕过硬门禁。

用户可接受 WARN，但不能因此把 pending 升级为 verified。

---

## 本轮已完成

1. 完成 V4 Gate 六阶段框架。
2. 完成 canonical JSON 规范。
3. 完成 reviewedContentHash 规范。
4. 发现并修复 Phase 2 的关系审阅缺口：新增 Link contextHashes。
5. 完成 review 字段与 decision 规范。
6. 完成 Evidence Tier A/B/C。
7. 完成 law / lawVersion / clause / hazard / link 各自硬门禁。
8. 完成 active/upcoming/repealed/unknown 行为。
9. 完成多 link 发布策略。
10. 完成 succession 更新规则。
11. 完成 soft warning。
12. 完成隐私 allowlist 原则。
13. 完成 deterministic release 规则。
14. 完成 gate report / error code。
15. 完成 override 边界。

---

## 下一阶段：Phase 4

创建：

`docs/MIGRATION_V3_TO_V4.md`

必须逐表/逐字段设计：

- V3 `hazards` → V4 hazard JSON
- `hazard_tags` → aliases/places/keywords
- `laws` / `law_aliases` → law JSON
- `law_versions` → lawVersion JSON
- `clauses` → clause JSON
- `links` → link JSON
- `law_successions` → succession JSON
- V3 verification → V4 review
- V3 evidence → V4 evidence
- provenance/source/source_rows 如何保留且不泄密
- Stable ID 如何原样迁移
- reviewedContentHash 初次如何计算
- Link contextHashes 初次如何生成
- merged / pending / invalid / 已失效如何处理
- r8 错误如何隔离
- r10 如何作为 release 对比基线，而不是迁移事实源

Phase 4 仍只做设计，不反写 V3 SQLite。

---

## 进入真实迁移前的阻塞

Phase 5 开始写真实迁移代码前，必须先解决：

**Drive `ecd76fa...` 与 GitHub 远端 `2b895ea...` 的历史分叉。**

不得从 `chat-v4` 当前旧 V3 源码假定为最新后直接重构生产代码。

---

## 明确禁止事项

- 不直接修改 `main`
- 不切生产/GitHub Pages
- 不自行修改 site-selection
- 不用 GitHub 旧状态覆盖 Drive
- 不恢复 r8
- 不把 pending 批量升级 verified
- 不编造法规/标准/条款/版本/效力
- 不把旧版条文当新版
- 不把 upcoming 当 active
- 不因完整全文缺失否定已可靠核验的具体条款
- 不公开企业资料、内部路径、私有报告、私有原件、受限全文、账号/token
