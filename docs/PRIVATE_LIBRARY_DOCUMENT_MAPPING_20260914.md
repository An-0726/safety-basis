# Private Library Document Canonical / Alias Mapping — 2026-09-14

## Scope and invariants

This report closes the read-only mapping action for the 170-row private `fulltext.sqlite3` document registry. It does **not** mutate SQLite, delete any document or FTS row, move any archive object, or renumber any stable ID.

Verified baseline: 170 documents; 20 duplicate-title groups; 4 duplicate-binary-SHA groups; 38 legacy `evidence/...` archive references. `knowledge/` remains the formal authority; SQLite `document_id` is not treated as a canonical law-version key.

Decision vocabulary:

- **SAFE_MERGE_CANDIDATE**: same real version, same raw SHA, same extracted text SHA. Identity-level dedupe is deterministic; a later physical DELETE still requires backup, reference scan, search-invariant checks and rollback.
- **ALIAS_ONLY**: same real version, but different raw carrier and/or extraction. Preserve both evidence carriers and FTS text; group to one canonical `knowledge` version.
- **CANONICAL_GAP**: same real version is established, but no current `knowledge` law/version exists. Do not invent a canonical ID inside SQLite; create/verify the formal identity in PHASE 4 first.
- **DO_NOT_MERGE**: same title but genuinely different legal/standard versions.

## 1. Exact-SHA duplicate groups

### 危险废物收集、贮存、运输技术规范

- raw SHA: `0a78de4416acc2a8f344956d5e5e265111078829fdb3e583a7142d772e2b88d4`
- decision: **ALIAS_ONLY** — same binary SHA but historical extraction differs; retain both FTS representations until a separate quality/physical-change batch.
- `L027HJ 2025-2012` — text `4f9b23066db047c5d3119db02e00dd4ed74a8846014018dfa3e00493c6bff9a9`; paragraphs 243; `archive/0a78de4416acc2a8f344956d5e5e265111078829fdb3e583a7142d772e2b88d4/original`
- `LF_L027L027` — text `381f0b370780c80a58849816663c32b7e0e7422998d5403d0884d09640c66d9f`; paragraphs 49; `evidence/L027.fulltext.pdf`

### 危险化学品仓库储存通则

- raw SHA: `13b9b4566d4a09a8686e36df8b373ec9e5da724dccd68bfffbabe45453d8f6de`
- decision: **ALIAS_ONLY** — same binary SHA but historical extraction differs; retain both FTS representations until a separate quality/physical-change batch.
- `L012GB 15603-2022` — text `39ac85f564b27f07909107de1192592827527d756a0c63c845884672ff08a4ae`; paragraphs 336; `archive/13b9b4566d4a09a8686e36df8b373ec9e5da724dccd68bfffbabe45453d8f6de/original`
- `LF_L012L012` — text `3bf594259cfa6807a92a3e6a9340150232852b8b60ce87e75513be53171347a7`; paragraphs 1959; `archive/13b9b4566d4a09a8686e36df8b373ec9e5da724dccd68bfffbabe45453d8f6de/original`

### 生产过程安全卫生要求总则

- raw SHA: `52789e230dc9e8cf8048c98454c5ffaea088237b72c4ab04af90a64f326ee59b`
- decision: **SAFE_MERGE_CANDIDATE** — same binary SHA and same extracted-text SHA.
- `LF_STD_GB12801_20082008` — text `d65679f3d4e15d2495eedbbba012b5c0b31ea9fed9233c52b3efc464efbd002d`; paragraphs 436; `archive/52789e230dc9e8cf8048c98454c5ffaea088237b72c4ab04af90a64f326ee59b/original`
- `LV_STD_DA490817FD80B99E1FAF4BCAGB/T 12801-2008` — text `d65679f3d4e15d2495eedbbba012b5c0b31ea9fed9233c52b3efc464efbd002d`; paragraphs 436; `archive/52789e230dc9e8cf8048c98454c5ffaea088237b72c4ab04af90a64f326ee59b/original`

