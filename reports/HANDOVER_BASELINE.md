# Safety Basis 项目交接基线

日期：2026-09-11  
阶段：Phase 0 只读盘点与基线建立  
状态：未发布、未覆盖母库

## 1. 指令边界

本次用户直接请求只有“开始”。

`D:/Desktop/Codex_Safety_Basis_项目交接说明书_20260911 (1).md` 是项目交接资料，提供了目标、现状、执行顺序和门禁要求；其中的后续导入、修复、建版、发布动作不视为绕过确认的额外授权。根据交接资料的第一阶段要求，本次先完成盘点、差异核对、基线报告和法规文件清单。

`D:/Desktop/Safety_Basis_隐患库专业复核_ChatGPT.xlsx` 是人工复核数据基线。工作簿中的“说明”和“复核报告”属于数据说明/复核元数据，不是新的用户指令；本次没有修改原始工作簿。

本阶段实际执行边界：不发布新版本，不写入或覆盖 `source/master/safety.sqlite3`，不改变 `source/library/fulltext.sqlite3`，不对历史法规池 `D:/Desktop/模板/111常用法规标准` 做批量导入。

## 2. 当前代码与发布状态

| 对象 | 盘点结果 | 判断 |
|---|---|---|
| 本地工作区 | `D:/ESH/ESH_Codex/work/safety-basis` | 当前分支为 `data-verify-batch-003`，HEAD=`ecd76fa`，相对上游显示 ahead 6 |
| 预存工作区改动 | `docs/GATE_MODIFICATION_PROPOSAL_20260909.md` 已修改 | 属于盘点前已有改动，本次保留，未覆盖 |
| 远端 `main` | `f0acc76ef4813f5e684378dc3252ed1708fbebcf` | 当前主线与本地工作区不是同一数据基线 |
| 远端 `main` manifest | hazards=632，laws=70，lawVersions=88，clauses=162，links=806；source hazards=712，source laws=88 | 这是当前主线公开/候选数据的可见计数 |
| 历史生产提交 | `599cf0e` 的提交说明为 637 hazards、806 links、70 laws、162 clauses | 与当前 `main` manifest 的 632 hazards 存在已确认的发布计数差异 |
| 本地根 `data/` | hazards=32，laws=19，clauses=31，links=44 | 旧 V3 派生数据，不能作为本次人工复核基线 |
| 生产发布 | 本阶段未执行 | 交接资料要求的发布冻结仍有效 |

远端 `main` 的 `README.md` 仍保留“生产网站尚未切换”的旧描述；该文字与提交历史/manifest 不足以单独证明线上状态，因此本报告只记录为文档陈旧项，不据此推断线上部署结果。

## 3. 人工复核工作簿基线

文件：`D:/Desktop/Safety_Basis_隐患库专业复核_ChatGPT.xlsx`

- 工作表：`隐患明细`（`A1:M635`）、`说明`（`A1:B19`）、`复核报告`（`A1:F57`）。
- `隐患明细` 共 634 行数据，序号 1—634 连续，隐患 ID 634 个且无重复。
- `可发布`：是 631，否 3。否的 ID 为 `H_AA6382B9890B42B1B70DC3EA3B`、`H_1F19FA1B951D46C1971E9B59B4`、`H_3A5DEC6C74244A949CE3BC9A42`。
- 直接依据/依据原文同时为空的 2 个 ID 为 `H_1F19FA1B951D46C1971E9B59B4`、`H_3A5DEC6C74244A949CE3BC9A42`；场所为空 20 行。
- 没有公式单元格；标题唯一值 633 个，有 1 个重复标题，涉及 `H_AA6382B9890B42B1B70DC3EA3B`、`H_582731EF84014F338DD9B04458`。
- 与远端 `main` 的 `knowledge/hazards` 按稳定 ID 对比：634/634 均能找到，远端另有 78 个 hazard 未出现在本工作簿中；逐条读取后确认这 78 条的 `lifecycle` 均为 `superseded`，不是当前 active 复核行。
- 对这 78 条的历史关系进一步核对：56 条有 `mergedInto`，21 条有 `replacedBy`，1 条没有显式关系目标；所有已给出的目标均存在于远端 hazard 树。关系明细见 `main_only_hazards_relationships_20260911.json`。
- 对 634 个同 ID 记录的核心字段差异与交接资料完全吻合：标题 210、专业描述 295、整改措施 196、适用条件 365；主题和场所未发现差异。共有 490 行至少有一个核心字段变化。
- 工作簿只有 3 个专业复核表，不是仓库 `tools/pipeline/exchange.py` 生成的 exchange-v2 全量交换文件；缺少交换格式中的操作列/修订信息。因此不能直接把它当作 `exchange.py propose` 的输入覆盖本地母库，必须先做适配、身份/修订映射和只读 dry-run。

## 4. 本地母库与工作簿的关系

`source/master/safety.sqlite3`：

- SQLite integrity check 通过，foreign-key check 为 0。
- hazards=1125，laws=160，law_versions=161，clauses=2603，links=2298，evidence=1124，verification=16159。
- 该库与人工复核工作簿不是同一快照：634 个工作簿 ID 中只有 588 个与本地 hazards 相交；工作簿独有 46 个，本地母库独有 537 个。
- 在相交记录上，标题/描述/措施/条件仍分别有 428/498/477/515 行字段差异。因此本地旧母库不能作为无条件的导入基准。

