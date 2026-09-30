# Source-integrity containment recovery — 2026-09-30

## Result and boundary

This targeted correction is based on commit `a5cc5e5ccc82c7b062a683217cdf855091946fca`. The canonical source records, official occupational-health text, current regulations index and resulting Gate decisions were independently rechecked.

- Withdrew `verified` by setting **6 hazard reviews + 6 corresponding link reviews + 1 clause-text review** to `rejected`, pending exact-source correction and fresh substantive review
- Preserved all six quarantined hazard entities, their link entities, their IDs/lifecycle, and original entity/context hash bindings; preserved `C_12158_2` including its suspect text
- Changed only `H_ZJWS_33_1.measures`, then substantively re-reviewed that exact hazard and its existing direct link rather than applying automatic hash re-signing
- Added `E_NHC_WORKPLACE_OH_20260930`; physical and manifest evidence counts are now **1235**
- Kept source hazard inventory **2130**: **1663 active**, 354 proposed, 113 superseded
- Dated Gate at **2026-09-30**: **1657 eligible hazards, 1791 eligible links, 1340 referenced clauses**; the only hazard/link eligibility changes are the six named quarantines

Source entities and private originals are preserved. Build and Gate checks establish engineering integrity, not corpus-wide legal-source correctness. Publication and deployment outcomes must be verified separately.

## Independently rechecked source failures

The following contradictions are directly observable in the restored canonical records and their linked clauses. They suffice to withdraw unsupported verification without inventing a replacement clause or repairing missing numerical exponents from inference.

| Hazard | Existing link clause | Rechecked issue |
|---|---|---|
| `H_12158_10_1_2` | `C_12158_10_1` | Hazard and measures turn GB/T 22845 into a flange/valve/joint bonding rule. The linked text is about clothing, shoes and gloves, and GB/T 22845 specifically concerns gloves |
| `H_12158_4_2_3_5_2` | `C_12158_4_2_2_1` | Evaluation/documentation for sliding or separable layered/nested nonconductors is mapped to a general conductor-grounding requirement |
| `H_12158_6_3_1_1` | `C_12158_4_2_2_3` | Material surface/volume resistivity of nonmetal liquid tanks/pipes is mapped to grounding/leakage resistance; `1×Ω` and `1×10Ω·m` are incomplete numerical conditions |
| `H_12158_6_3_2_2` | `C_12158_4_2_2_3` | Exposed nonconductor width/area limits and over-limit evaluation are mapped to grounding/leakage resistance |
| `H_12158_7_6_1` | `C_12158_4_2_2_1` | Dissipative conveyor-belt resistance tests are mapped to general grounding; `3×10Ω`, `7.5×Ω` and the trailing `相对湿度50%±` are incomplete |
| `H_12158_8_8_5_3` | `C_12158_4_2_2_1` | Process-specific electrostatic measures/documentation are mapped to general grounding |

Each link is `K_XLSX_WEB_<hazardId>`. Existing hazard and link definitions remain in source inventory for correction; rejected reviews prevent public projection.

`C_12158_2` is labelled `第2条` but starts with `/s…(3)` followed by hydrocarbon-liquid loading velocity and loading-arm diameter material. The formula and source location are not sufficiently intact to retain a verified-text claim. Its text review is rejected; the source entity is retained with canonical hash `2f3cdc1dd4be2dce00a22524e8ae87b4fdde3603bd2e50c9d9bfe30b7c3f8fac`.

### GB 12158 source limits

The official [GB 12158-2024 metadata](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=B4B6BEA653AB3C8218837E90115E747D) was re-read. It names **防止静电事故通用要求**, publication date **2024-12-31**, implementation date **2026-01-01**, and status **现行**. That verifies identity/status metadata, not the correctness of every imported quotation or applicability link.