### 消防设施通用规范

- raw SHA: `da5d08917f0b9b32b2be25b50b539f606428819d95589a011d8423d8471287f8`
- decision: **SAFE_MERGE_CANDIDATE** — same binary SHA and same extracted-text SHA.
- `L007GB 55036-2022` — text `e7fce95424c5f4a8f50efec355d7106f03eb87b9b01a21c3c270f094c7ef8de9`; paragraphs 701; `archive/da5d08917f0b9b32b2be25b50b539f606428819d95589a011d8423d8471287f8/original`
- `LF_L007L007` — text `e7fce95424c5f4a8f50efec355d7106f03eb87b9b01a21c3c270f094c7ef8de9`; paragraphs 701; `archive/da5d08917f0b9b32b2be25b50b539f606428819d95589a011d8423d8471287f8/original`

## 2. Same-real-version alias groups

| title | canonical | decision | member document keys |
|---|---|---|---|
| 仓储场所消防安全管理通则 | `L015` | **ALIAS_ONLY** | `LF_L015L015`<br>`L015XF 1131-2014（原GA 1131-2014）` |
| 低压配电设计规范 | `LV_STD_GB50054_2011` | **ALIAS_ONLY** | `LF_STD_GB500542011`<br>`L009GB 50054-2011` |
| 危险化学品仓库储存通则 | `L012` | **ALIAS_ONLY** | `LF_L012L012`<br>`L012GB 15603-2022` |
| 危险化学品安全管理条例 | `LV_HAZCHEM_REG` | **ALIAS_ONLY** | `LF_NPC_ff8080816f3cbb3c016f4087cdcc03d92013-12-07`<br>`LV_NPC_ff8080816f3cbb3c016f4087cdcc03d9国务院令第591号（国务院令第645号修订）` |
| 危险化学品目录（2015版） | `—` | **CANONICAL_GAP** | `LF_META_7A6DFF557CB39094FC88F041LV_META_3661A94BDB94C638CFD5A662`<br>`LV_META_3661A94BDB94C638CFD5A66210部门公告2015年第5号` |
| 危险废物收集、贮存、运输技术规范 | `LV_YJFGZ` | **ALIAS_ONLY** | `LF_L027L027`<br>`L027HJ 2025-2012` |
| 各类监控化学品名录 | `—` | **CANONICAL_GAP** | `LF_META_97168750500C4BE7D7E69865LV_META_ABE468D077A3918268DE18EF`<br>`LV_META_ABE468D077A3918268DE18EF工业和信息化部令第52号` |
| 吸附法工业有机废气治理工程技术规范 | `LV_STD_HJ2026_2013` | **ALIAS_ONLY** | `LF_L013L013`<br>`L013HJ 2026-2013` |
| 工贸企业粉尘防爆安全规定 | `L006` | **ALIAS_ONLY** | `LF_L006L006`<br>`L006应急管理部令第6号` |
| 易制毒化学品管理条例 | `LV_META_8982B9B15AF4365DE59CDFCE` | **ALIAS_ONLY** | `LF_META_0C856E722AF7822CA5E9415DLV_META_8982B9B15AF4365DE59CDFCE`<br>`LV_META_8982B9B15AF4365DE59CDFCE国务院令第445号（截至2018年修订文本）` |
| 易燃易爆性商品储存养护技术条件 | `—` | **CANONICAL_GAP** | `LF_STD_GB179142013`<br>`L024GB 17914-2013` |
| 毒害性商品储存养护技术条件 | `—` | **CANONICAL_GAP** | `LF_STD_GB179162013`<br>`LV_STD_BBF6F34C5D6F4D256C389C12GB 17916-2013` |
| 江苏省安全生产条例 | `L020` | **ALIAS_ONLY** | `LF_L020L020`<br>`L0202023年修订` |
| 消防设施通用规范 | `L007` | **SAFE_MERGE_CANDIDATE** | `LF_L007L007`<br>`L007GB 55036-2022` |
| 特种设备安全监察条例 | `—` | **CANONICAL_GAP** | `LF_NPC_ff8080816f3cbb3c016f40d306b705f32009-01-24`<br>`LV_NPC_ff8080816f3cbb3c016f40d306b705f3国务院令第549号` |
| 生产过程安全卫生要求总则 | `LV_STD_GB12801_2008` | **SAFE_MERGE_CANDIDATE** | `LF_STD_GB12801_20082008`<br>`LV_STD_DA490817FD80B99E1FAF4BCAGB/T 12801-2008` |
| 科研建筑设计标准 | `LV_STD_JGJ91_2019` | **ALIAS_ONLY** | `LF_STD_JGJ912019`<br>`LV_STD_JGJ91_2019JGJ 91-2019` |
| 腐蚀性商品储存养护技术条件 | `—` | **CANONICAL_GAP** | `LF_STD_GB179152013`<br>`LV_STD_GB17915_2013GB 17915-2013` |

