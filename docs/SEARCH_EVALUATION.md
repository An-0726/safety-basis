# 现场检索评估工具

本工具直接调用正式网站的 `DataStore`、`searchHazardsDetailed` 及同一正式数据包，在本机导入 UTF-8 CSV 或 JSONL 问法。保存原始问法、判读、必要事实、筛选条件、期望与禁止 H/K、候选条款和来源链接。它用于发现检索错误及复核边界；匹配结果不会自动确认现场隐患。

截至 2026-11-08，仓库提供 29 条新增合成边界样例，并复用既有 120 条合成问法。**真实脱敏企业问法为 0，经专业人工复核的真实样本为 0**。合成测试通过不能解释为真实现场准确率已验证。

本次可复现结果见 [2026-11-08 评估交付](SEARCH_EVALUATION_20261108.md) 及 [机器可读结果](SEARCH_EVALUATION_20261108.json)。

## 运行

要求 Node.js 22 或更高版本，以及按仓库构建流程生成的正式发布包。工具通过仅绑定 `127.0.0.1` 的临时只读服务交给原有 `DataStore` 加载，仍校验包内文件哈希及现场检索画像。没有云端上传、外部模型调用或后台遥测。

```sh
# JSONL 脱敏合成样例；--check 失败会返回非零退出码
node tools/checks/field_query_eval.mjs \
  --input tests/fixtures/field-query/synthetic-boundaries.jsonl \
  --bundle source/releases/current \
  --output private-intake/search-evaluation/synthetic-boundaries \
  --check

# 同一批样例的 UTF-8 CSV 版本
node tools/checks/field_query_eval.mjs \
  --input tests/fixtures/field-query/synthetic-boundaries.csv \
  --bundle source/releases/current \
  --output private-intake/search-evaluation/synthetic-boundaries-csv \
  --check

# 导入自己已脱敏且完成判读的现场问法
node tools/checks/field_query_eval.mjs \
  --input private-intake/field-questions.jsonl \
  --bundle source/releases/current \
  --output private-intake/search-evaluation/field-questions

# 回放已存在的 120 条合成问法；旧输出只作兼容性对照
node tools/checks/field_query_history.mjs --bundle source/releases/current
```

每次评估输出 `report.json` 与 `report.md`。JSON 包含完整原始数据、逐项检查、各分组指标、输入 SHA-256、发布包 manifest 和实际公开条数；Markdown 提供可读结果。标准输出只显示统计及文件位置，不打印原句。`--check` 的退出码：0 表示已复核断言全部满足；1 表示断言失败、编号缺失或只有待复核样本；2 表示输入、包完整性或运行错误。无 `--check` 时可正常生成失败样本报告。

`field_query_history.mjs` 额外输出 `import-pending.jsonl` 与 `comparison.json`。导入记录使用 `historical_regression` / `pending`，不会把旧搜索答案当成人工真值；兼容性比较包含原结果数量、直接前三 H、提示有无、建议查询路径及已撤出的历史编号。比较结果变化应逐条解释，不能简单把旧答案恢复回去。

## 输入格式

JSONL 每行一个对象；CSV 首行为相同英文列名。CSV 支持 UTF-8 BOM、CRLF、双引号转义及带逗号或换行的原始问法。数组和对象列填写 JSON；表格软件需使用 UTF-8 CSV 导出。保留原始问法文本，不先改成标准标题来提高命中率。上限为 10,000 条、16 MiB。

