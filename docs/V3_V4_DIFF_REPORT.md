# V3 / V4 差异验收报告

> 状态：`INTERIM — FINAL REFRESH REQUIRED`
> 最后同步：2026-09-10
> V3 基线：`source/master/safety.sqlite3`
> V3 SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
> V3 全程只读，未修改。

## 1. 当前说明

本文件原版本是在 V4 仍只有约 543 publishable hazards / 596 links / 523 eligible links 时生成的中途快照。随后 `chat-v4` 又进行了大规模 link backfill、hazard 收口、Requirement 校准和 Gate 逻辑统一，因此旧数字不能继续作为 Phase 16 最终差异验收结论。

最终差异报告必须等当前知识树稳定、重新生成最终 candidate 后再做一次完整 V3 → V4 对比。本文件现在保留已确认的结构性结论，同时明确哪些项目仍待最终刷新。

## 2. 当前 V4 真实规模

以当前 `knowledge/manifest.json` counts 为准：

- laws: 75
- lawVersions: 75
- clauses: 88
- hazards: 712
- links: 735
- requirements: 75
- evidence: 567
- successions: 23

上一稳定 candidate（本轮 manifest 元数据修正前）记录：

- publishable hazards: 596 / 712
- eligible links: 666 / 735
- link reviews: 666 verified / 19 rejected / 0 pending
- production: false

由于 Phase 16 已修改 `knowledge/manifest.json`，最终 candidate 需要重建后才能生成新的最终 hash 和最终差异统计。

## 3. 已确认的 V3 → V4 结构性变化

以下结论仍成立，不依赖中途数量：

1. V4 保留 Stable ID 作为迁移和追溯核心，没有为了重构而全量重新编号。
2. V4 将 law identity、lawVersion、clause、hazard、link、requirement、evidence、succession 等关系显式结构化。
3. V4 对 link 采用合法 role 集合并建立逐条 review；不能把 V3 历史 link 机械继承为已通过。
4. V4 引入 hazard lifecycle / superseded / merged 处理，复合 hazard 拆分后仍保留父实体追溯。
5. V4 发布判定采用 hazard → link → clause → lawVersion → law 的共享链式 Gate，而不是旧 V3 通用 dependency hash 作为唯一真伪依据。
6. V4 允许局部条款核验，不要求取得整部标准全文才允许建立一个已可靠核验的 clause。
7. V3 r8 历史批量误判不得因为追求数字一致而回灌 V4。

## 4. 最终差异验收必须重新执行的项目

最终 candidate 稳定后至少重新比较：

- V3 最新可靠 release 中的已发布 hazard 是否无故丢失；
- hazard Stable ID、标题、专业描述、整改措施；
- law identity、lawVersion、实施/废止状态；
- clause locator 与条款文本；
- hazard—clause 关系和 role；
- direct/fallback/supporting 角色变化是否合理；
- merge/split/superseded 的去向；
- 搜索关键词覆盖；
- 分类、场所筛选；
- law index；
- 页面、PWA、Service Worker；
- 公开数据隐私扫描；
- V3 已知错误是否被 V4 重新引入。

## 5. 差异分类标准

最终报告中的每项差异必须归入以下之一：

- `EXPECTED_STRUCTURAL_CHANGE`：由 V4 架构变化造成，且可解释。
- `QUALITY_IMPROVEMENT`：V4 修正 V3 错误、弱依据、非法 role、复合隐患等。
- `CONTENT_CORRECTION`：法规版本、条款、隐患描述或整改措施经过核验后的纠正。
- `INTENTIONAL_EXCLUSION`：历史、merged、superseded、正向事实或不满足发布条件的实体被排除。
- `REGRESSION`：V4 无合理原因丢失或破坏了 V3 的可靠能力；必须修复。
- `REVIEW_REQUIRED`：差异尚不能专业判断，不得强行归类为改进。

## 6. 当前已知风险

- 原报告中的旧 publishable/link 数字已经过期。
- 最终候选尚未在本轮 manifest 修改后重建，因此当前不能给出最终 V3/V4 数量差异结论。
- 最终差异报告不能只对比总数，必须对关键 Stable ID、内容和法规链做语义对比。

## 7. 当前结论

V3 冻结基线仍有效；V4 已进入 Phase 16。此前差异检查没有发现需要回滚架构的根本问题，但**最终 V3/V4 差异验收尚未完成**。

本文件的最终刷新必须在最终 candidate 重建并通过 validator/gate/strict audit 后执行。总验收顺序以 `docs/V4_FINAL_ACCEPTANCE.md` 为准。