Existing canonical targets independently checked against `knowledge/law-versions`:

- 仓储场所消防安全管理通则 → `knowledge/law-versions/L015.json`
- 低压配电设计规范 → `knowledge/law-versions/LV_STD_GB50054_2011.json`
- 危险化学品仓库储存通则 → `knowledge/law-versions/L012.json`
- 危险化学品安全管理条例 → `knowledge/law-versions/LV_HAZCHEM_REG.json`
- 危险废物收集、贮存、运输技术规范 → `knowledge/law-versions/LV_YJFGZ.json`
- 吸附法工业有机废气治理工程技术规范 → `knowledge/law-versions/LV_STD_HJ2026_2013.json`
- 工贸企业粉尘防爆安全规定 → `knowledge/law-versions/L006.json`
- 易制毒化学品管理条例 → `knowledge/law-versions/LV_META_8982B9B15AF4365DE59CDFCE.json`
- 江苏省安全生产条例 → `knowledge/law-versions/L020.json`
- 消防设施通用规范 → `knowledge/law-versions/L007.json`
- 生产过程安全卫生要求总则 → `knowledge/law-versions/LV_STD_GB12801_2008.json`
- 科研建筑设计标准 → `knowledge/law-versions/LV_STD_JGJ91_2019.json`

Notes:

- `GB 15603-2022` and `HJ 2025-2012` are **not** physical-delete candidates merely because each pair shares one raw SHA; their historical extracted-text hashes differ.
- `JGJ 91-2019` has identical extracted text across two different raw carriers; preserve both source carriers and use alias grouping.
- all other mapped pairs have different raw and/or text hashes, so their duplicate identity is a canonical/alias issue, not evidence-file duplication.

## 3. CANONICAL_GAP legal verification

### 危险化学品目录（2015版）

法规身份已核：2015年第5号公告，自2015-05-01施行；2022年第8号公告自2023-01-01调整柴油条目；2026年第3号公告又新增5种化学品。不能把“2015原始静态文本”直接当 2026-09-14 的完整现行目录版本，PHASE 4 必须建 base + amendments/现行表达。

Official verification:
- https://www.mem.gov.cn/gk/gwgg/201503/t20150309_241330.shtml
- https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202211/t20221107_426077.shtml
- https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202604/t20260429_602103.shtml

### 各类监控化学品名录

法规身份已核：工业和信息化部令第52号，2020-06-03公布并施行，原1996年第11号令同时废止。可在 PHASE 4 建 canonical law/version。

Official verification:
- https://www.miit.gov.cn/jgsj/aqs/jhwgz/art/2020/art_300aaa4cf68b44a3ab2d5d387d967ca7.html

### 易燃易爆性商品储存养护技术条件

法规身份已核：GB 17914-2013，2014-07-01实施，全国标准信息公共服务平台显示现行。可在 PHASE 4 建 canonical law/version。

Official verification:
- https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BD4BA33D46B2AD5DCA3F1EBA7E99BEE6

### 毒害性商品储存养护技术条件