| 字段 | 类型 / 取值 | 用途 |
| --- | --- | --- |
| `id` | 唯一匿名字符串，如 `CASE-001` | 不使用企业名称、员工姓名或电话 |
| `query` | 非空原始问法，最长 4,000 字符 | 空格、标点及换行原样留存；搜索内部正常归一化 |
| `source_kind` | `synthetic` / `real_deidentified` | 真实与合成分开统计 |
| `source_reference` | 可选匿名来源代号 | 可回查本机私有记录，不放企业地址或照片路径 |
| `captured_at` | 可选时间字符串 | 记录采集日期或时间 |
| `deidentified` | 布尔值 | 真实数据必须显式为 `true`；这是导入者声明，不是自动脱敏证明 |
| `publishable` | 布尔值，默认 `false` | 只有明确可公开的合成样例才放入仓库；真实数据始终受私有输出限制 |
| `annotation_origin` | `human` / `assistant_synthetic` / `historical_regression` | 区分人工判读、助手合成断言及历史回放 |
| `review_status` | `pending` / `reviewed` | 待复核样本可以导入，但不进入评分分母 |
| `expert_label` | 见下一表 | 保存判读类别，与搜索实际分类并列 |
| `expert_judgment` | 判读说明 | 已复核必须非空；写明依据、成立条件和不能推定的事实 |
| `expected_outcome` | 可选，见搜索分类表 | 用于分类、条件不足及缺证提示评估 |
| `expected_target_route` | `direct` / `suggestion` / `either` / `none` | 规定直接命中或经条件建议到达；默认随是否有期望编号确定 |
| `expected_hazard_ids` | H 编号数组 | 可接受候选的替代集合 |
| `expected_basis_ids` | K 编号数组 | 可接受适用性连接的替代集合 |
| `forbidden_hazard_ids` | H 编号数组 | 明确属于高风险误配的结果；未标注不能视为安全 |
| `forbidden_basis_ids` | K 编号数组 | 不应被返回的法源连接 |
| `forbidden_match_kind` | 可选四类误配标签 | `object_mismatch` / `state_mismatch` / `scope_mismatch` / `document_fact_mismatch` |
| `required_facts` | 对象数组 | 每项 `{ "fact": "事实", "status": "unconfirmed", "evidence": "可选匿名证据说明" }` |
| `filters` | 对象，默认 `{}` | 原网站支持的地域、类别、场所等筛选；建议点击也使用同一筛选 |
| `group` | 可选字符串 | 分组评估，如 `pressure-gauge` |

`required_facts[].status` 支持 `confirmed`、`unconfirmed`、`not_applicable`。工具只保存导入值，不自行补事实或自动变更状态。已复核记录至少应提供一项期望分类、期望目标或禁止目标，否则拒绝导入。

| `expert_label` | 含义 |
| --- | --- |
| `direct_correct` | 原问法可直接检索到预期候选；不代表隐患已确认 |
| `needs_conditions` | 缺少设备、场所、义务、期限等成立条件 |
| `evidence_gap` | 缺少对题且可靠的法源链 |
| `object_mismatch` | 错把消防门当成消火栓门等对象混淆 |
| `state_mismatch` | 错把超期当损坏、未装当故障等状态混淆 |
| `scope_mismatch` | 扩大行业、地域、物料或适用范围 |
| `document_fact_mismatch` | 由未提供资料推定现场故障或未实施行为 |
| `fact_unconfirmed` | 未发现、未核实或已修复等事实状态不能删去 |
| `no_result` | 预期没有合适直接结果 |
| `unreviewed` | 尚未判读，只允许与 `pending` 配合 |

`filters` 仅接受既有键：`region`、`category`、`displayCategory`、`place`、`scene`、`sceneTag`、`level`、`displayLevel`、`mode`、`status`、`browse`、`inspectionClass`，值为字符串。未知字段、重复 ID、坏引号、不合法 JSON、同时期望和禁止同一编号均报错。

以下是**合成格式示例**；复制到真实记录前应填写实际的匿名问法、事实和专业判读，不能沿用样例结论：

```json
{"id":"SYN-FORMAT-001","query":"现场未发现灭火器损坏","source_kind":"synthetic","annotation_origin":"assistant_synthetic","deidentified":true,"publishable":true,"review_status":"reviewed","expert_label":"fact_unconfirmed","expert_judgment":"合成边界断言：未发现损坏不能反转为已经损坏。","expected_outcome":"fact_unconfirmed","expected_target_route":"none","expected_hazard_ids":[],"expected_basis_ids":[],"forbidden_hazard_ids":[],"forbidden_basis_ids":[],"required_facts":[{"fact":"实际当前状态","status":"unconfirmed"}],"filters":{},"group":"fact-state"}
```

## 指标如何计算

所有率都带分子、分母及 `rate`；分母为 0 时为 `null`。真实、合成及“真实且人工复核”分别输出。报告中的全部样本栏允许包含合成断言，不能替代真实栏。

