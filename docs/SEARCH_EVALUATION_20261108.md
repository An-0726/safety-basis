# 现场检索改进与评估交付（2026-11-08）

已实现 CSV / JSONL 问法导入评估，并在包含 **1764 条公开规则、106 个法源版本、1514 条条款、1949 条适用连接** 的正式构建包上复跑。检索继续使用网站原有 `DataStore` 与 `searchHazardsDetailed`；本次没有另建法规索引或扩大条款适用范围。[发布包记录与逐例检查](SEARCH_EVALUATION_20261108.json)

**真实脱敏企业问法 0 条，独立专业人员审核的真实样本 0 条。** 新增 29 条为助手编写的合成边界断言；既有 120 条也为历史合成文本。以下数字是合成回归结果，不能解释为真实现场准确率已通过验收。

## 已修复的问题

1. **压力表检定超期误命中损坏规则。** 非精确标题问法此前可能从损坏条目的排除性说明中命中“检定超期”。现在按标题核对已明确表达的检定或损坏状态；“固定式压力容器压力表检定超期／检定过期”只保留 `H_TSG21_PRESSURE_GAUGE_NOT_VERIFIED`，同时提示核实设备范围、检定有效期及证据。“固定式压力容器压力表损坏”保留损坏规则。精确标题查条目和原有筛选继续可用。
2. **带场所前缀的未配置问法绕过引导。** “车间应急灯没有安装”此前错误偏向疏散指示标志。现在原句不返回直接认定结果，提示核实建筑、部位和应设条件，并给出“应设疏散照明的建筑部位未设置疏散照明”的条件查询入口。未设置、已装但故障及指示标志分别处理。
3. **对象、物料身份与法源缺口得到明确保留。** 防震圈缺失不转换为缺瓶帽或保护罩；未辨识“消防门”不解释为消火栓箱门；普通化学品不自动补成危险化学品；行车和自行车继续隔离。缺少对题依据的气瓶、绝缘器材、普通工业地面等场景保留缺证提示。
4. **资料缺失不推定现场事实。** 检测报告未提供不等于检测从未实施或设施故障；设备检验资料找不到不等于超期且继续使用；培训签到缺签字不等于未培训。条件提示保存应核实的事实。未发现、未确认和已修复的事实状态优先于其他匹配边界。
5. **联调补齐灭火器附近堆物的自然问法。** “灭火器前堆放纸箱”现在显示 `needs_conditions`，给出既有 `H003` 的条目入口，并要求确认是否遮挡识别或实际妨碍取用。纸箱存在本身不会被直接写成已确认隐患。明确查找“灭火器被遮挡、取用受阻”仍返回原条目。

以上边界仅控制候选检索和提示；现场事实、条款适用性与专业结论仍须由工作台审核流程确认。[实现](../web/js/search-boundaries.js) · [回归](../tests/search-boundaries.test.mjs)

## 工具已能实际做什么

`tools/checks/field_query_eval.mjs` 读取 UTF-8 CSV 或 JSONL，保留原问法、匿名来源、人工期望 H/K、禁止 H/K、必要事实及其确认状态、人工判读、地域类别等筛选。CSV 可处理 BOM、逗号、引号和换行。真实与合成、人工与助手标注、已复核与待复核分别记录。

工具加载正式包并校验原有数据完整性，按原句检索，记录直接前三项、条件建议的前三项、对应 H/K/条款/适用条件/来源链接及分类提示。直接命中与条件建议可达分别统计，避免把改写后的命中混算为原句准确率。H 与 K 同时提供时必须落在同一个候选上。不存在于当前公开包的期望或禁止编号会单独报告并令 `--check` 失败；未复核样本不进入评分分母；零分母为 `null`。

评估仅在本机运行，不调用外部模型或上传原句。包含真实记录或不可公开记录的仓库内输出仅允许 `private-intake/`，同时检查符号链接。报告保留原句，因此必须与企业资料一起私有保存。`deidentified=true` 只是导入者声明，工具不声称自动完成脱敏。[完整输入契约与运行说明](SEARCH_EVALUATION.md)

## 本次结果

