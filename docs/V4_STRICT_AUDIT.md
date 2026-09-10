# V4 Strict Release Audit Report

> 生成时间：2026-09-10，基于共享核心 release_gate_core.py
> asOf: 2026-09-10

## 最终判定

**strictVerdict: PASS**

## 实体规模

- laws: 74
- lawVersions: 74
- clauses: 85
- hazards: 712
- links: 209

## 发布门禁分类

- releaseBlockers: **0**
- inventoryWarnings: 486
- excludedEntities: 108
- eligibleHazards: 162
- eligibleLinks: 186

## 分类说明

- **releaseBlockers**：真正影响当前发布投影的硬 blocker。当前为 0，无任何当前 publishable Hazard 的链路引用 repealed/upcoming/unknown LawVersion。
- **inventoryWarnings**：库存数据问题（active 但暂无合格依据的 backlog、pending link、supporting-only link），不阻塞 production。
- **excludedEntities**：历史/非发布实体（superseded/merged Hazard、repealed/upcoming LawVersion、rejected link），允许留在知识库但不进入当前发布依据。

## 普通 Gate 与 Strict Gate 一致性

gate_v4.py RELEASE 阶段已接入共享链式门禁。strictBlockers=0 时 RELEASE=PASS；strictBlockers>0 时即使 sourceStateHash 一致也强制 BLOCK。