| 指标 | 分母与判定 |
| --- | --- |
| 原问法直接 Top3 | 已复核、标签存在、有期望 H/K 且路径为 `direct` 的样本；前 3 个直接结果至少 1 项符合期望 |
| 条件建议 Top3 可达 | 同上但路径为 `suggestion`；至少一条建议查询的前 3 个结果符合期望；原问法未命中仍如实保留 |
| 任一路径 Top3 | 路径为 `either`，直接或建议至少一条成立；独立列出，不混入直接命中率 |
| 分类一致 | 有 `expected_outcome` 的可评分样本；实际 `assessment.classification` 一致 |
| 条件不足提示 | 期望 `needs_conditions` 的样本；分类一致并实际存在提示文案 |
| 缺证提示 | 期望 `evidence_gap` 的样本；分类一致并实际存在提示文案 |
| 严重误配 Top3 | 有有效禁止 H/K 标注的已复核样本；直接前三出现任一禁止目标即计入分子 |
| 建议禁止结果 | 单独统计建议前三包含禁止 H/K 的样本，不用建议掩盖错误 |

同时提供 H 与 K 时必须在**同一个候选**上满足，不能用候选 A 的 H 加候选 B 的 K 凑成命中。编号数组表达替代目标集合；需要多条都应找到时应拆成多个独立断言。期望或禁止编号不存在于当前正式发布包时单独列出、排除评分并令 `--check` 失败，不默默删除标注或记为成功。

没有禁止 H/K 标注的样本计入 `unreviewed_mismatch_risk_samples`。这包括标注覆盖不足，不代表已知发生误配。“0 严重误配”只适用于已明确枚举的禁止结果，不能代表全库没有未知误配。

## 与工作台共用的接口

不需要另建搜索词库、法规索引或法律推断服务。现有 `DataStore` 初始化及 `searchHazardsDetailed` 返回值可以直接供 Node 桥接使用：

```js
const store = await new DataStore(bundleBaseHttpUrl).init();
const result = searchHazardsDetailed(store.searchIndex, originalQuery, filters);
const detail = await store.getHazardDetail(result.rows[0]);
```

原有 `rows`、`matchKind`、`interpretedQuery`、`queryNotice`、`suggestions` 保留；增加：

```js
assessment: {
  classification: 'needs_conditions',
  reason: 'gauge_verification_state',
  requiredFacts: ['是否属于固定式压力容器及条款适用范围', '检定有效期及证据']
}
```

| 实际分类 | 工作台应表达的含义 |
| --- | --- |
| `candidate_matches` | 找到待审核候选；用户仍须核实事实及适用性 |
| `needs_conditions` | 保留提示及必要事实，条件未补齐不能直接定性 |
| `evidence_gap` | 当前知识库没有足够对题来源；保留原观察，待补证 |
| `fact_unconfirmed` | 原句为未发现、未核实、已修复等状态；不反转成确定缺陷 |
| `no_result` | 当前检索没有合适结果；不等于现场没有问题 |

`reason` 是稳定原因代号；`requiredFacts` 为字符串数组。旧有引导分支未单独结构化事实清单时数组为空，完整条件仍在 `queryNotice` 和建议说明中。引导会抑制危险直接匹配，但精确标题仍是定向条目查找，不能据此省略专业复核。

## 数据与隐私

真实现场问法先在企业受控环境脱敏，再放入 `private-intake/` 或仓库外的私有目录。不要使用 `tests/fixtures/` 或 `docs/` 存真实记录。只要包含真实记录或 `publishable=false`，输出到仓库内时仅允许 `private-intake/`，并检查已有目录的符号链接，拒绝借符号链接写入公开目录。默认目录权限 0700、新建报告文件 0600；部署时还应使用实际操作系统权限保护目录。

工具不会自动移除人名、企业名称、地址等信息。`deidentified=true` 是导入者声明，需要人工检查。报告 JSON 会保留原句及判读，因此报告本身同样是私有资料。不要将真实报告、企业照片、私有 PDF、SQLite 或凭据提交到公开仓库。公开 fixture 只有可复现的合成文本和已公开法规 ID。

## 验证与限制

```sh
node --test tests/search*.test.mjs tests/fuzzy-vocabulary.test.mjs \
  tests/field-query-guidance.test.mjs tests/field-query-eval.test.mjs
```

重点回归包括未配置/损坏、检定超期/故障、防震圈/瓶帽、消防门/消火栓、行车/自行车、普通化学品/危化品、资料核查/现场隐患。导入器另测 CSV 引号和换行、原句保存、H/K 同候选匹配、真实零样本、待复核排除、失效标签、筛选不绕过及私有输出限制。

检索仍是既有规则与词汇体系，不声称覆盖任意长句、多问题组合或所有企业行业。后续实际改进应由真实匿名问法、专业标注和官方来源驱动。专用法源缺口继续保留缺证提示，不用相邻法规或泛化义务凑结果。