| 检查 | 结果 | 解释 |
| --- | ---: | --- |
| 新增合成样例 | 29 | 七类安全边界、事实状态、缺证、未知对象及工作台联调问法 |
| 原问法直接 Top3 | 12 / 12 | 只统计标注要求直接候选的样本 |
| 条件建议 Top3 可达 | 7 / 7 | 建议入口后的检索；原问法无直接结果仍如实记录 |
| 分类一致 | 29 / 29 | 与合成断言的分类一致 |
| 条件不足提示 | 14 / 14 | 既分类正确，也实际有提示文案 |
| 缺证提示 | 4 / 4 | 保留无法用相邻条款代替的缺口 |
| 已标注严重误配 Top3 | 0 / 25 | 只涵盖明确标注禁止 H/K 的样本 |
| 建议结果含禁止 H/K | 0 | 单列检查，没有用建议掩盖禁止结果 |
| 缺少禁止目标标注的样本 | 4 | 不视作已验证无误配 |
| CSV 与 JSONL | 逐项完全一致 | 29 条输入经两种解析路径得到相同结果和检查 |
| 真实企业样本 | 0 | 真实指标分母为 0，率为 `null` |

既有 `docs/FUZZY_QUERY_CHECK_20261016.json` 的 **120 / 120** 条在结果数量、直接前三 H、提示有无、建议查询路径上与原报告一致。当前分类为候选 37、条件不足 77、缺证 5、无结果 1。所有历史记录导入为 `pending` / `historical_regression`，原输出仅用于兼容性对照，**没有升级成人工真值**。[回放工具](../tools/checks/field_query_history.mjs)

专项 Node 测试 **140 / 140** 通过，发布资产测试 **1 / 1** 通过。140 包括原有 120 项相关测试及新增 20 项导入、安全边界和历史回放检查。全仓测试和发布结果由统一交付另行记录，本文不声称已部署。[机器可读结果与实现 SHA-256](SEARCH_EVALUATION_20261108.json)

## 正式发布链与工作台接口

新 `web/js/search-boundaries.js` 已同时加入 `build_unified_release.py` 和 `verify_unified_bundle.py` 的 `SITE_ASSETS`，正式包会复制并记录文件校验和。原发布测试已扩展，验证包内模块与源码逐字节一致并被 `checksums.json` 覆盖。本次独立构建再次核实了复制结果。

`searchHazardsDetailed` 保留原字段，并固定返回以下对象。后端桥接可原样增加 `assessment: detailed.assessment`，前端使用 `classification` 和 `requiredFacts` 展示处理状态及待核事实；提示正文仍从 `queryNotice` 读取。

```js
assessment: {
  classification: 'needs_conditions',
  reason: 'extinguisher_access_observation',
  requiredFacts: [
    '灭火器设置点及适用场景',
    '物品是否遮挡识别或妨碍便捷取用',
    '现场照片及实际取用核实'
  ]
}
```

分类枚举为 `candidate_matches`、`needs_conditions`、`evidence_gap`、`fact_unconfirmed`、`no_result`。`requiredFacts` 总是字符串数组；旧引导没有独立结构化事实清单时为空数组，完整要求仍在提示与建议说明中。`candidate_matches` 表示待审候选，不能作为事实或适用性的自动确认。

## 复现

先按仓库统一流程构建 `source/releases/current`，然后执行：

```sh
node --test tests/search*.test.mjs tests/fuzzy-vocabulary.test.mjs tests/field-query-guidance.test.mjs tests/field-query-eval.test.mjs
node tools/checks/field_query_eval.mjs --input tests/fixtures/field-query/synthetic-boundaries.jsonl --bundle source/releases/current --output private-intake/search-evaluation/synthetic-boundaries --check
node tools/checks/field_query_eval.mjs --input tests/fixtures/field-query/synthetic-boundaries.csv --bundle source/releases/current --output private-intake/search-evaluation/synthetic-boundaries-csv --check
node tools/checks/field_query_history.mjs --bundle source/releases/current
PYTHONPATH=tools/pipeline/tests python -m unittest test_field_profile_release.FieldProfileReleaseTests.test_formal_ui_module_is_shipped_and_checksum_covered
```

本次独立验证包的 `dataVersion` 为 `2026.11.08.phase2`，`asOf` 为 2026-11-08；数据 `releaseHash` 为 `e681ca40a794c5dce0aeb751a3e9b93dac9d976cc0266379e31a4ad8cc5c920d`，`sourceRevision` 为 `5482114854f447450e9b5cfbf29436e94bde3e3a02d6b9ba9430dc3dfa608b7a`。JSON 交付记录输入与实现文件 SHA-256，便于区分将来的数据变更和代码变更。

## 真实剩余问题

