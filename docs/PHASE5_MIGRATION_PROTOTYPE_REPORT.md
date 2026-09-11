# Phase 5：V3 → V4 只读迁移原型验收报告

> 日期：2026-09-10  
> 工作分支：`chat-v4`  
> 原型输入：Drive `source/master/safety.sqlite3`  
> 输入 Git 语义基线：`drive:data-verify-batch-003@ecd76fa521c7a3af8bf1341481bb6588dac1ef37`  
> 对比候选：`reviewed-20260909-r10`

## 1. 结论

Phase 5 的**独立只读迁移原型已跑通**。

原型没有调用或改写旧 V3 `tools/pipeline/`，直接以只读 URI 打开冻结 SQLite，输出隔离 `v4-candidate` 树，从而绕开 Drive 最新 V3 与 GitHub 远端源码未同步的问题。

本轮未切生产、未改 `main`、未改 `site-selection.json`、未反写 SQLite，也未把 1.3 万多个候选 JSON 直接提交仓库。

## 2. 输入真实性校验

实际下载的母库：

- size：110,002,176 bytes
- SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- `PRAGMA integrity_check`：`ok`

关键源数量：

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

迁移执行结束后再次计算 SQLite SHA-256，仍为同一值，证明本轮没有改写母库。

## 3. 完整迁出结果

候选知识树完整生成：

- laws：160 / 160
- lawVersions：161 / 161
- clauses：2603 / 2603
- hazards：1125 / 1125
- links：2298 / 2298
- evidence：1124 / 1124
- successions：4 / 4

同时为每个 law / lawVersion / clause / hazard / link 生成独立 review sidecar。

Stable ID 检查：

- ID issue：0
- broken FK：0
- 未发生批量重编号
- 既有 `K_...` link ID 原样保留

重复基础数据检查：

- hazard tag 重复组合：0
- law alias 重复组合：0

## 4. Review 迁移结果

采用保守自动迁移，不把 V3 `status=已核验` 直接等价为 V4 verified。

自动生成的 verified candidate：

- law：148
- lawVersion：150
- clause：54
- hazard：642
- link：179

其余：

- law：11 pending，1 superseded
- lawVersion：11 pending
- clause：2549 pending
- hazard：483 pending
- link：1502 superseded，617 pending

所有 V4 `reviewedContentHash` 都重新基于**迁移后的 V4 entity canonical JSON**计算，没有复制 V3 `dependency_hash`。

link review 另外生成：

- `contextHashes.hazard`
- `contextHashes.clause`

## 5. r8 风险控制与 link 差异

r10 graph 有 269 条 link；V4 原型当前自动认可 179 条。

缺少的 90 条 r10 link 全部可以解释：

- `primary`：84
- `候选直接依据`：5
- `主要负责人职责`：1

其中 84 条 `primary` 的最新 reviewer 为“并发重验批次”。这些角色名称不足以证明 direct/supporting/fallback 语义，因此原型没有自动升级。

这 90 条 link 当前保留在 knowledge，不丢失数据，只是 review=pending / role=unclassified。

相应地：

- r10 hazard：242
- V4 当前有完整 qualifying basis 的 hazard：158
- 差额：84

这 84 个 hazard 的 r10 支撑链恰好主要依赖上述 `primary` / 候选角色，因此属于**保守迁移差异，不是字段丢失**。

## 6. 法规版本与条款差异解释

### lawVersion

V4 current-support subset 为 148，r10 graph 为 150。

缺的两个版本：

- `L011`：GB/T 13869-2026，2027-02-01 生效
- `LV_STD_GB12801_2025`：GB 12801-2025，2026-10-01 生效

两者都是 upcoming。V4 已把它们迁为 verified upcoming，但按 2026-09-09 `asOf` 不允许支撑当前 hazard，因此 current-support 只有 148；这符合 Gate V4。

### clause

V4 verified clause 为 54，r10 graph 只有 52。

V4 多出的：

- `C006`
- `C043`

两条都已通过当前 clause review，但 r10 没有 link 引用它们，所以未进入 r10 graph。它们留在知识库是正确行为，不代表 V4 错误增加发布依据。

## 7. Quarantine

共 154 条：

- `ROLE_UNCLASSIFIED`：143
- `VERSION_EFFECTIVITY_UNCERTAIN`：11

Quarantine 只表示“禁止自动升级”，不删除实体。

## 8. 隐私验收

公开 candidate `knowledge/` 扫描以下模式：

- Windows / Linux / macOS 本地绝对路径
- `/mnt/` / `ESH_Codex`
- Google Drive 私有文件 URL
- `privateRef`
- `snapshot_ref`
- `storage_ref`
- `raw_payload`
- `legacy_payload`

最终命中：**0**。

原型明确不公开 V3：

- `sources.original_name`
- `sources.storage_ref`
- `source_rows.raw_payload`
- `evidence.snapshot_ref`
- 各实体 `legacy_payload`

## 9. 确定性验收

使用完全相同输入连续运行两次：

- candidate knowledge + quarantine 文件数：13,825
- 第一次 tree hash：`5545fcfbd43fdeac8d5cb9a7106b17639a5781237330fe40b1c7ff5b0542e07d`
- 第二次 tree hash：`5545fcfbd43fdeac8d5cb9a7106b17639a5781237330fe40b1c7ff5b0542e07d`
- 整个原型输出树两次 hash：`6e3bb90df7d9e2150e0d33a8f72a80005235db797fe7826953951c63951eb39c`

结果完全一致。

## 10. 当前限制

本原型只完成**迁移与保守 review 提炼**，尚未实现正式 V4：

- JSON Schema validator
- Gate V4 完整执行器
- production release builder
- schemaVersion=2 网站 adapter
- 全量人工复核 143 条 unclassified active link
- 11 个效力信息不足 lawVersion 的补证

因此 158 个 hazard 只是当前原型的“可形成 qualifying 链的保守比较子集”，不是正式 V4 production release 数量。

## 11. Phase 5 验收判断

通过：

- V3 SQLite 全程只读
- 全量实体迁出
- Stable ID 无静默重编号
- 无 broken FK
- r8 失效 link 未复活
- pending 未自动升级
- reviewedContentHash 重新计算
- link contextHashes 重新计算
- 私有来源字段未进入公开 candidate
- 两次重跑确定性一致
- r10 差异可解释
- main / site-selection / production 均未修改

**Phase 5 只读迁移原型完成。**

下一阶段应进入 Phase 6：迁移现有有效知识。具体做法是以本原型 candidate 为输入，先将已经通过保守 review 提炼且不在 quarantine 的现有有效知识纳入版本控制的 V4 `knowledge/` 候选工作面；pending、superseded、unclassified 与效力不明版本继续隔离，不为追求数量强行升级。Phase 9/10 再按既定顺序实现 Validator 与 Gate。正式生产仍不切换。