法规身份已核：GB 17916-2013，2014-07-01实施，全国标准信息公共服务平台显示现行。可在 PHASE 4 建 canonical law/version。

Official verification:
- https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E7CE7A6707DCEB0130206D57D0751FDD

### 特种设备安全监察条例

法规身份已核：国务院令第549号（2009修订）；市场监管总局仍提供现行条例全文，商务部法规库标记现行有效。可在 PHASE 4 建 2009 修订 canonical version，并与《特种设备安全法》并行而非互相替代。

Official verification:
- https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_39ccf49cb9924eb9a4c496d050f027cd.html

### 腐蚀性商品储存养护技术条件

法规身份已核：GB 17915-2013，2014-07-01实施，全国标准信息公共服务平台显示现行。可在 PHASE 4 建 canonical law/version。

Official verification:
- https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=2FAE236436667CD9B9E1D1B2D1E6D2D4

Conclusion: the six groups are not candidates for title-based deletion. Five can proceed to normal PHASE 4 canonical identity/version creation. `危险化学品目录（2015版）` needs explicit amendment modeling because the live catalogue has 2022 and 2026 changes.

## 4. Same-title genuine version pairs — DO_NOT_MERGE

### 木材加工系统粉尘防爆安全规范

- `AQ 4228-2012`: current through 2026-10-31; official standards platform records repeal on 2026-11-01.
- `AQ 4228-2025`: published 2025-10-15, effective 2026-11-01, fully replaces AQ 4228-2012.
- decision: **DO_NOT_MERGE**. Preserve separate historical/current/upcoming identities and succession.
- official: https://std.samr.gov.cn/hb/search/stdHBDetailed?id=8B1827F1E2A5BB19E05397BE0A0AB44A
- official: https://std.samr.gov.cn/hb/search/stdHBDetailed?id=460FBF4254442E79E06397BE0A0AA2A9

### 用电安全导则

- `GB/T 13869-2017`: `knowledge/law-versions/LV_STD_GBT13869_2017.json`, active through 2027-01-31.
- `GB/T 13869-2026`: `knowledge/law-versions/LV_STD_GBT13869_2026.json`, upcoming, effective 2027-02-01.
- decision: **DO_NOT_MERGE**. Keep both versions under the same law identity and preserve succession.

## 5. Legacy `evidence/...` migration matrix

Rule applied: a legacy reference may be rebound only when an existing current archive object has the **same raw SHA** and the version relationship is the same. Title similarity is insufficient.

Drive archive verification found exactly one current archive folder whose name equals one of the 38 legacy rows' raw SHA values: `0a78de4416acc2a8f344956d5e5e265111078829fdb3e583a7142d772e2b88d4`.

