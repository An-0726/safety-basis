# 重大隐患标准官方查阅入口 v1

本契约增加独立的题录和短检索主题视图，不改变 `major-criteria-catalog`、`major-criteria-topic` v1 的规范条文/直接关联规则。原目录仍为两部受控标准、22条正文。题录标准数和短主题数单列；不能称三部全文、不能把主题数当已审判定条款数或现场隐患数，也不声明全行业覆盖。

## 内容与界面

- 统一入口：`manifest.files.majorCriteriaReferences` → `data/major-criteria-references.json`
- 根对象：`schemaVersion: safety-major-criteria-references-v1`、`asOf`、`catalogScope: official_reference_entries_only`、`allIndustryCoverage: false`、`wholeNormNotFieldFinding: true`、统一提示和 `referenceEntries`
- 每个入口含 canonical LF/LV、标题、文号、版本、发布机关、实施日、效力、元数据/短主题审核日期、`officialLink`（官方题录页）和 `officialTextLink`（官方原件）
- `searchTopics` 可显式为空，表示只获审题录；不能据空数组推断条款覆盖。非空时每个元素只有条号、短主题、`contentKind: search_topic_only`、`isOfficialQuote: false`、`standaloneDeterminationAllowed: false`
- 条目固定 `contentKind: reference_only`、`textMode: link_only`、`publicationPermission: metadata_only`、`fullTextReviewed: false`、`fullQuotePublicationReady: false`、`reviewedClauseCount: 0`、`directHazardCount: 0`、`wholeStandardComplete: false`、`standaloneDeterminationAllowed: false`
- `publicationReady` 显式分开：`metadata: true`、`searchTopics: true`、`fullText: false`。这里仅指本次契约的内容资格，不代表已部署或完整条件获准再发布
- `checked` 是题录和短主题审核时间，不是完整正文公开审核日期。私有原件曾被人工核对也不能把公开 `fullTextReviewed` 改成 true
- 标题、文号、条号和短主题只在独立参考视图内检索，不合并进 H 搜索、规范 `clauses`、direct topic 或全文倒排词条
- 不输出 `quote`、条件重述、现场判定、整改要求或 H/K。每个短主题限定1—16个中文/字母/数字/空格，不能有换行或标点；该长度门禁不是语义许可，仍须独立审阅精确主题内容及条号映射

第一批入口为 AQ 3067-2026。53个短主题是定位索引；本契约不公开53条正文，不批准完整条件改写，也不新增其任何 C/H/K。不推断2017危化附件废止/替代，不触动同文件烟花爆竹部分。

## 来源与单独审核

正式来源仍为 `knowledge/laws`、`law-versions`、`evidence` 和对应的真实限范围 reviews。metadata-only 不绕过现有 LF/LV Gate、证据、当前效力及真实审核日期，也不需要人为造一个 H 才可显示。

- `knowledge/major-criteria-references/v1/records/REF_*.json`：严格字段的受控主题配置
- 同 namespace 的 `reviews/REF_*.json`：只批准身份/日期/官方链接/短检索主题的独立 review
- review 必须有真实 `checkedAt`、`reviewScope: identity_dates_official_links_short_search_topics_only`、`fullQuotePublicationReady: false`、内容哈希及依赖指纹
- 依赖指纹绑定 LF/LV、本链所有 evidence/review，以及 `source/publication/law-index.json` 精确行、`fulltext/catalog.json` link_only 题录、`fulltext/search-index.json` 精确题录行
- `review_bindings` 仅算绑定值，不能写 review、不能批准内容、不能自动刷新恢复资格。内容变化必须重新审阅
- 只提供 draft 的报告不等于 `verified`。缺审、拒审、陈旧绑定、未来审核、过期或未实施版本均不显示

独立标准题录不加入原“隐患所引法规”索引。原普通法规索引仍由有效 H/K/C 的实际引用生成；新独立官方查阅视图与资料库题录解决无 H 的可见性。

## 防止旧资料库旁路泄漏

受控 reference 的 `source/publication` 题录必须为严格 link_only：`textPath: null`、`fullTextSha256: ""`、`fullTextReviewed: false`、`publicationPermission: metadata_only`。附加 quote/未知字段、full_text、私有路径或不匹配的检索题录直接阻断构建。

新的受控标准没有达到该构建日期的审核资格时，同时从公开 fulltext catalog 和其 search-index 的 documents 中过滤；不能只隐藏新卡片，却通过旧资料库 copy 提前显示。已有其他全文、题录、文本与 grams 保持原内容。新受控 namespace 存在时，公开两个题录文件 `asOf` 采用构建日期，来源文件的 `asOf` 保留本次来源更新日期。

AQ本轮真实审核发生于2026-10-01，故2026-09-30包此入口/主题为0，2026-10-01包为1/53。这与法律实施日期2026-09-30是两条不同门禁，不能倒填审核日期。

## 完整性与验证

`release_snapshot` 包含完整 reference namespace；统一 build、manifest、site-manifest、checksums、releaseHash 和 verifier 都显式接入。计数使用 `majorCriteriaReferenceStandards`、`majorCriteriaSearchTopics`，不修改规范条文的原计数字段。verifier 重新从稳定 knowledge 与 publication 元数据计算精确投影，重算外层哈希也不能加入假条款/完整条件或改变范围。

`check_major_criteria_references.py` 是 validate_all 阻断步骤，只做结构/来源检查，不自动签审。未签 review 的候选仍不能公开。合成单测覆盖无H/K/C题录、真实日期、缺审/陈旧绑定、未知标准不自动发现、重复条号、超长/全文替身、私有字段、版权状态、历史资料库过滤、快照绑定及重封装篡改。

本地生成和代码测试通过不代表真实浏览器动态验收或远端部署。发布必须另按用户授权执行。

## 通用官方文件题录

非技术标准文号、现行使用中及未知实施日期由独立[官方文件题录目录](MAJOR_CRITERIA_DIRECTORY_CONTRACT.md)处理，不放宽本AQ/短主题契约。各自独立计数与文件，且都不能替代完整判据。
