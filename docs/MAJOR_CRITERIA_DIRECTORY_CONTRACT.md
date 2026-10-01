# 官方重大隐患文件题录目录 v1

## 与已有内容的关系

2026-10-01后续燃气正文批次可以在独立规范目录中提供同一LV的11条已审正文。此题录payload及9份metadata审核不因此改成全文审核；前端核对精确版本身份后提供导航，不把题录计数重复计入正文数。详见[完整行政正文扩展](MAJOR_CRITERIA_CONTRACT.md#2026-10-01-完整行政正文扩展)。以下首批记录仍描述原metadata批次的范围。

新增 `manifest.files.majorCriteriaDirectory` 指向 `data/major-criteria-directory.json`。保留原规范目录、direct专题和AQ参考入口三个契约：两部已审规范仍为22整条，AQ仍只有53个短定位主题。新目录不增加任何C/H/K或完整条件，不把题录文件计入已审条款或关联隐患数。

首批来源为消防、房屋市政施工、城镇燃气、电力、煤矿、金属非金属矿山、民爆、烟花爆竹8个目录主题，实际为9份文件。非煤基础与2024补充必须同组呈现。目录主题并非互斥行业，消防和燃气保留各自法定重大隐患名称；`allIndustryCoverage` 始终为false。

原 `major-criteria-references/v1` 的AQ源记录、review、53主题及公开投影保持不变。技术标准、部门规章、规范性文件在新目录均使用 `documentNumber`，不强塞技术标准号格式。

## 受控源与独立审核

- 新源命名空间：`knowledge/major-criteria-directory/v1/records` 与同层 `reviews`
- 记录只含canonical版本、官方入口、目录组、主/补充关系、法性质、判定文件类型、短主体范围提示、适用边界提示、现行性核验基准日与未知实施日说明
- reviewer只批准 `identity_dates_currentness_scope_official_links_only`，`fullQuotePublicationReady:false`
- 精确绑定记录、LF/LV、全部所引E及其原reviews、source/publication的law-index行和两份fulltext题录行
- 非煤主/补充还相互绑定对方record及其LF/LV/E/source链。不会互相哈希对方directory review，以免形成循环。任何成员缺审、未来审、陈旧、无效或关系不完整，整组退出公开投影
- `review_bindings` 只计算指纹，不写review，也不是语义审核。新增配置、哈希自洽或文章标题相似均不自动取得发布资格

范围提示仅说明文件适用主体/文献关系，不替代完整判定条件，不输出阈值条件表、quote、现场结论或整改建议。

## 元数据日期与当前依据Gate分开

本目录是查阅入口，不能作为现场判定依据。原 `release_gate_core` 未修改。元数据准入仍要求LF/LV真实审核、内容匹配、官方证据、日期与独立目录review，但不把“允许显示题录”当成 `supports_current`。

- `referenceStatus: current` → 现行有效；必须有明确且已到的有效实施日
- `referenceStatus: current_in_use` → 现行使用中；可以有已知实施日，或在充分核验且说明原因后保留null
- `effectiveDate:null` 只在current_in_use且 `effectiveDateNote` 明确时准入。不用成文日、转载日、网页上传日或模型猜测填补
- 三个null版本为民爆2024、非煤2024补充、烟花2017部分。原规范Gate仍拒绝其当前C/H资格；题录显示不会修复此缺口
- 过期、未来实施、proposed、upcoming、无真实审核、未来审核或无效日期不能进入本目录
- `checked` 是此次元数据审核日期；`statusAsOf` 是现行性核验基准日，都不表示原文条款已经审准

source/publication保留null与准确状态。“现行使用中”的显示例外只由此namespace的精确审核绑定产生，不能任意新增status来改变全局映射。日期校验仅把null和空字符串视为未知日期的两种元数据表示，并继续拒绝布尔值/数字；不会给共享依据Gate增加空日期例外。

## 公开结构

严格schema：`tools/v4/schemas/major-criteria-directory.schema.json`，顶层 `schemaVersion:safety-major-criteria-directory-v1`。

顶层含asOf、目录边界提示、`directoryGroupCount`、`documentCount`、`directoryGroups`、`entries`。组含id/label/primaryReferenceId/documentIds，文件含精确 `directoryGroup`、requiredCompanionIds、supplementsReferenceId。计数组和文件时分开，匹配补充文件的搜索也应保持完整组。

每个文件固定：

- `contentKind:official_document_reference_only`
- `textMode:link_only`、`publicationPermission:metadata_only`
- `publicationReady:{metadata:true,fullText:false}`
- `fullTextReviewed:false`、`fullQuotePublicationReady:false`
- `reviewedClauseCount:0`、`directHazardCount:0`、`searchTopicCount:0`
- `standaloneDeterminationAllowed:false`、`wholeStandardComplete:false`

没有quote、clauses、topics或H/K数组。它可被看见和查阅，不能被冒称完整判据。新计数仅为 `majorCriteriaDirectoryGroups` / `majorCriteriaDirectoryDocuments`，不更改旧规范/AQ/隐患计数。

## 资料库与完整性

两个fulltext题录文件也按受控目录的真实审核日期投影，防止新目录已隐藏而旧资料库副本提前公开。9文件真实目录审核均在2026-10-01；故9/30为0组0文件，10/1为8组9文件。原非受控文档、全文文本和grams保持原值。

新namespace纳入稳定源快照；新公开文件纳入manifest、site-manifest、checksums、releaseHash和精确重算verifier。非法全文模式、额外quote字段、私有路径或题录漂移阻断构建。重新计算外层哈希也不能升级为判定依据、伪填日期或篡改主补充关系。

新增structural check纳入validate_all。源fixture精确绑定本批79个新knowledge文件；旧库存测试只扣除本批明确9LF/9LV/25E后，继续检查原库存哈希，未通过广泛放松断言取得绿灯。

本地模型、模拟DOM、schema和构建验证不等于真实浏览器动态/视觉验收，也不授予远端上传或部署许可。