| title | document key | legacy ref | SHA | decision | target |
|---|---|---|---|---|---|
| 危险废物收集、贮存、运输技术规范 | `LF_L027L027` | `evidence/L027.fulltext.pdf` | `0a78de4416acc2a8f344956d5e5e265111078829fdb3e583a7142d772e2b88d4` | **SAFE_REBIND** | `archive/0a78de4416acc2a8f344956d5e5e265111078829fdb3e583a7142d772e2b88d4/original` |
| 危险化学品目录（2015版） | `LF_META_7A6DFF557CB39094FC88F041LV_META_3661A94BDB94C638CFD5A662` | `evidence/LV_META_3661A94BDB94C638CFD5A662.catalog.doc` | `4ad47e211763b849e6339ab09dd28cc2c55686463a15d13bf31c736d2cc12070` | **KEEP_LEGACY** | `` |
| 各类监控化学品名录 | `LF_META_97168750500C4BE7D7E69865LV_META_ABE468D077A3918268DE18EF` | `evidence/LV_META_ABE468D077A3918268DE18EF.catalog.docx` | `9453a57f2252397ee1272172330732105269a46ba019ad0a86f2fb87e1df9c4b` | **KEEP_LEGACY** | `` |
| 吸附法工业有机废气治理工程技术规范 | `LF_L013L013` | `evidence/L013.fulltext.pdf` | `aa7f034ca4651903f30a76cde0cc28874a29007d369bc574f2a09f08b777d8bf` | **KEEP_LEGACY** | `` |
| 工贸企业粉尘防爆安全规定 | `LF_L006L006` | `evidence/L006.metadata.html` | `6500f619d8a699071b9d244fa79c70708ca8cfa0ae82d10ed25bae8c8ef5f8b8` | **KEEP_LEGACY** | `` |
| 易制毒化学品管理条例 | `LF_META_0C856E722AF7822CA5E9415DLV_META_8982B9B15AF4365DE59CDFCE` | `evidence/LV_META_8982B9B15AF4365DE59CDFCE.metadata.html` | `f03f336613b552640336edede99cb1afaed9ff40a055c21cdecabe3cc5fa170b` | **KEEP_LEGACY** | `` |
| 建设项目安全设施“三同时”监督管理办法 | `LF_REG_SAN_TONG_SHILV_REG_SAN_TONG_SHI_2011` | `evidence/LV_REG_SAN_TONG_SHI_2011.fulltext.html` | `4ff2e4ca85147afb968c6a91f9a482e0ca9c4d3979e7506d5cc2839fc4eb5ccc` | **KEEP_LEGACY** | `` |
| 安全生产培训管理办法 | `LF_AQPXGLLV_AQPXGL` | `evidence/LV_AQPXGL.metadata.html` | `a7b3946e365ea360efc7915eed73dc5292d7533a91183b67535688de50420318` | **KEEP_LEGACY** | `` |
| 生产安全事故罚款处罚规定 | `LF_SGFKCFLV_SGFKCF` | `evidence/LV_SGFKCF.metadata.html` | `c9a4fdd9e014b6bc44d5b95abfd3a5318ad20c92ba24fc50fb8d722e084275ef` | **KEEP_LEGACY** | `` |
| 企业安全生产费用提取和使用管理办法 | `LF_QYFYBFLV_QYFYBF` | `evidence/LV_QYFYBF.fulltext.pdf` | `4cdda25d69d62405d20abea276e2058fab7766e0a2feb80569bef287f44d2170` | **KEEP_LEGACY** | `` |
| 安全生产事故隐患排查治理暂行规定 | `LF_SGSGTLLV_SGSGTL` | `evidence/LV_SGSGTL.metadata.html` | `fd6e880a0228c71f7e519b82b04e71eb31364ead02fd93ae12da53c037cd8477` | **KEEP_LEGACY** | `` |
| 安全生产违法行为行政处罚办法 | `LF_APGJBFLV_APGJBF` | `evidence/LV_APGJBF.fulltext.pdf` | `f8e8940f57917e08ad7ea8f92ffd09185a9d12f0960d6bb4aee1698b485c5afd` | **KEEP_LEGACY** | `` |
| 特种设备作业人员监督管理办法 | `LF_META_58A30021A5BA9F36E9C271D9LV_META_771B100258743094F7C7A3B4` | `evidence/LV_META_771B100258743094F7C7A3B4.fulltext.pdf` | `1685d4aa0c997d9435e746e17ade4a9f9f2dc03c91e6605981422fd2c6735630` | **KEEP_LEGACY** | `` |
| 中华人民共和国安全生产法 | `LF_META_99BB97DB60A5B5A5A9CE3242LV_META_534BC3AC4FAD951F7D9D1D14` | `evidence/LV_META_534BC3AC4FAD951F7D9D1D14.metadata.html` | `704430dd99dccac838b05b6f3d0eb56cab11807c88aee6540e7f19a3dd77695d` | **KEEP_LEGACY** | `` |
| 中华人民共和国消防法 | `LF_META_6923074959342083ADEFE1D4LV_META_76CBC5E3A95A053C6D0AE11A` | `evidence/LV_META_76CBC5E3A95A053C6D0AE11A.metadata.html` | `f69ae284dfd94703836aa645f66f3d0d4ac06f932c511293de69fad29f33f476` | **KEEP_LEGACY** | `` |
| 中华人民共和国职业病防治法 | `LF_META_7D6DC3BFF6A9B06771005300LV_META_FD60AD8CF2D195D5BE5C19D6` | `evidence/LV_META_FD60AD8CF2D195D5BE5C19D6.catalog.html` | `e6aea769ba888ea88f7fade6fd14b22dcb2a8c05eb5aac3cc058384c3071085a` | **KEEP_LEGACY** | `` |
| 中华人民共和国特种设备安全法 | `LF_META_75AA3E6BD8656D93792F0F75LV_META_CCAA849DB8447522B4449E48` | `evidence/LV_META_CCAA849DB8447522B4449E48.fulltext.pdf` | `f0e4898af804a9a267c31c30f54b24a5b0f1c1344112b5fc0f861ce6267169c5` | **KEEP_LEGACY** | `` |
| 中华人民共和国环境保护法 | `LF_META_BD25F96A9374BE7F8AD411F9LV_META_5458CE68D11522BA22FF67E4` | `evidence/LV_META_5458CE68D11522BA22FF67E4.metadata.html` | `5753b52560eef12817f7014c639c73603fcbefae8533c96da56da5790b097377` | **KEEP_LEGACY** | `` |
| 中华人民共和国固体废物污染环境防治法 | `LF_META_03113B19029DAB4B87A8C397LV_META_0F25632CBAC629D05C936471` | `evidence/LV_META_0F25632CBAC629D05C936471.metadata.html` | `247e31b3e14687fea94102ec9a6ff7f21932aef971761b318ee2eaca319a3ef6` | **KEEP_LEGACY** | `` |
| 中华人民共和国大气污染防治法 | `LF_META_EC74155229BD81DB7DC00F61LV_META_E6F8CF41CFA85E6F94051803` | `evidence/LV_META_E6F8CF41CFA85E6F94051803.metadata.html` | `4c68623fbe60b6d86d50e793d8f3e48f9775d81b2121c3bf41c306bbbad83dad` | **KEEP_LEGACY** | `` |
| 中华人民共和国水污染防治法 | `LF_META_362BA3D8CB86A2B44C7C0B86LV_META_2E00931902B9FF5559ADBA04` | `evidence/LV_META_2E00931902B9FF5559ADBA04.metadata.html` | `aa44b173be1ddfb3389c025f43923b5059577679a755aaaee8c13b25951f12f2` | **KEEP_LEGACY** | `` |
| 中华人民共和国噪声污染防治法 | `LF_META_4D061164D5BE6FBE74E92653LV_META_646A315B1AE8F17A7EAED030` | `evidence/LV_META_646A315B1AE8F17A7EAED030.metadata.html` | `e301a22dca88c01d8f9fceb11dc81c0c2fdb6a28ce96c771f75442aee8476df9` | **KEEP_LEGACY** | `` |
| 中华人民共和国突发事件应对法 | `LF_META_C73C160C038AD8D30C246A73LV_META_814B302F8BBC7089C76E928D` | `evidence/LV_META_814B302F8BBC7089C76E928D.metadata.html` | `124fbc221371cd6a4feac24b42c5f634115ef3c85623f2448c6040d1ffa430fd` | **KEEP_LEGACY** | `` |
| 使用有毒物品作业场所劳动保护条例 | `LF_META_07687850DB2A100F354577D2LV_META_59B66052E28A07113BD2E797` | `evidence/LV_META_59B66052E28A07113BD2E797.metadata.html` | `f03e5a9070cc25588628730fd301a1081072a3732369d64ad9f9a0b1471dc9aa` | **KEEP_LEGACY** | `` |
| 危险化学品重大危险源监督管理暂行规定 | `LF_META_F009DC921C25FC2DA86A15FDLV_META_96BA5CFE20A16B7352341F2C` | `evidence/LV_META_96BA5CFE20A16B7352341F2C.metadata.html` | `77951d0927afbb9b941fe36dc64c7eefb0528a830691c5836f028f3171b2c127` | **KEEP_LEGACY** | `` |
| 危险化学品生产企业安全生产许可证实施办法 | `LF_META_F24BF9D4623FEF4C9D1B1A80LV_META_7B91BE7E022C3E08CFEE5CCB` | `evidence/LV_META_7B91BE7E022C3E08CFEE5CCB.metadata.html` | `172a511f8782fe0b147d6ba3a48fd5008239ff3bd247de680e075fd96b9c16ba` | **KEEP_LEGACY** | `` |
| 危险化学品经营许可证管理办法 | `LF_META_A82EBBE6466CE15821248256LV_META_DD6E07104A77299A996147FE` | `evidence/LV_META_DD6E07104A77299A996147FE.metadata.html` | `dc60b61b3e19bc704ea774fc6032d258aee34e4e01421c84ffb464cd44800235` | **KEEP_LEGACY** | `` |
| 危险化学品登记管理办法 | `LF_META_A995A377EC0F06173D62183ELV_META_45B21D2723805E950B835095` | `evidence/LV_META_45B21D2723805E950B835095.metadata.html` | `a912e537d87b73d781249860398d64bb92ff4e5dda133bcc1298405b3070bbaf` | **KEEP_LEGACY** | `` |
| 危险化学品输送管道安全管理规定 | `LF_META_75AA73910170D933566310B4LV_META_C94CF16FA2EC3C98F949FDE4` | `evidence/LV_META_C94CF16FA2EC3C98F949FDE4.metadata.html` | `51f25e8449ac466b23a7f537f9a897ba60284cae74fb37d0c3ede48da09235c6` | **KEEP_LEGACY** | `` |
| 危险化学品建设项目安全监督管理办法 | `LF_META_5FB7A59015CC8C2F7B523B3ALV_META_A625888934429591909259A7` | `evidence/LV_META_A625888934429591909259A7.metadata.html` | `b6808a943e2387c7e2979b34ca7e453ce7714f1fd19447838b24da41bfdf8099` | **KEEP_LEGACY** | `` |
| 工贸企业重大事故隐患判定标准 | `LF_META_4BA2C895A6803D54F1C1D5E8LV_META_8F66F127B996271163931B85` | `evidence/LV_META_8F66F127B996271163931B85.metadata.html` | `44586de2885d9d1bf439c6efe8e89f265848b83dda5576d41a721aa36b310c0c` | **KEEP_LEGACY** | `` |
| 工贸企业有限空间作业安全规定 | `LF_META_9FD822433EF5940780710449LV_META_FC43256C0F595A6F9165697E` | `evidence/LV_META_FC43256C0F595A6F9165697E.metadata.html` | `90cb5235ff9a37f90eec0e59ca3fb8d926960266bcdfc4d8c78c710d3f78d227` | **KEEP_LEGACY** | `` |
| 生产安全事故应急预案管理办法 | `LF_META_0681E7B70133EB6ED40C7DC8LV_META_8FC4CBFDFB62D66BDDF41C8F` | `evidence/LV_META_8FC4CBFDFB62D66BDDF41C8F.metadata.html` | `2d04286fc34d408d746b0bf7b569294ecbc9d9d3a57a56292ee831981330790b` | **KEEP_LEGACY** | `` |
| 生产经营单位安全培训规定 | `LF_META_528285E4F154F948A39C85DBLV_META_02831A2D59892B8976EF98AB` | `evidence/LV_META_02831A2D59892B8976EF98AB.metadata.html` | `bbc77f5f672cebb80ad1d807bff62c0e5857a7cf46b95cce1a94a84919b8dacb` | **KEEP_LEGACY** | `` |
| 特种作业人员安全技术培训考核管理规定 | `LF_META_AEB4555D8E67E9596656764BLV_META_E19AF5C190049781D89B3E1C` | `evidence/LV_META_E19AF5C190049781D89B3E1C.metadata.html` | `7037f15c29fb94b9e598312500be74978c9e68373b260d8218947353e3baf36d` | **KEEP_LEGACY** | `` |
| 江苏省工业企业安全生产风险报告规定 | `LF_REG_JS_RISK_REPORTLV_REG_JS_RISK_REPORT_2021` | `evidence/LV_REG_JS_RISK_REPORT_2021.metadata.html` | `52715bd62404b9c3552fd86b8095f29da4ad75d06a0fd8fac21be01eb4f214a0` | **KEEP_LEGACY** | `` |
| 南京市安全生产条例 | `LF_META_A8D6D39B565355613868548BLV_META_D8AC5C82B2E301503A9BDDA6` | `evidence/LV_META_D8AC5C82B2E301503A9BDDA6.metadata.html` | `5823eea75cd5364c934f12170acec6ee9e2df2baaee736d7251cd3bc4353d0d7` | **KEEP_LEGACY** | `` |
| 南京市消防条例 | `LF_META_0FDF5327E4DFEA3A35FC2598LV_META_46497A5D41C2B7F21D4BE251` | `evidence/LV_META_46497A5D41C2B7F21D4BE251.metadata.html` | `51bb132a2469ce30c0b4301837e03da590f2aa833f8e3931cac60727392734fd` | **KEEP_LEGACY** | `` |