- 仍没有可用于真实场景验收的匿名企业问法及独立专业标注。工具已能导入这些记录，不能用 29 条合成断言代替实际验收。
- 禁止 H/K 是有界标注，只能验证已枚举的误配；4 条新样例及全部历史待复核样例没有完整禁止目标覆盖，未知误配仍需专业判读。
- 检索沿用现有词汇、画像与规则边界。长句、多问题组合、地方和细分行业条件仍可能无结果或需要补条件，未宣称任意自然语言均能正确分类。
- 防震圈、部分绝缘器材、普通工业地面等专用法源仍有缺口，当前采取缺证提示；没有把通用义务或相邻条款伪装为直接依据。
- 既有部分引导仅在文案中说明事实，结构化 `requiredFacts` 为空；工作台应同时保留完整提示，不能只读数组判断是否需要确认。

## 新增合成问法逐项结果

“direct”与“suggestion”是样例期望路径；“none”表示仅核查分类及禁止结果，不要求候选命中。逐项 H/K、禁止目标、事实清单和检查细节见 JSON 和导入样例。

| ID | 原始问法 | 实际分类 | 直接前三 H | 期望路径 |
| --- | --- | --- | --- | --- |
| SYN-001 | 车间应急灯没有安装 | needs_conditions | 无直接结果 | suggestion |
| SYN-002 | 仓库内应急照明灯未设置 | needs_conditions | 无直接结果 | suggestion |
| SYN-003 | 应急灯坏了 | needs_conditions | H_FIRE_EMERGENCY_LIGHTING_LAMP_FAULT | direct |
| SYN-004 | 已设置的消防应急照明灯具损坏、不能正常点亮 | candidate_matches | H_FIRE_EMERGENCY_LIGHTING_LAMP_FAULT | direct |
| SYN-005 | 固定式压力容器压力表检定超期 | needs_conditions | H_TSG21_PRESSURE_GAUGE_NOT_VERIFIED | direct |
| SYN-006 | 固定式压力容器压力表检定过期 | needs_conditions | H_TSG21_PRESSURE_GAUGE_NOT_VERIFIED | direct |
| SYN-007 | 固定式压力容器压力表损坏 | needs_conditions | H_TSG21_PRESSURE_GAUGE_DAMAGED | direct |
| SYN-008 | 压力表检定超期 | needs_conditions | 无直接结果 | suggestion |
| SYN-009 | 气瓶防震圈丢失 | evidence_gap | 无直接结果 | none |
| SYN-010 | 钢瓶缺少防震胶圈 | evidence_gap | 无直接结果 | none |
| SYN-011 | 气瓶未装配保护罩或瓶帽 | candidate_matches | H_TSG23_CYLINDER_NO_GUARD_OR_CAP | direct |
| SYN-012 | 车间消防门关不上 | needs_conditions | 无直接结果 | suggestion |
| SYN-013 | 消火栓被遮挡、圈占 | candidate_matches | H002 | direct |
| SYN-014 | 人员密集场所、高层和地下公共建筑防火门关闭功能不符合要求 | candidate_matches | H_99C14C8150B1AF834ADC8E5121_3 | direct |
| SYN-015 | 行车吊钩防脱钩装置损坏 | candidate_matches | H_772BE36081184956B7899AA306 | direct |
| SYN-016 | 电动自行车飞线充电 | candidate_matches | H010 | direct |
| SYN-017 | 普通化学品未分类存放 | needs_conditions | 无直接结果 | none |
| SYN-018 | 普通化学品混放 | needs_conditions | 无直接结果 | none |
| SYN-019 | 危险化学品仓库未采用规定的储存方式 | candidate_matches | H_38446A727CFE42F2B4BB5B471C、H_GB15603_5_1_1 | direct |
| SYN-020 | 资料核查：年度消防检测报告缺失 | needs_conditions | 无直接结果 | suggestion |
| SYN-021 | 没有找到设备检验报告 | needs_conditions | 无直接结果 | none |
| SYN-022 | 培训签到表缺签字 | needs_conditions | 无直接结果 | suggestion |
| SYN-023 | 生产经营单位未培训从业人员或未合格即上岗 | candidate_matches | H_6B81819B5BCB43149B0148792F | direct |
| SYN-024 | 现场未发现灭火器损坏 | fact_unconfirmed | 无直接结果 | none |
| SYN-025 | 车间灯具已经修复 | fact_unconfirmed | 无直接结果 | none |
| SYN-026 | 插座坏了 | evidence_gap | 无直接结果 | none |
| SYN-027 | 普通工业车间地面有油 | evidence_gap | 无直接结果 | none |
| SYN-028 | 脱敏样例不存在的设备类型甲乙丙 | no_result | 无直接结果 | none |
| SYN-029 | 灭火器前堆放纸箱 | needs_conditions | 无直接结果 | suggestion |
