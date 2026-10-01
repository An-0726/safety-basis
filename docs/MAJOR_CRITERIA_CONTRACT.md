# 重大事故隐患判定目录与直接依据专题 v1

## 两个正交视图

- `data/major-criteria-catalog.json`：受控标准版本的规范条文。条款不需要已有隐患 H 或关联 K；仍须 C→LV→LF、证据和当前审核链全部通过 Gate。
- `data/major-criteria-topic.json`：现有隐患的精确 direct H→K→C→LV 关联。专业分类不变；检索命中、标题文字、fallback/supporting、全文提及均不能取得专题资格。
- 两者均 `wholeNormNotFieldFinding: true`。整条规范、直接关联或条款覆盖并不是某企业现场重大隐患结论。每次使用仍应核对主体、设备、行业、事实触发条件及适用版本。
- 第一版只有工贸令第10号和 GB 45067-2024 两个受控版本，`allIndustryCoverage: false`；不声称覆盖全行业。

原有 hazard/clauses/law-index/search/taxonomy 与 governed field profiles 发布规则保持原样。新目录不扩张旧法条分片或制造隐患凑数。整合时另行撤回错误依据，会按原 Gate 自然影响原有集合。

## 受控选择与来源边界

`knowledge/major-criteria/v1/catalog.json` 是明确的目录配置，不是独立法源、不签发审核、不生成或修改源实体/review。

每部标准绑定精确 LF/LV 身份、名称、文号、版本、官方入口、LF/LV 内容哈希；选择的规范 C 绑定内容哈希，专题每条 H/K/C 链绑定完整上游依赖指纹（含源隐患全部关联）。变更源内容、审核、证据或关联必须先重新核验选择，不能自动刷新 pin 来恢复发布资格。新选择及范围变更需要明确逐项核验，禁止关键词发现后自动纳入或批量签审。

第一版目录选择：

- 工贸令第10号：`C_PDDB_3` 至 `C_PDDB_14`，共12整条。第三至十三条64个列项，与第十四条失效/无效通则分开；第十四条不算第65项。完整文件还有第一、二、十五条，故 `wholeStandardComplete: false`。同条重复记录和摘项不重复计入目录覆盖。
- GB 45067-2024：`C_GB45067_4_1` 至 `_4_10`，共10整条。4.2、4.6、4.8、4.9无 H/K 也可独立发布。本轮补以施甸县政府公开的完整11页标准原件逐条复核；十C在明确排版规范化（空白、逗号/括号全半角和范围波浪号）后全部一致。该范围共47个字母列项，4.1d是转致项，不重复算成独立叶子判据；不含第1—3章、前言、引言、参考文献，仍不是整本标准全文。