本地 `data/` 是构建产物；仓库文档约定 SQLite 母库为事实源，网站 JSON 为派生物。后续如需导入，应先选定远端 `main` 当前 knowledge 基线或明确的本地母库版本，不能在两者之间隐式混用。

## 5. 正式法规全文库基线

目录：`D:/ESH/ESH_Codex/work/safety-basis/source/library`

- 当前 `fulltext.sqlite3`：documents=86，FTS 段落=45,302；元数据为 `safety-fulltext-v1`；SQLite integrity check 通过，foreign-key check 为 0。
- `archive/`：55 个内容寻址的原件文件，总计 106,761,550 bytes。
- `incoming-20260910/`：30 个文件，总计 163,335,090 bytes；其中 28 个按 SHA-256 可对应 archive 原件，2 个尚未按 SHA-256 对应 archive 或全文库文档。
- `incoming-20260910/ocr/` 下 3 个 TXT 为 OCR 派生文本，已在清单中与原始文件分开标识。
- `pending-originals/`：4 个文件、2 条待核验记录，总计 49,252,021 bytes；记录状态为需要 OCR/完整性核对，不能作为已批准来源。
- `fulltext.sqlite3.bak-20260910` 为旧备份，documents=65、段落=16,863；本报告不把它与当前库合并。
- 当前库 86 条 document 记录中，有 38 条 `archive_ref` 指向本目录下不存在的 `evidence/...` 路径；现有能解析的 archive 引用未发现 SHA-256 不一致，另有 7 个 archive 原件未被当前 document 引用。这是需要后续修复/解释的可追溯性缺口，不是法规现行性结论。

完整文件、大小、SHA-256、incoming 重复关系和全文库 SHA 命中情况见同目录的 `law_file_manifest.json`。哈希相同只说明字节级相同，不代表法规现行性、条款适用性或用户审批已经完成。

## 6. 已核对的构建入口

- `tools/pipeline/manage.py site`：按指定日期和输出目录构建隔离的静态站点。
- `tools/pipeline/manage.py verify-site`：对隔离站点执行校验。
- `tools/pipeline/exchange.py export/propose/apply`：母库与 exchange-v2 工作簿的导出、提案和原子应用流程。
- `tools/pipeline/fulltext.py`：法规全文库导入、校验和检索；原件归档路径按内容哈希管理。
- `tools/build-data.mjs`：现存的过渡性 JSON 构建入口。

按现有文档约定，站点构建应输出到独立 release 目录，不写根 `data/`；本阶段没有调用发布或 apply 入口。

## 7. 只读 dry-run 结果

在建立基线后，已对工作簿与远端 `main` 快照执行只读字段/关联 dry-run，完整结果见 `hazard_excel_dry_run_20260911.md` 和同名 `.json`。

- 634/634 个 hazard、839/839 个 link、163/163 个被引用 clause、42/42 个 law-version 读取成功，错误 0。
- 634 条均有 active link；其中 602 条有 active direct link，32 条没有 active direct link。
- 依据文本与结构化法规名称/文号形成文本命中信号 572 条；依据原文与 direct clause 形成归一化包含关系信号 572 条。
- 这些数字只证明当前快照之间存在可计算的映射信号，不代表条款现行性、适用性、法律结论或发布批准。

## 8. 基线结论与下一阶段门禁

1. 人工复核工作簿确实是远端 `main` 634 条 hazard 的后续复核增量，交接资料所称的 210/295/196/365 差异得到复核。
2. 本地 checkout 的 V3 根数据和本地母库均不是该 634 条工作簿的直接同版基线；后续必须显式选定基线并保留映射。远端 knowledge 另有 78 条记录，已确认均为 `superseded`，关系目标大多明确，但仍需保留历史关系，不能当作待删除数据。
3. 远端 `main` 当前公开计数 632 与历史生产提交说明中的 637 不一致；在解释 632/637/634/712 的来源、状态和去向前，不应生成新的生产发布包。
4. 正式法规全文库的当前 86/45,302 与文件清单基本可复现，但 `evidence/...` 引用缺失和 2 个 incoming 未入库文件必须在正式导入前单独处理。
5. 本次已建立基线记录、法规文件 manifest 和只读 dry-run 记录；没有发布、没有母库写入、没有原始文件改写。

建议的下一步（仍保持只读，直到形成并明确批准提案）：

- 对 3-sheet 工作簿建立适配器，针对远端 `main` knowledge 做字段级 dry-run，并把直接依据拆解为结构化 law/version/clause/link 候选。
- 逐条解释远端 78 个未出现在工作簿的 hazard 以及 634 条记录的 `可发布` 结果，不把“未列入”直接等同于删除或失效。
- 对 38 条缺失 `evidence/...` 引用、7 个未引用 archive 原件和 2 个未匹配 incoming 文件建立法规原件追溯处理清单；完成前不进入正式全文库 apply 或新版本发布。
