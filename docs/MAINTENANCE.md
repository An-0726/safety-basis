# 日常维护

本项目只维护一条当前主线。历史从 Git 恢复，不从旧 Excel、旧发布包或网页生成物反向覆盖 `knowledge/`。

## 法规或标准入库

1. 先确认法规/标准身份、编号、版次、发布/实施日期和当前效力，再决定证据获取路线；
2. **优先复用本地私有母库，但不以本地母库为唯一来源。** 本地有已核验原件时直接使用；本地没有、版本不全、原文缺失或效力存疑时，必须主动联网查询权威官方来源；
3. 官方来源优先使用全国人大/国家法律法规数据库、中国政府网/国务院、发布机关及主管部门官网、国家标准全文公开系统/全国标准信息公共服务平台、对应省市政府或主管部门官网。普通搜索摘要、百科、培训网站、商业法规库和第三方转载仅用于定位；
4. 官方网页/PDF若能确认现行版本、精确条/款/项或标准条号、完整逐字原文、官方 URL/证据和适用范围，可直接建立 `knowledge/` 中的法规身份、版本、条款、evidence、隐患关联和 review，**不要求先把原件导入 `source/library/` 或先写 `fulltext.sqlite3`**；
5. 只有需要离线保存、全文检索或补充本地证据库时，才按单独授权流程将原件复制到 `source/library/incoming-YYYYMMDD/`，做 SHA-256 去重、题录匹配、文本/OCR 和 SQLite 维护；SQLite 仍只用于检索定位，不高于官方/原始证据；
6. 允许公开的题录、官方入口或全文才同步到 `source/publication/`；同一真实版本的多个官方来源只作为多来源，不制造多个正式法规身份；
7. 运行完整 Gate、构建和校验；涉及架构/口径/归并/候选策略时同步更新 README；交接方式实际变化时再更新 HANDOFF。

## 长期维护触发条件

当前项目已完成全量 proposed 候选逐条核销闭环与最终验收，正式进入长期维护模式（Long-Term Maintenance Mode），业务范围全面冻结。仅当出现下列任一情况时方可开启新的维护批次：

- 新法规、标准、修订版本、废止/替代关系或官方证据需要纳管；
- 既有法规到达生效日期（如 upcoming 转为 active）或废止日期；
- Validate / strict gate / publication integrity / fresh build / verify / Pages 出现异常；
- `PROJECT_STATE.md`、README、HANDOFF 与远端实际状态出现实质冲突；
- 私有 SQLite 到达计划备份/integrity 维护点，或出现文档数、FTS 行数、paragraph sum、archive 引用等不变量异常。

在没有上述触发条件时，严格保持冻结状态，不为“保持活跃”而修改业务数据，不扩增业务范围，也不把经过审慎保留的 184 条 proposed（主要为 upcoming 149 条及需官方依据/适用边界补充项）强行清零。

## 候选

候选规则只认 `docs/CANDIDATE_REVIEW.md`。`proposed` 可留在 knowledge 继续审核，但**不得进入正式发布包**。全库 426 条 proposed backlog 已经完成逐条审查与处置闭环，其中 242 条转正 active，184 条分类保留（含 149 条 upcoming 等）。

## 数量口径

- 法规身份数：`knowledge/laws/`；
- 法规版本库存数：`knowledge/law-versions/`；
- 正式法规页数：当前正式条款实际引用并通过 Gate 的法规版本；
- publication 数：公开来源/题录项目，不是正式法规身份数；
- knowledge 隐患数：含 active / proposed / superseded 等全部实体；
- 正式隐患数：当前日期链式 Gate 通过的已核验隐患；
- 私有全文数：SQLite 中成功建立正文记录的文档；
- 公开全文数：`source/publication/fulltext/` 中允许公开分发的全文。

当前 2026-09-19 正式基线：1,744 条正式隐患、60 个实际引用法规版本、1,354 条正式条款、1,863 个正式关联；184 条 proposed 只留后台，公开 proposed=0。knowledge 库存为 104 laws / 107 lawVersions / 3,007 clauses / 2,015 hazards / 1,886 links / 1,197 evidence；publication 为 69 个 canonical 来源关系（11 full_text + 58 link_only）。

## Publication 长期完整性门禁

`source/publication/` 是公开来源层，但它仍必须严格服从 `knowledge/` 的 canonical 身份。日常 CI 通过 `tools/v4/validate_publication_integrity.py` 持续检查：

- `law-index.json` 必须与 `knowledge/law-versions/` 保持 1:1 canonical version ID 投影；
- 全文 catalog 的 `versionId/lawId`、效力日期、公开权限与 knowledge/目录规则一致；
- `full_text` 必须有已批准全文、合法 `texts/` 路径和真实文件；`link_only` 不得携带全文文件或全文 hash；
- catalog 引用的全文文件集合必须与物理 `texts/*.json` 双向完全一致，禁止孤儿全文被复制到公网包；
- `search-index.json` 与 `grams/*.json` 必须能由当前 catalog/全文确定性重算得到，禁止陈旧搜索派生物继续部署；
- publication 元数据不得带入 `proposed` 隐患或私有库路径/SQLite 标记。

该门禁只读，不修改 `knowledge/`、publication、SQLite 或 archive；任何失败都必须先调查真实不一致，不能通过修改业务数据“凑通过”。Validate 与实际 Pages Build 两条长期 workflow 都必须执行此门禁。

## 站内检索词库维护

`web/js/search-vocabulary.js` 是公开站隐患与法规检索的词库。`EQUIVALENT_GROUPS` 只放可以互查的名称、简称和口语写法；`RELATED_GROUPS` 放相近但不等同的设备或概念，仅在原词及同义词均无结果时回退；`SEGMENT_TERMS` 用于拆解没有空格的中文组合查询。新增词先用库内标题、别名或实际失败查询确认用途，并为召回和不应命中的结果补充 `tests/search.test.mjs` 用例。不得把相反状态、不同法规身份或不同技术要求合并成同义词。

词库只影响查找，不创建隐患、法规、条款或正式关联；没有已核验条目的词可能仍显示零结果。新增前端模块时，同步维护发布包的 `SITE_ASSETS` 清单与 `web/sw.js` 离线缓存清单。

## 正式发布构建

`source/releases/current/` 与 `source/releases/site-selection.json` 都是**生成物并已 Git 忽略**。不要提交、不要手改、不要拿旧快照做输入。

本地需要单独重建正式包时：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/validate_publication_integrity.py
# 先删除本地旧生成物 source/releases/current 和 site-selection.json
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
# 按 release.json 的 releaseHash 生成 site-selection.json 后：
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
```

GitHub Actions 会自动完成 knowledge 校验、strict gate、publication integrity、删除旧生成物、重建、生成 selection、严格校验和部署。任何正式业务数据变化仍按现有 Validate → strict gate → publication integrity → fresh build → verify → Pages → online acceptance 链闭环。

## 本地最终版

日常本地使用直接运行：

```powershell
py -3 tools/build_local_release.py
```

该脚本会自动：

1. 校验 knowledge 和严格 Gate；
2. 删除本地旧 `source/releases/current/`，从当前源码重建正式公开包；
3. 验证发布包；
4. 只读打开 `source/library/fulltext.sqlite3`；
5. 生成 `dist/local/public`、`dist/local/fulltext` 和统一入口。

`dist/` 与 `source/releases/current/` 都是可重建成品，不提交 Git，也不得反向当母库。