The [HIPC PDF](https://www.hipc.org.cn/upload/files/20250408/1744076000682708.pdf) is an institutional repost, **not an official issuing source**. Retrieval timed out in this recovery; no claim here depends on having re-read or retained it. Exact replacement clauses and numerical values remain unverified. No official-source URL was substituted for a missing full-text verification.

The historical evidence reference `E_SAMR_GB12158_2024` is retained on rejected reviews for traceability. Its existing locator/URL metadata is not new proof and was not silently promoted or broadly repaired in this targeted task. Original verified rationales have been explicitly withdrawn.

### Frozen canonical hashes

The following hashes match the pre-repair records and their retained review bindings. The tests intentionally pin them until a separately evidenced source correction is reviewed; changing a hash alone is not a correction.

| Hazard | Hazard SHA-256 | Link SHA-256 |
|---|---|---|
| `H_12158_10_1_2` | `0e8a0d83530361b03f09dec30dee440b595adb54017b2e913d52d26fef6f3cc3` | `6fe472607b6127e80672c791336c78a9786345111e838617dbebb684511a08bf` |
| `H_12158_4_2_3_5_2` | `f33f1aa78dfb49ade47151f54ce31dabeb5e3eddb483429e301340e8f846d254` | `831fff7db5b47c739f5c2ccca88562d506f24b175a92369c80cd61819a2f86ea` |
| `H_12158_6_3_1_1` | `71ac75c08efdc5807b2f7e073efd598346a2676fc19065666c498b90398ca64b` | `7034dea0c986d3d798dea0fee0ee3a6d91a7b2c7cc4f358d6cdd67e72e4d7590` |
| `H_12158_6_3_2_2` | `8679cb03a293b1da93d352288ba249c743f68dfa82d1e5476c4126e7a3abb6ce` | `aa6ec231a5995d09934c0fb5440107e0fa0d50f4e6f0f6ed0f94f240f108484e` |
| `H_12158_7_6_1` | `c7c2761cbcd69cb18eddfbc54518d6f3c943aa335ce712761580c171a71e28cc` | `cdc55d089f4dc573009859fddc1b66172d90bb795fdcddddb3ac1f3983b52108` |
| `H_12158_8_8_5_3` | `2818557f79c8dba3c2a894de7ac8fbcc77b709cb88c4775226889f35a9a95d9b` | `efd86b41114d5b65b883e0f299f65076173fbcf9633c2bfd880dd6d12c2ae834` |

## Occupational-health correction and substantive review

### Verified official source

- [National Health Commission regulation text](https://www.nhc.gov.cn/wjw/c100221/202201/edc9ae24435d4d93ace796f33c29b029.shtml)
- [Current NHC regulations index](https://www.nhc.gov.cn/wjw/c100221/fg_gzk.shtml)
- Identity: 《工作场所职业卫生管理规定》, 国家卫生健康委员会令第5号, published 2020-12-31, effective 2021-02-01
- Both pages were directly observed in the cloud browser on 2026-09-30; web text retrieval initially returned HTTP 412
- The live index lists the rule under **现行有效**, at row 13 on its current first page. Search-index output had an older row number, so it was not substituted for the live index
- Article 33 expressly prohibits the two assignment types at issue; Article 34(9) requires relevant health-examination results and disposition/placement records; Article 60 confirms the effective date and repeals the prior 2012 rule

### Exact corrected measures

> 立即停止安排未成年工从事接触职业病危害的作业；对有职业禁忌的劳动者，调整至不涉及其所禁忌作业的岗位。结合劳动者年龄、职业健康检查结论与岗位危害核查用工安排，保留岗位调整及复核记录；不得以配发个人防护用品替代上述岗位安排限制。

This is practical corrective guidance implementing the prohibition, **not a purported verbatim quotation of the regulation**. It does not prescribe assigning everyone with an occupational contraindication away from every possible occupational hazard: the limitation is the specific work contraindicated for that worker. PPE cannot discharge the separate statutory placement prohibition.

The hazard's actor, two prohibited acts, applicable workplace context and corrected measures were checked individually. Existing direct link `K_XLSX_FT_E94F0A28CBE0F9F58B3750D8` targets `C_XLSX_FT_45C64317A1F75D412483E774`; its Article 33 sentence matches the official provision. The stored leading `33` is an extraction marker, not part of the legislation. Neither link nor clause entity was changed.

- Corrected hazard hash: `eadd974142ead919888810014c6ab467b2f2753a6b539793d8c460dd81710091`
- Unchanged link hash: `aeff90030c84d9ef0d572fca70d38cda0ea823aeed8fd948038bcda7bb857002`
- Unchanged clause hash: `a31ba257fac116fddd8c5f953b95064850f8a084d1746d31e4a402b08b7097fa`

The hazard review and link applicability review remain `verified` only after that substantive re-review. The hazard hash and link's hazard context hash were then updated to the exact corrected content. No blind rebind tool was used.

### Evidence snapshot scope

`E_NHC_WORKPLACE_OH_20260930.snapshotSha256` is `5ecb03290663d9f5208b4919699b2c4ab1abad50295923e2a298b472ffc28ab0`. It hashes the following **normalized UTF-8 observation excerpts**, joined with LF including one final LF. It is not a hash of downloaded HTML or a complete PDF. This explicit scope avoids falsely presenting a reconstructed excerpt as an original file snapshot.

```text
工作场所职业卫生管理规定
（2020年12月31日国家卫生健康委员会令第5号公布 自2021年2月1日起施行）
第三十三条 用人单位不得安排未成年工从事接触职业病危害的作业，不得安排有职业禁忌的劳动者从事其所禁忌的作业，不得安排孕期、哺乳期女职工从事对本人和胎儿、婴儿有危害的作业。
第三十四条 用人单位应当建立健全下列职业卫生档案资料：
（九）劳动者职业健康检查结果汇总资料，存在职业禁忌证、职业健康损害或者职业病的劳动者处理和安置情况记录；
第六十条 本规定自2021年2月1日起施行。原国家安全生产监督管理总局2012年4月27日公布的《工作场所职业卫生监督管理规定》同时废止。
国家卫生健康委员会规章库：现行有效；第13项：工作场所职业卫生管理规定（2020年12月31日国家卫生健康委员会令第5号公布 自2021年2月1日起施行）
```

## Validation and reopening conditions

The dedicated regression suite `tools/pipeline/tests/test_source_integrity_containment.py` passes **5/5** tests. It checks frozen identities/lifecycle/hash bindings; rejection of all 13 unsupported reviews; dated exclusion from the public chain; exact occupational measures and post-review bindings; official evidence scope and reconciled inventory.

Combined checks were run against the frozen knowledge set and the companion routing-only contract changes:

| Check | Result |
|---|---|
| Full Python pipeline suite | 209 tests passed |
| Node suite | 74 tests passed |
| Aggregate validator | Passed; no blocking failures |
| Strict release audit, 2026-09-30 | Passed |
| Publication integrity | Passed |
| Local bundle build and strict verifier | Passed; 1657 hazards / 1791 links / 1340 clauses / 3 field profiles |
| Existing three public profiles | Byte-identical to baseline; all six profile/review source files unchanged |
| Whitespace diff check | Passed |

Verified local bundle release hash: `6beee7a96a4aae05825a3a8973eca6e63d2ef48c96039a86567d434146f6014b`. Command logs and recovery comparisons are retained outside the repository. These engineering checks establish projection/integrity behavior; they do not prove legal-text accuracy across the corpus.

To reopen a quarantined record: obtain complete authoritative/original text of the currently applicable version; verify identity, exact locator, complete formulas/exponents/units, actor, obligation and applicability; correct the source entity only within authorized scope; then substantively review the resulting entity and each affected link/context. Do not bulk flip decisions or hashes to regain release counts.
