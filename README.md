# 隐患依据速查库

面向工贸企业安全检查与评价报告的法规、标准、条款和隐患关联库。国家层面为主，江苏、南京地方依据为补充。

在线站点：<https://an-0726.github.io/safety-basis/>

**当前上线版本、已核数量、剩余工作和完整8步计划统一见 [PROJECT_STATE](docs/PROJECT_STATE.md)。** 本页说明怎么使用与长期数据边界，不另维护第二份“当前状态”。接手维护先读 [AGENTS](AGENTS.md) 和 [HANDOFF](docs/HANDOFF.md)。

## 一、怎么使用

1. **隐患速查**：输入设备、现场问题或法规名称；多个关键词用空格分开。先看专业分类、地区，必要时再用“更多筛选”中的场所、依据类型和适用方式。没有结果时先清除过窄条件，不把“未检索到”理解为不存在义务
2. **隐患详情**：先核对对象、场所和适用条件，再读具体条款、逐条关联范围与官方来源。描述和整改建议是核查参考，不是对任何现场事实的自动确认
3. **核查用途与场景**：当前源码在“更多筛选”中提供可选核查用途，详情可展开“条件 / 场景适用性”；上线进度见PROJECT_STATE。默认仍包含全部正式条目，未归类不等于不适用。选择场景只显示对应条件、误判边界、最小取证和整改方向；资料核查、法规义务不能被当成现场可直接认定的隐患。无模板场景不提供描述模板，有模板的也保持未填占位。详见[交互契约](docs/FIELD_PROFILE_UI_CONTRACT.md)
4. **法规库**：按实际被正式条款引用的版本查阅；同名或不同来源不一定是不同法规。使用前核对标准号/文号、版次、实施与终止日期
5. **重大隐患判定**：独立查看受控规范条文、直接关联隐患、行业题录和官方原文查阅。条数、列项数、文件数和隐患数分别计数；不能把一条关键词命中、一个入口或未核日期的阅读文件当作重大隐患结论
6. **法规全文**：区分获准公开的全文与仅提供官方入口的资料。只有题录/官方链接，不表示本站已核全文、允许复制全文或认可其当前适用性

页面中的复制与分享便于追溯，不代替核实现场条件。场景选择不保存到URL或浏览器持久存储，不接收企业事实或上传资料。多次使用同一配置仍需重新收集本次现场证据。

## 二、数据边界

- **正式站**只发布指定 `asOf` 日期下通过完整审核链Gate的记录。`lifecycle=active` 只是源状态，单独不能证明可发布；`proposed` 候选不进入正式公共包
- **日期快照**不是实时法律状态。未来版本、历史版本、未知施行日期和已过期记录须按各自规则处理；发布后法律变化不会自动成为本包的新结论
- **场景审核**确认通用用途、条件和取证边界，不证明企业事实成立。`routing_only` 不生成隐患描述模板，排除默认现场用途不等于删除原条目或否定法规义务
- **独立原文查阅**与当前判定依据分开。非煤补充、民爆和烟花文件的明确施行日未核准时，即使正文可读，也不进入本站当前隐患依据体系
- **公开权利**与官方来源分开。消防GB/AQ全文再发布权利尚未核准，仅提供各自已获准的题录、短主题或官方入口；不能由其他行政正文的公开依据推定技术标准可全文复制
- **未完资料**逐项区分无法恢复的旧冻结包、仍待证的通用定义、现场事实与试点验收。历史行级资料和24候选实体已经恢复，恢复文件不等于现场批准。详情见PROJECT_STATE；已读取、标记hold、工程测试通过均不等于实质审核完成

结果是查证辅助，不承诺全行业、全部项目原件或全部现场问题已覆盖。使用者须结合最新官方文件、实际对象与完整前提作判断。

## 三、唯一正式架构

```text
本地私有原件 / 官方网页与PDF
              ↓
         knowledge/
  身份 → 版本 → 条款 → 隐患/关联 → 审核
              ↓
     指定日期的完整证据链Gate
              ↓
  tools/v4/build_unified_release.py
              ↓
    source/releases/current/（生成物）
              ↓
      GitHub Pages / 本地静态版
```

| 层级 | 位置 | 职责 |
|---|---|---|
| 正式知识源 | `knowledge/` | 法规身份、版本、条款、隐患、关联、审核及独立场景配置 |
| 公开来源层 | `source/publication/` | 题录、官方入口和获准公开的全文，不创建第二套正式法规身份 |
| 私有证据库 | `source/library/` | 本地原件、archive、incoming、SQLite、OCR；Git忽略 |
| 网站源码 | `web/` | 正式搜索、详情、法规与专题界面 |
| 生成发布包 | `source/releases/current/` | 从源与规则重建，不提交、不手改、不反向当母库 |

`knowledge/` 是唯一正式结构化知识源，`main` 是唯一自动部署主线。SQLite只承担检索定位，不高于官方或原始证据。本地证据优先，但缺失时继续查权威官方来源；无须先写SQLite或把原件导入私有库才能建立合格证据链。

