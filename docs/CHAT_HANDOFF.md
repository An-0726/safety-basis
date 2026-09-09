# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（Chat 自动续建第 2 轮）  
> 首要规则：每轮先读本文件，再核对 GitHub 与 Google Drive 的真实状态；若冲突，以真实最新资产为准并修正本文件。

## PROJECT_STATUS

ACTIVE

## 当前 Phase

- Phase 1：建立续接系统并冻结 V3 基线 —— **完成**
- Phase 2：V4 Chat-first 架构设计 —— **完成**
- 下一轮：Phase 3 —— **设计 `docs/GATE_V4.md`**

当前不进行大规模正式数据迁移，不切生产。

---

## 当前工作分支

### Chat V4 工作面

`chat-v4`

当前 HEAD（第 2 轮完成时）：

`8e5598f268659030c9f256e071eb288ec4f9b9f9`

本轮主要提交：

- `86d41f8959052ca06cf87b8760d2b1208973c321`：建立 V4 Chat-first 架构文档
- `8e5598f268659030c9f256e071eb288ec4f9b9f9`：修正 review 绑定漏洞，采用实体级 `reviewedContentHash`，取消跨实体 dependencyHash 级联

注意：`chat-v4` 最初从 GitHub 远端旧的 `data-verify-batch-003 @ 2b895ea...` 创建，因此它目前仍主要是 V4 文档/规划工作面，不可假定其中旧 V3 源码就是 Drive 最新源码。

### Drive 中真实 V3 工作分支

`data-verify-batch-003`

Drive 本地 ref：

`ecd76fa521c7a3af8bf1341481bb6588dac1ef37`

GitHub 远端同名分支仍为：

`2b895ea961f771cb469a86ca0155c586edf4df52`

已确认 GitHub 当前无法解析 `ecd76fa...`。

**禁止用 GitHub 旧状态覆盖 Drive 本地 V3。**

Drive 在 `2b895ea...` 之后已知提交包括：

- `eace7b9a...`：修复门禁并生成 r6
- `0f38e24d...`：r7 修复重复 clause、全文库核验与依赖刷新
- `e61343ab...`：r8 批量关联/核验；后续确认有质量事故
- `9c2c078e...`：r10、修复 evidence/clauses、生成待获取标准清单
- `87996340...`：完整交接文档
- `ecd76fa5...`：分级门禁修改方案

---

## V3 冻结基线

### GitHub main

`11a98ca3fa379a9e8a92549ba94dcc074297be1f`

main 公开 `data/manifest.json`：

- dataVersion：`2026.09.08.4`
- hazards：81
- laws：28
- clauses：80
- links：93
- verifiedHazards：32
- pendingHazards：49

禁止直接修改 `main`。

### V3 SQLite 母库

`source/master/safety.sqlite3`

- size：110,002,176 bytes
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- `PRAGMA integrity_check`：`ok`
- schemaVersion：3
- datasetHash：`a0916d788944c186a1420e8b0882971df54c4ebb056132100a8f4e841fa6b195`

关键数量：

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

### V3 全文库

`source/library/fulltext.sqlite3`

- size：21,864,448 bytes
- SHA-256：`8cedaf8f73134d78b3d489d862fb1540b2288b9326875c18f0aa23be2024b30e`
- `PRAGMA integrity_check`：`ok`
- documents：65
- FTS records：16,863

### 最新候选 release

`source/releases/reviewed-20260909-r10/`

- formatVersion：`safety-release-v2`
- asOf：`2026-09-09`
- releaseHash：`dc556a01cc24f95a3e6bfb21ebb1f89e13297c6ba469fa7c5d6b343348c0f3d2`
- sourceStateHash：`2d38b8b8b576446a34f48d3c98f7598ac44c2917c7208872031f9a2fb8b8e889`
- hazards：242
- laws：148
- law_versions：150
- clauses：52
- links：269
- evidence：574
- proofs：861

r8 是历史质量事故版本，不得恢复为可靠真值；r9 是回滚基线；r10 是当前最新候选。

### 当前生产/CI 选择

`source/releases/site-selection.json` 仍指向：

`reviewed-20260909-r4`

releaseHash：`67617524f24ae494a76993b434f414faf0675cc7d4466b3715bbabf982ffb5f2`

**r10 尚未切生产。不得自行修改 selection 或 GitHub Pages。**

---

## Phase 2 已完成设计

正式文档：

`docs/ARCHITECTURE_V4_CHAT_FIRST.md`

### V4 架构核心结论

1. **V4 日常正式维护源改为 Git-first `knowledge/`。**
2. **SQLite 不删除。** 它保留为 V3 冻结事实源、迁移来源、对账/查询资产，但 V4 日常新增修改不再要求先写 SQLite。
3. Stable ID 全部保留。
4. `law` / `lawVersion` / `clause` / `hazard` / `link` / succession 的关系模型保留。
5. V4 正式维护格式优先采用 **一实体一 UTF-8 pretty JSON**。
6. review 与内容分离，放 sidecar。
7. **review 必须用实体级 `reviewedContentHash` 与当前 canonical entity 内容硬绑定。**
8. **取消 V3 的跨实体 dependencyHash 级联。**
9. 上游实体变化通过链式 gate 自然阻断下游发布，而不是让所有下游 proof 机械失效。
10. evidence snapshot/hash、archiveOk、reviewDue、完整全文等默认进入软警告/审计增强层。
11. 条款原文、条款 locator、法规版本有效性、link applicability、当前 review 是否匹配当前内容、隐私泄漏仍是硬门禁。
12. 完整法规/标准全文不是每个可靠条款发布的统一前置条件。
13. `releaseHash` 保留。
14. 网站第一阶段不重写，通过 adapter 继续产出当前 schemaVersion=2 manifest/index/shards。
15. Phase 4 前不做正式字段迁移；Phase 5 前不写真实迁移代码。
16. 生产切换必须用户批准。