工贸完整官方原文：[应急管理部规章正文](https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/202305/t20230523_451578.shtml)。[发布说明](https://www.mem.gov.cn/xw/ztzl/2023zt/zzpc2023/dybs_5536/202305/t20230524_451669.shtml)明确64项。GB完整原件见[施甸官方发布页附件](https://www.shidian.gov.cn/info/4492/3706283.htm)。GB身份与实施日期来自[国家标准全文公开系统](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=081C93E3186E0D1FE5CB034093C47A53)。

已发现 L019 的 `C_MEM10_13` 与 `C_MEM10_4_2` 正文不符官方所标条号，关联4个H。新专题将这4条精确关联列为 `pendingTopicLinks`，不发布；不能因旧 Gate 已通过而再次传播错误。目录配置本身不撤回源审核；本地整合另纳入独立审阅的2C/4K review拒绝补丁，原实体和历史审核保留。第三个旧转述 `C_MEM10_8_7` 已由独立精准修复将唯一K重接逐字规范 C_PDDB_8；仅该selector随经审新链更新，不批量刷新pin。K.applicability明确轻工企业、第八条第（七）项，不将第八条其他分项套用到当前H。新K真实审核日期为2026-10-01，因此本专题在9月30日有19个H、5条未纳入，10月1日20个H、4条未纳入；这是额外审核日期Gate结果，不是更改法律实施日，也不等于原共享Gate已按审核发生日期回溯。

## 公开 schema

机器可读 schema：`tools/v4/schemas/major-criteria-catalog.schema.json`、`major-criteria-topic.schema.json`。严格 verifier 还把整个公开对象与稳定源重新计算结果逐字段比较，封装哈希重算也不能绕过语义投影检查。

Catalog 顶层：`schemaVersion:1`, `asOf`, `wholeNormNotFieldFinding:true`, `catalogScope:"controlled_reviewed_standards_only"`, `allIndustryCoverage:false`, `standards`。

每部标准：

- `id`/`lawVersionId` 为原 LV 稳定ID
- `standardVersion`：`lawId`, `name`, `documentNumber`, `versionKey`, `officialSourceUrl`, `effectiveDate`, `endDate`, `validityStatus`
- `officialScope`：`label`, `sourceUrls`, `wholeStandardComplete:false`
- `coverage`：`status` 为 `reviewed_scope_complete` 或 `partial`；`reviewedClauseCount` 只数本目录已发布记录；`reviewedWholeClauseCount` 与 `reviewedSubitemClauseCount` 不混用；`expectedWholeClauseCount` 是明确选择范围的整条数；`expectedJudgmentItemCount`/`reviewedJudgmentItemCount` 未核为 null，不拿C数冒充判定列项数；`wholeStandardComplete:false`
- `clauses`：`clauseId`, `article`, `quote`, `lawVersionId`, `sourceUrl`, `checked`, `status`, `granularity` (`whole_clause`/`subitem`), `directHazardIds`
- `directHazardIds` 与 `directHazardCount`：该标准的当前专题关联隐患，去重H。条款的 `directHazardIds` 仅为指向此原始C的精确链，不按相似文字或条号合并其他C

Topic 顶层：`schemaVersion:1`, `asOf`, `wholeNormNotFieldFinding:true`, `associations`, `hazardIds`, `coverage`。

- 每个 association：`hazardId`, `linkId`, `clauseId`, `lawVersionId`, `role:"direct"`, 原样 `applicability`, 可空 `jurisdictionCode`
- `coverage.excludedAssociationCount`/`excludedHazardCount` 仅指受控专题里显式待复核或当前精确链失效的关联，不表示全行业缺口。`exclusionReason` 为无私有字段的说明
- `associations` 的 clauseId可指向原公开条款分片的旧摘项/同条记录，不必在规范目录22条中。UI应通过原隐患详情追溯原链接；规范正文只渲染catalog选定条款，不复制这些摘项

## 门禁、快照与隐私

额外限制不放松现有 Gate：严格ISO实施/终止日期（终止日排除）、显式审核日期不得晚于asOf、所有指定证据对象存在、精确direct角色、依赖内容pin一致。未审、缺review、过期、即将实施、伪造/未列入的标准、缺证据、重ID、私有路径均不可进入。未传asOf不可运行。

公开序列化只列明字段。配置hash、依赖指纹、审核人、审核正文、待复核具体ID清单、证据和私有inventory不写入公开包；自动扫描不能识别任意正文内的私人信息，逐字审核仍有责任。

`release_snapshot.FORMAL_NAMESPACES`包含新配置，构建器与verifier都基于同一稳定私有副本，`snapshotSha256`绑定配置源；配置变化即便不改变最终输出也不能沿用旧源验收。

统一manifest新增 `files.majorCriteriaCatalog`/`majorCriteriaTopic`；counts新增 `majorCriteriaStandards`, `majorCriteriaClauses`, `majorCriteriaHazards`, `majorCriteriaAssociations`。两文件纳入`site-manifest.fileHashes`、`checksums.json`和`releaseHash`，strict file allowlist拒绝额外私有JSON。

`check_major_criteria.py`进入validate_all阻断检查，只验证配置schema与选定实体/证据引用完整性，不把未完成覆盖或待审数量当作全局失败或批准。实际发布须再次通过上述日期、内容与审核检查。

## 验证

`python -m unittest discover -s tools/pipeline/tests -p test_major_criteria.py -v`

覆盖无H/K规范条款、整条/摘项分计、未知覆盖、候选/缺审核/陈旧审核/已变语义pin、失效日期、未来审核日期、缺证据、伪标准/泛文本链、非direct关联、私有字段、稳定快照源和重封装篡改，以及旧公开集合与field profile字节不变。正式验收另执行全量Node/Python、validate_all、strict_release_audit、publication integrity和双日期build/verify。

## 官方查阅入口扩展

独立 reference-only v1 见 [官方查阅入口契约](MAJOR_CRITERIA_REFERENCE_CONTRACT.md)。其题录/短主题不改变本v1的22条规范正文、直接关联集合或计数；不可拿短主题替代完整判定条款。