Migration totals:

- `SAFE_REBIND`: 1 (`LF_L027\x1fL027` → `archive/0a78de.../original`)
- `KEEP_LEGACY`: 37
- no title-only rebinds

For the 37 `KEEP_LEGACY` rows, preserve the original `archive_ref` as provenance/missing-legacy metadata until an exact-byte source is recovered. Do not rewrite them to a similarly titled current archive object.

## 6. Four-class change list

### 可安全归并

- `消防设施通用规范` (`GB 55036-2022` pair): same raw SHA + same extracted-text SHA.
- `生产过程安全卫生要求总则` (`GB/T 12801-2008` pair): same raw SHA + same extracted-text SHA.
- scope is identity-level deterministic dedupe. Physical SQLite deletion remains a separate high-risk operation and is **not authorized by this report**.

### 仅保留 alias

- the 10 already-`knowledge`-mapped same-real-version groups other than the two deterministic exact duplicates.
- `GB 15603-2022` and `HJ 2025-2012` specifically remain alias-only because same raw files have different historical extraction text.
- all distinct source carriers remain evidence; no archive move/delete.

### 待法规核验 / canonical 纳管

- legal identity/effectivity has now been verified for all six prior `knowledge_unmapped` groups; what remains is PHASE 4 formal canonical modeling.
- `危险化学品目录（2015版）` remains the only one requiring nontrivial current-version modeling because 2022 and 2026 amendments changed the live catalogue.

### 禁止合并

- `AQ 4228-2012` vs `AQ 4228-2025`.
- `GB/T 13869-2017` vs `GB/T 13869-2026`.

## 7. Rollback / physical-change guard

No physical mutation was performed in this phase-closing analysis, so rollback is not needed. If a later SQLite cleanup is approved, it must be its own batch and must:

1. create a consistent backup of the work SQLite database;
2. record document count, FTS row count, paragraph-count sum, per-document row counts, raw/text SHA values, archive refs and representative search counts;
3. only touch explicitly enumerated deterministic duplicate rows;
4. preserve alias metadata and every source/evidence carrier;
5. re-run all invariants and representative searches after the write;
6. restore the backup on any count, hash, search, archive-ref, version, or evidence-traceability regression.

## 8. Phase conclusion

The PHASE 3 read-only mapping requirement is complete. There is no need to hand legal/canonical judgment to Luna. The next logical cursor is PHASE 4: formalize the six canonical gaps (with amendment-aware treatment for the hazardous-chemicals catalogue), then reconcile any remaining private document aliases against the resulting `knowledge` IDs before considering a separate physical SQLite dedupe batch.