### reviewedContentHash 设计原因

第 2 轮二次校验时发现：如果 review 只写 `verified` 而不绑定当前实体内容，则实体修改后可能错误沿用旧 review。

因此正式修正为：

- review 记录 `reviewedContentHash`；
- validator/gate 对当前 entity canonical JSON 重新计算 hash；
- 不一致即 review stale，不能按 verified 发布；
- 只 hash 本实体，不计算跨图 dependencyHash；
- clause 被修改时只需复核 clause；链式 gate 会阻断引用它的 hazard，无需把所有 hazard/link review 全部重做。

这是 Phase 2 的重要安全结论，Phase 3 必须继续落实。

---

## Phase 2 输入依据

本轮已读取并交叉对照：

- `docs/CHAT_HANDOFF.md`
- Drive `docs/DATA_ARCHITECTURE_V3.md`
- Drive `docs/GATE_MODIFICATION_PROPOSAL_20260909.md`
- Drive `safety-basis_完整架构与设计书_20260909.md`
- Drive 最新 `tools/pipeline/verification.py`
- Drive 最新 `tools/pipeline/publish.py`

V3 当前代码确认：

- `own_errors()` 同时检查 status、identity、validity、proof revision、dependency hash、reviewer/locator、public fields、evidence、archive hash 和时间；
- `gate()` 对 hazard → link → clause → law_version → law 做链式拦截；
- `publish.prepare()` 只选无 gate error 的 hazard/version，并把 proofs/evidence 一并写进 release。

V4 没有删除链式质量检查，只把“技术一致性”与“内容正确性”重新分层。

---

## 当前未完成事项

- Phase 3：`docs/GATE_V4.md`
- Phase 4：V3 → V4 字段映射设计
- Phase 5：只读迁移原型
- V4 `knowledge/` 实体原型尚未创建
- V4 validator/gate/release/site 工具尚未实现
- V3/V4 release 对比尚未执行
- Drive 本地未推送历史尚未与 GitHub 安全同步
- 461 个 pending hazard 的专项依据尚未补齐
- 2508 个 pending clause 尚未全量核验
- 125 项待获取专项标准队列尚未按 V4 新流程处理
- 生产仍为 r4；未切换

---

## 下一轮第一步

**Phase 3：创建并完成 `docs/GATE_V4.md`。**

必须先再次核对：

1. `docs/CHAT_HANDOFF.md`；
2. `chat-v4` HEAD；
3. Drive `data-verify-batch-003` HEAD 是否仍为 `ecd76fa...`；
4. 是否出现更新的 V3 数据库/release/gate 方案。

Phase 3 必须明确：

- canonical JSON 与 `reviewedContentHash` 的规范；
- hazard/law/lawVersion/clause/link 各自硬门禁；
- 链式 gate；
- soft warning；
- upcoming/repealed/unknown；
- 私有标准证据；
- official URL 暂时失效的处理；
- link applicability；
- 隐私扫描；
- release 失败条件；
- 用户 override 边界；
- 不能因为技术哈希/全文缺失而误杀已可靠核验条款，同时也不能放松内容真实性。

Phase 3 仍不做大规模正式数据迁移。

---

## 风险 / 阻塞

### 1. Drive / GitHub 历史分叉

当前首要工程风险。Phase 2/3/4 可继续文档设计；Phase 5 真正迁移代码前必须安全对账，不能从 `chat-v4` 旧源码直接改生产。

### 2. r8 历史质量事故

禁止恢复 r8 批量核验结论。无法确定的内容保持 pending。

### 3. 生产仍为旧选择

r10 是候选，不是生产。

---

## 明确禁止事项

- 不直接修改 `main`
- 不切生产网站/GitHub Pages
- 不改 `site-selection.json` 指向 r10 或 V4 candidate，除非用户批准
- 不用 GitHub 旧状态覆盖 Drive 最新成果
- 不用旧 release 覆盖 r10
- 不用旧 SQLite 覆盖当前 V3 母库
- 不恢复 r8 为真值
- 不在 V4 Gate 定稿前全量处理 2508 个 clause
- 不在 V4 架构未迁移前清理 1502 个历史失效 link 作为优先事项
- 不批量假定 hazard—clause 关联正确
- 不编造法规、标准、条款、日期、效力、适用范围
- 不把 upcoming 当 active
- 不把旧版条文冒充新版
- 不因缺少完整标准全文而否定已可靠核验的具体条款
- 不公开企业资料、内部路径、私有报告、受限标准全文或其他非公开资料