## 四、法规身份、日期和引用规则

- 同一法规、同一真实版本、多个来源：一个canonical版本保留多来源；不同真实版本分别保留，并记录生效、替代和废止关系
- `LF_* / LV_* / C_* / H_*` 等稳定ID不因展示或整理而重编号，不按标题相似度删除实体
- 正式引用须同时具备法规身份、适用版本、精确条款、完整逐字原文、官方URL或可追溯原件、适用性及仍绑定当前内容的审核
- AI、OCR、搜索摘要、Excel要点和第三方转载只能辅助定位，不能替代正式原文；指纹更新不能代替实质复核
- 普通条文的表格保留完整行列、条件和例外，窄屏可横向滚动，复制包含完整内容。普通详情每条 `basisRefs` 保留精确关联K的适用范围与地域；多依据不能互串条件，整条规范或原H条件不能代替逐K边界。详见[法源范围契约](docs/BASIS_SCOPE_CONTRACT.md)

CI/正式发布以 `Asia/Shanghai` 取得中国标准时间的 `asOf` 日历日期。当前依据须满足：`validityStatus=active`、`effectiveDate <= asOf`、`endDate` 为空或 `asOf < endDate`，并通过完整审核链。`upcoming` 不能提前支撑当前正式隐患；最新发布不等于当前适用。

重大判定条款允许不创建H/K即可显示，但必须满足受控选择、内容pin、逐条审核和公开范围审核。目录、专题、题录、原文查阅各自有契约，不能通过添加入口来扩大正式依据：

- [规范目录与专题](docs/MAJOR_CRITERIA_CONTRACT.md)
- [官方查阅入口](docs/MAJOR_CRITERIA_REFERENCE_CONTRACT.md)
- [行业题录](docs/MAJOR_CRITERIA_DIRECTORY_CONTRACT.md)
- [独立原文查阅](docs/MAJOR_CRITERIA_READING_CONTRACT.md)
- [场景数据治理](docs/FIELD_PROFILE_CONTRACT.md)

## 五、维护与验证

开始前检查工作区并保留已有修改。更改知识源需明确证据、审核范围和受影响关联；不通过删条目、放宽Gate或自动重签审核来“凑绿”。只改文档时核内容、相对链接和diff；涉及代码/数据时执行受影响测试及完整发布检查。

在仓库根目录运行（Python依赖见 `tools/pipeline/requirements.txt`；CI使用Python 3.12、Node 22）：

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tools/pipeline/tests -v
python tools/v4/validate_all.py
python tools/v4/strict_release_audit.py
python tools/v4/validate_publication_integrity.py
python tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
python tools/v4/verify_unified_bundle.py --bundle source/releases/current
node tools/v4/check_field_profile_ui.mjs source/releases/current
```

把 `YYYY-MM-DD` 换为要验证的中国标准时间日期；Windows可用 `py -3` 代替 `python`。涉及版本切换还须验证边界日期。场景UI检查是数据/控制器验证，不代替真实浏览器验收。

`validate_publication_integrity.py` 校验canonical身份投影、全文目录、物理文本与搜索分片的确定性一致性及公开/私有边界。strict blocker或publication完整性失败必须阻断发布。

本地私有版另运行 `python tools/build_local_release.py`：先重建并验证公开包，再只读组合已存在的私有SQLite，生成 `dist/local/`；本命令不授权获取、修改或同步任何用户私有资料。

发布完成必须对照精确提交、CI、部署产物及线上验收；本地构建成功不能写成已上线。操作顺序见 [HANDOFF](docs/HANDOFF.md)，长期流程见 [MAINTENANCE](docs/MAINTENANCE.md)。

## 六、文档与历史

- [PROJECT_STATE](docs/PROJECT_STATE.md)：唯一当前基线、8步计划和资料保留项
- [HANDOFF](docs/HANDOFF.md)：继续执行所需的少数步骤
- [ARCHITECTURE](docs/ARCHITECTURE.md)：架构；[LEGAL_STATUS_POLICY](docs/LEGAL_STATUS_POLICY.md)：效力与版本
- [CANDIDATE_REVIEW](docs/CANDIDATE_REVIEW.md)：候选审核；[source说明](source/README.md)：来源与生成物
- [历史阶段归档](docs/history/PROJECT_STATE_THROUGH_20261001.md)：旧阶段的原记录及明确更正；更早完整变更可在Git历史追溯

历史日期报告中的“完成”“待审”“已部署”仅属于所记批次，不能被复制成当前全库状态。知识库存、公开投影、原始行、细分项、规范条文和场景配置分别计数。

## 七、隐私与许可证

GitHub和GitHub Pages是公开空间。企业原件、照片、联系人、签字、私有映射、真实本机路径、SQLite、OCR、私有审计/交接材料和未获再发布权利的全文不得进入公开仓库或发布包。

代码采用 [MIT License](LICENSE)；这不为第三方法规标准原件或其他资料授予额外复制权利。
