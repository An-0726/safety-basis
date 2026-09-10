# V4 Strict Release Audit Report

> 生成时间：2026-09-10。只读审计，不修改任何知识实体。

## 结论

- **strictVerdict: BLOCK**
- blockerCount: 157
- warningCount: 1

## 实体与审查覆盖

| 实体 | 总数 | 审查数 | verified | pending | rejected |
|---|---|---|---|---|---|
| laws | 68 | 43 | 43 | 0 | 0 |
| law-versions | None | 43 | 43 | 0 | 0 |
| clauses | 76 | 54 | 54 | 0 | 0 |
| hazards | 662 | 642 | 642 | 0 | 0 |
| links | 181 | 181 | 128 | 32 | 21 |

## 链式发布门禁结果

- eligibleLinks: 126 / 181
- eligibleHazards: 113 / 662
- pendingLinks: 32
- backfill（20条补迁）eligible: 0 / 20

## Blocker 分类

- hazard_content: 48
- pending_link_on_blocked_hazard: 31
- law: 28
- lawVersion: 28
- clause: 22

## Blocker 详情（前50）

- **law** `LF_HAZCHEM_LAW`: review_missing
- **law** `LF_HAZCHEM_REG`: review_missing
- **law** `LF_L006`: review_hash_stale
- **law** `LF_L019`: review_hash_stale
- **law** `LF_L028`: review_hash_stale
- **law** `LF_STD_GB12158_2006`: review_missing
- **law** `LF_STD_GB12801`: review_missing
- **law** `LF_STD_GB12801_2008`: review_missing
- **law** `LF_STD_GB14444`: review_missing
- **law** `LF_STD_GB14444_2006`: review_missing
- **law** `LF_STD_GB15603_1995`: review_missing
- **law** `LF_STD_GB15607`: review_missing
- **law** `LF_STD_GB15607_2008`: review_missing
- **law** `LF_STD_GB15760_2004`: review_missing
- **law** `LF_STD_GB17120_1997`: review_missing
- **law** `LF_STD_GB18597_2001`: review_missing
- **law** `LF_STD_GB19517_2009`: review_missing
- **law** `LF_STD_GB2893_2008`: review_missing
- **law** `LF_STD_GB2894_2008`: review_missing
- **law** `LF_STD_GB5083_1999`: review_missing
- **law** `LF_STD_GB6514`: review_missing
- **law** `LF_STD_GB6514_2008`: review_missing
- **law** `LF_STD_GB7231_2003`: review_missing
- **law** `LF_STD_GB9448_1999`: review_missing
- **law** `LF_STD_GBZ188_2014`: review_missing
- **law** `LF_STD_TSG08_2017`: review_missing
- **law** `LF_STD_TSGZF001_2006`: review_missing
- **law** `LF_STD_TSGZF003_2011`: review_missing
- **lawVersion** `L006`: law_gate_failed
- **lawVersion** `L019`: law_gate_failed
- **lawVersion** `L028`: law_gate_failed
- **lawVersion** `LV_HAZCHEM_LAW`: review_missing; law_gate_failed
- **lawVersion** `LV_HAZCHEM_REG`: review_missing; law_gate_failed
- **lawVersion** `LV_STD_GB12158_2006`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB12801`: review_missing; law_gate_failed
- **lawVersion** `LV_STD_GB12801_2008`: review_missing; law_gate_failed
- **lawVersion** `LV_STD_GB14444`: review_missing; law_gate_failed
- **lawVersion** `LV_STD_GB14444_2006`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB15603_1995`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB15607`: review_missing; law_gate_failed
- **lawVersion** `LV_STD_GB15607_2008`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB15760_2004`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB17120_1997`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB18597_2001`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB19517_2009`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB2893_2008`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB2894_2008`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB5083_1999`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing
- **lawVersion** `LV_STD_GB6514`: review_missing; law_gate_failed
- **lawVersion** `LV_STD_GB6514_2008`: review_missing; invalid_validityStatus:superseded; effectiveDate_invalid_or_missing

## Warnings

- {"type": "pending_link_excluded", "id": "K_f0ef428ae23fcba6deb9f379", "hazardId": "H_0AB8998CB24041C894BB326A69"}

## 说明

- 本审计为只读，不修改 knowledge/ 或 release/。
- BLOCK 不代表数据错误，而是表示当前知识状态尚未满足严格发布条件（主要是 law/lawVersion/clause/hazard 的 review 缺失）。
- 最终 production 切换前必须消除所有 blocker 或经专业验收确认可豁免。
- build_release.py 的链式门禁已与本审计对齐（publishable=eligibleHazards=113）。
