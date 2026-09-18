# 项目阶段状态与恢复计划

本文件保留截至 2026-09-14 的业务核验记录，并补记 2026-09-16 至 2026-09-18 的各项里程碑及 2026-09-19 的 PR #60 与 PR #61 定点纠错专项。历史统计数字仍按对应阶段记录；不得将历史阶段数字冒充当前发布结果。

**PHASE 10 DONE；PHASE 11 长期维护循环持续，PR #60 与 PR #61 定点纠错专项已完成本地核验。** 2026-09-17 完成远端治理、publication 长期门禁、GB 46768-2025 收录、搜索修复及首批电气隐患转正；2026-09-18 完成两批 GB/T 47236-2026 候选转正、PHASE 12 exact-locator 批次、PR #60（全库 434 backlog 最终处置）及 PR #61（GB 18597 危废专项收录与转正）。针对 PR #60 与 PR #61 遗留的 blockers 与模型瑕疵，2026-09-19 专项展开定点纠错：危化法第五条替换为官方正式逐字原文；清理指向已合并实体的残留链接；撤销对 GB 12158 5 条 proposed 候选的不当标题合并（恢复为独立 proposed 候选，proposed 从 421 增至 426）；依原件 PDF 精准修复 9 条 active clause 科学计数法指数排版；逐条严格重构缩窄 PR #61 转正的 8 条危废贮存隐患（清除旧版附录A、非官方专用设施、越权防火防雷、消防通讯及宽泛选址，严格补齐触发条件与适用边界）；将 GB 18597 统一归并至既有规范版本卡 `L023`；客观记录私有母库历史写入后恢复备份的事实。当前正式基线为 **1,502 active / 426 proposed / 87 superseded（共 2,015）**，公开包为 **1,502 hazards / 58 law versions / 1,276 clauses / 1,621 links / public proposed 0**，`releaseHash=491d2e5236b2f0b35deb8cc52e029e8731d6cbd46b3d49d8a14d0fd68af61181`。

## 1. ULTIMATE GOAL — 最终目标

形成一套可长期维护、可审计、可持续部署的安全隐患法规依据网站：

- 私有法规证据库分层清楚：原件、历史版本、来源副本、OCR/文本派生物、全文检索数据库各司其职；
- `knowledge/` 是唯一正式结构化法规/版本/条款/隐患知识源；
- 同一法规同一真实版本只有一个 canonical identity，多来源只作为来源；
- 正式引用链满足：`隐患 → 法规身份 → 适用版本 → 具体条/款/项 → 逐字原文 → 官方/原始证据 → 适用性审核`；
- `proposed` 候选不得进入正式公共站；
- 本地私有版可从仓库 + `source/library/` 重建；
- `main` Validate / Build / Pages Deploy 全绿；
- 线上完成搜索、法规详情、来源链、候选隔离、历史/upcoming、桌面/移动端抽检；
- 任意新窗口不依赖旧聊天即可继续。

### Definition of Done

以下为整个项目的最终验收目标，不作为局部任务的完成条件：

1. 私有母库实体、重复、历史版本、派生物关系已解释；
2. 工作 SQLite 在实际本机运行时完整性正常，任何修复有备份和变更记录；
3. `knowledge/` 不存在未经解释的同法规同真实版本重复；
4. 1,929 目标隐患均有明确状态；
5. 正式记录全部通过 Gate；
6. `proposed` 不进入公开正式包；
7. 本地私有版可重建；
8. GitHub Actions 全绿；
9. GitHub Pages deploy success；
10. 线上抽检通过；
11. `docs/PROJECT_STATE.md` / README / HANDOFF 与最终状态一致。

---

## 2. 当前正式基线

**LAST VERIFIED：2026-09-19（分支 `fix-pr60-pr61-remediation-20260919`，基于 main `3fa240a911d18c13ed42c59d0f894d5bc354d4dc`，门禁严格测试全绿）。**

PHASE 10 正式发布 PR #40 已合并，发布合并提交为 `3c486cba5142a85ebaef366f04dbc7d4e53a91ba`；PR #41 完成 PHASE 10 状态收尾。PHASE 11 首轮维护随后完成：PR #42 收口等待态文档与远端审计；PR #43 将 publication canonical / catalog / 物理全文 / search 派生物一致性固化为长期硬门禁；PR #45 为该门禁补齐合成失败回归测试和 schema/asOf 契约。PR #45 合并提交为 `9e8de313e2321a9b81b8e812155434d7735e463b`，其后 `main` Validate run `35180759610` success，Build/Pages run `35180759551` 的 build 与 deploy 均 success。部署地址仍为 `https://an-0726.github.io/safety-basis/`。

PR #60（全库 434 backlog 最终处置与质量闭环）与 PR #61（GB 18597 危废专项）合并后，本轮定点纠偏全面修复了遗留缺陷：
1. 《危险化学品安全法》第五条纠正为全国人大常委会正式法律原文（主席令第六十四号第5条：全员责任制、双重预防机制）；
2. 彻底删除指向已合并实体的残留链接（`K_XLSX_FT_F2F31FEEE9DC4C57B899A82F`），`links to merged hazards` 清零；
3. 撤销对 GB 12158 5 条 proposed 候选的不当标题合并（`H_12158_10_1_2`、`H_12158_4_2_3_5_2`、`H_12158_6_3_2_2`、`H_12158_8_8_5_3`、`H_1764B7439DFE44C1A680A7393E` 恢复为独立 proposed 候选，proposed 从 421 升至 426，superseded 从 92 降至 87）；
4. 依据原件 PDF 精确修复 9 条 active clause 的科学计数法指数及排版（Unicode 上标），扫描器指数损坏告警彻底清零；
5. PR #61 转正的 8 条危废贮存隐患逐条严格缩窄重构（清除旧附录A、非官方专用设施、越权防火防雷、消防通讯及宽泛选址，严格补齐 6.2.2 触发条件，理清 6.1.1 与 8.3.5 适用边界），重算 reviews 与 contextHashes；
6. 删除多余的 `LV_STD_GB18597_2023`，条款统一切换归并至既有规范版本卡 `L023`（挂靠 `LF_L023`），修正 publication 题录；
7. 明确记录母库曾执行写入后完整恢复纯净备份的事实，物理核实指标一致。

当前 fresh public bundle 为 **1,502 hazards / 58 law versions / 1,276 clauses / 1,621 links / public proposed 0**，`releaseHash=491d2e5236b2f0b35deb8cc52e029e8731d6cbd46b3d49d8a14d0fd68af61181`。

公开发布架构已收口：

- `knowledge/` 是唯一正式结构化知识源；
- `source/publication/` 只承担题录、官方入口和获准全文，不创造第二套正式法规身份；
- `source/library/` 是本地私有法规证据库，不进 Git；
- `source/releases/current/` 与 `site-selection.json` 为运行时生成物，不提交 Git；
- 正式站只发布 Gate 通过的已核验隐患；
- `proposed` 不进入公网；
- `upcoming` 尚未实施版本不能支撑当前正式隐患。

### `main` 历史首次正式发布基线（PHASE 10）

- 1,429 条正式隐患；
- 57 个正式引用法规版本；
- 1,205 条正式条款；
- 1,544 个正式关联；
- 499 条 `proposed` 候选仅留 `knowledge/`，公网候选 0。
- PR #40 首次正式部署验收基线：`releaseHash=552cca4f3e12877c7af1f56cd323220fe6af5631e4b334ffddb04881bbc83a07`，`dataVersion=2026.09.16.3c486cba5142`。后续纯文档收尾提交可能触发等价重部署，不改变 governed knowledge/publication 业务数据。

### 当前 knowledge 状态

PHASE 6 从 519 条 `proposed` 基线候选出发，逐条生成最终处置；其中 20 条转为 `active`，499 条继续保持 `proposed`。其后 PHASE 11 新增 1 条正式电气隐患、转正 12 条电气候选，并在 GB/T 47236-2026 两个专题批次中转正 16 + 26 条；PHASE 12 exact-locator 再转正 11 条。
PHASE 13 全库 434 proposed backlog 最终处置中合并 1 条危化法草案实体。
PHASE 14 转正 8 条危废核心隐患，其余 10 条危废候选继续审慎保留 proposed。
本轮纠错专项撤销 5 条 GB 12158 候选的不当标题合并，恢复为 independent proposed 候选。
最终生命周期为：**1,502 active、426 proposed、87 superseded，共 2,015**。

当前 manifest 库存为：**103 个法规身份、106 个法规版本、2,940 条条款、2,015 个隐患实体、1,644 个关联、1,165 个 evidence、29 条 succession、75 条 requirements**。

新版 Excel 目标集仍为：**1,929 个唯一隐患 ID（621 修订、1,308 保留）**。它不是正式发布数量。

### 最近 Git 里程碑

- PR #29：正式/候选发布边界与 current 现场生成收口；
- PR #30：建立 `AGENTS.md` 作为仓库长期接手入口；
- PR #31：扩展为完整 MASTER ROADMAP；
- PR #32：完成 PHASE 1 私有母库审计，加入私有母库修复方案、安全维护工具和测试；
- PR #34：新增 `AGENT_EXECUTION_PROTOCOL.md`，固化“总控判断、本地 Luna 只执行本机操作”的协作边界；
- PR #36：完成 PHASE 3 document mapping 收口和 PHASE 4 六个 canonical gaps；CI Validate/Build 成功并已合并 main；
- PR #38：完成 PHASE 5 隐患目标集对账并已合并 main；
- PHASE 6 工作分支：完成 519 条候选最终处置、20 条正式回绑、499 条证据不足保留 proposed；
- PHASE 7 工作分支：publication 题录已 canonical 化为 106 个 law-version 行，全文目录收口为 69 个 canonical 来源关系，审计与验证全部通过；
- PHASE 8 工作分支：公开前端、canonical 跳转和本地私有全文展示边界已验收；公开/私有审计均 PASS，最终 workflow run `35120861560` success；
- PHASE 9 RC 工作分支：公共 RC 全量验证 workflow run `35122196162` success；同一 RC 源码快照结合真实私有 SQLite 完成本地最终版构建，输入库内容哈希不变；
- PHASE 10：PR #40 已合并 `main`（发布合并提交 `3c486cba5142a85ebaef366f04dbc7d4e53a91ba`）；PR checks、main Validate、main Build、Pages Deploy 全绿；已部署 artifact 与公网 HTTP 验收均 PASS。
- PR #41：完成 PHASE 10 状态收尾和一次性 workflow/trigger 清理，`main` 收口到长期维护入口。
- PR #42：完成 PHASE 11 首轮等待态远端审计，刷新 README / MAINTENANCE / HANDOFF 并固化维护触发条件。
- PR #43：新增 `tools/v4/validate_publication_integrity.py`，把 PHASE 7 一次性 publication canonical / 全文 / search 一致性审计升级为 Validate 与 Pages Build 都必须执行的长期硬门禁；合并后业务 releaseHash 仍为 `552cca4f3e12877c7af1f56cd323220fe6af5631e4b334ffddb04881bbc83a07`。
- PR #45：为 publication 长期门禁增加正常/失败合成回归测试和 catalog/search/text/gram schema + asOf 契约；合并后 main Validate `35180759610`、Build/Pages `35180759551` 全绿。
- PR #46：同步 Phase 11 当前状态文档，保持 long-lived 架构与维护文档与实际治理状态一致。
- PR #47：记录 current-main 本地验收状态（`docs/PHASE11_LOCAL_ACCEPTANCE_20260917.md` 及状态文档同步）；合并提交 `e3d2e2ac689b26c5dc4058e66feff095039b1358`，main Validate run `35199100753`、Build/Pages run `35199100714` 均 success。
- PR #48：为 `main` 配置并激活 GitHub Repository Ruleset（ID `23589482`），确立技术保护强制，并修复 Windows 本地 SQLite 文件句柄未关闭问题；PR CI 与 main CI/Pages 全绿。
- PR #49：记录历史远端分支清理闭环并关闭 Issue #44。
- PR #50：收录强制性国家标准 GB 46768-2025 及 63 条核心规范条款。
- PR #51：修复连续中文复合检索切词与假阳性问题。
- PR #52：补录配电箱（柜）前通道或维护空间被遮挡、占用的高频电气隐患。
- PR #53：将 12 条证据链完整的常见电气候选转为正式隐患。
- PR #54：按实施日期门禁校正 GB/T 13869-2017/2026 的 current/upcoming 版本治理；CI 与 Pages 均 success。
- PR #55：记录当时 current-main 的真实私有母库本地验收结果。
- PR #56：GB/T 47236-2026 直接匹配专题批次转正 16 条候选，1 条部分重叠候选保留 proposed。
- PR #57：GB/T 47236-2026 独立义务专题批次转正 26 条候选。
- PR #58：PHASE 12 exact-locator 批次转正 11 条候选；合并提交 `f6cf9ed34a7a42ba70f65336dc91aa4c6ce8a823`，main Validate `35321083736`、Build/Pages `35321083752` 及 deploy 均 success。
- PR #59：更新 `docs/HANDOFF.md` 等治理文档，收敛主线基线为 `b24fd495cf52f8948ec5742dc3641c0799337a73`。
- PR #60：PHASE 13 全库 434 proposed backlog 逐条处置闭环、质量错误清零、Windows release clean 兼容优化与真实私有母库本地最终版验收；合并提交 `16891123bbe2dac1627b33ff5716dd1d8cdad138`。
- PR #61：PHASE 14 GB 18597-2023 危险废物贮存专项收录，转正 8 条危废核心隐患；合并提交 `3fa240a911d18c13ed42c59d0f894d5bc354d4dc`。
- PR #62：证据获取规则长期治理调整：确立“本地证据库优先，但不是唯一来源；本地没有就主动联网查官方来源”原则；`source/library/` 仅作为本地优先原件与全文检索库，不再作为法规正式纳管的前置条件；官方来源（全国人大/国家法律法规数据库、中国政府网/国务院、发布机关/主管部门官网、国家标准全文公开系统、省市政府官网等）满足现行版本、精确条号、完整原文、官方 URL 与适用性时直接建立正式证据链入 Gate，无需先下载落库或写 SQLite。
- 纠偏工作分支（`fix-pr60-pr61-remediation-20260919`）：系统定点纠偏 PR #60 与 PR #61 blockers 与模型瑕疵：危化法第五条修复官方逐字原文；清理指向已合并实体的悬空链接；撤销 GB 12158 5 条 proposed 候选的不当标题合并（恢复为独立 proposed 候选，421→426）；9 条 active clause 指数排版依照原件精确恢复；PR #61 8 条危废贮存隐患逐条严格缩窄重构；删除多余的 `LV_STD_GB18597_2023`，条款统一切换归并至规范版本卡 `L023`。

---

## 4. 私有母库与证据获取规则

本地工作仓库：`D:\ESH\ESH_Codex\work\safety-basis\`

私有法规母库：`D:\ESH\ESH_Codex\work\safety-basis\source\library\`

### 证据获取长效规则（PR #62 确立）
- **本地证据库优先，但不是唯一来源；本地没有就主动联网查官方来源。**
- `source/library/` 只是优先使用的本地原件和全文检索库，不是法规正式纳管的前置条件。以后遇到本地没有某项法规、标准、现行版本或完整条款时，不得因为“本地无原件”停止核验，也不得直接把它长期留在 proposed。
- 应继续联网查询权威官方来源，优先：全国人大 / 国家法律法规数据库、中国政府网 / 国务院、法规或标准发布机关和主管部门官网、国家标准全文公开系统 / 全国标准信息公共服务平台、省市政府及主管部门官网。
- 只要官方网页或官方 PDF 能核实：**法规/标准身份 → 当前适用版本 → 精确条/款/项或标准条号 → 完整逐字原文 → 官方 URL/原始证据 → 隐患适用性**，就可以直接建立正式 evidence / lawVersion / clause / link / review 并进入 Gate，不需要先下载进私有母库，也不需要先写 fulltext.sqlite3。
- 搜索摘要、AI、OCR、Excel、百科、培训网站、商业法规库和普通第三方转载仍只能用于找线索，不能代替正式原文。
- 绝不把“本地没有法规原件”当成无法继续核验的理由。

### 母库操作事实澄清与当前核实验证
- **操作事实客观记录**：本轮在 Phase 14 初期曾对 `source/library/fulltext.sqlite3` 运行过写入插入操作，随后已通过安全备份原位完全恢复，不可再表述为“全过程只读零修改”；
- **当前物理属性核验**：当前文件 SHA-256 为 `4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`，文件大小 106,958,848 字节，修改时间（UTC）为 `2026-09-17T10:11:19.831234+00:00`，`documents=171`，`fulltext_fts=215,464`，本机 `PRAGMA integrity_check` 结果为 `["ok"]`，与写入前纯净备份完全一致。

Google Drive for desktop 已同步项目。Drive 关键词搜索可能漏掉 `.sqlite3` 二进制文件；应直接读取已知 `source/library` 文件夹，不可因搜索 0 条判断不存在。

### PHASE 1 最终只读审计

- SQLite 文件大小：106,958,848 bytes；`documents=170`；`fulltext_fts=215,326`；唯一文件 SHA-256=166；
- 4 组同一 SHA 双登记，共 8 行；`sum(paragraph_count)=count(fulltext_fts)=215,326`；逐 document FTS 数量一致；
- 同标题双记录 20 组，其中 2 组是真实不同版本，其余为同真实版本旧身份/再导入/多载体；
- 明确真实不同版本：`AQ 4228-2012 / AQ 4228-2025`、`GB/T 13869-2017 / GB/T 13869-2026`；
- current `archive/` 有 136 个 SHA：129 个被当前 `archive_ref` 直接引用，另 7 个为历史纯文本派生物；
- 38 行旧 `evidence/...` 引用不可按标题猜目标；
- inventory：144 原文件 / 138 唯一 SHA / 6 完全重复；inventory-only 不可批量自动导入；
- `pending-originals` 中 TSG 08-2026、TSG 92-2026 待 OCR 载体须先核版本/来源，不可直接再次导入；
- `document_id` 混有 `LF_*`、`LV_*`、旧 `Lxxx`、标准号，不能直接当 canonical law-version 主键。

详细规则：`docs/PRIVATE_LIBRARY_REMEDIATION_PLAN.md`。

### PHASE 3 第一批：FTS5 修复 — 本机 PASS，云盘内容不变量复核 PASS

本机一致性备份：`source\library\backups\fulltext.sqlite3.bak-20260914-155510+0800`。

修复后：documents=170；ftsRows=215,326；paragraphCountSum=215,326；FK errors=0；逐 document mismatch=0；`ftsContentSha256=1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd` 未变；数据库文件 SHA-256=`7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`；本机 `integrity=["ok"]`。

搜索抽检：`洗眼器=15`、`危险化学品=13,864`、`GB 55036=707`。总控从 Drive 下载同字节文件独立复核，行数、全文摘要、FK、搜索结果全部一致。

兼容性备注：总控 Linux/Python SQLite 3.46.1 对同一字节文件的 `PRAGMA integrity_check` 仍报告 FTS5 inverted-index 错误，而项目实际本机运行时为 `ok`。因此后续 FTS 维护以**项目本机运行时 + 内容不变量 + 搜索抽检**联合验收，不允许因异构运行时单项结果自动覆盖数据库。

### PHASE 3 第二批：170 documents canonical / alias 映射 — PASS

完整报告：`docs/PRIVATE_LIBRARY_DOCUMENT_MAPPING_20260914.md`。

- `GB/T 12801-2008`、`GB 55036-2022` raw SHA + extracted-text SHA 均相同，可列为未来独立高风险物理去重候选；
- `HJ 2025-2012`、`GB 15603-2022` raw SHA 相同但历史抽取文本/段落数不同，只做 alias，不物理删旧 FTS；
- 18 组同真实版本双身份已分类：12 组原已对齐 knowledge，6 组为 canonical gap；
- 2 组真实不同版本禁止合并；
- 38 条 legacy `evidence/...` 中仅 `LF_L027 / HJ 2025-2012` 有同 SHA current archive 目标可安全重绑，其余 37 条继续保留 legacy provenance；
- 7 个 archive-only 历史纯文本派生物不生成独立法规身份；
- 当前不做 document 物理 DELETE/archive 移动；任何物理压缩另开高风险批次。

### PHASE 4：六个 canonical gaps — PASS

已由总控回到官方来源核验，并在 PR #36 建立完整 law/lawVersion/evidence/review/succession 链：

- `危险化学品目录（2015版）`：1 个 law identity，显式建模为 2015 base → 2023 柴油调整后 → 2026 新增 5 种化学品后三个版本状态；私有 2015 原件仍映射 2015 版本，不冒充 2026 当前完整状态；
- `各类监控化学品名录`（工业和信息化部令第52号）；
- `GB 17914-2013`、`GB 17915-2013`、`GB 17916-2013`；
- `特种设备安全监察条例（2009修订）`。

新增：6 laws、8 lawVersions、8 authoritative evidence、6 law reviews、8 lawVersion reviews、2 successions；manifest 已更新到 102 laws / 105 lawVersions / 1,114 evidence / 28 successions。review hash 使用仓库 `canonical.py` 口径绑定。

私有 `source/library/document-aliases.json` 已在 Drive 原位回填 6 个 `canonicalVersionId`，`knowledgeUnmappedTitles=[]`；其策略仍是 `local_display_grouping_only`，`databaseMutation=false`、`archiveMutation=false`，未写 SQLite/FTS/archive。

PR #36 在 canonical 数据提交后已通过：

- `Validate safety data` — success；
- `Build current verified website` — success。

### PHASE 5：1,929 目标 ID 与 2,014 knowledge hazards 全量对账 — PASS

权威目标源已固定为本机 `D:\Desktop\隐患库_1929条_新版口径全部整改完成_20260914.xlsx`，工作表 `隐患明细_修订后!A2:R1930`，文件 SHA-256=`c84ec965ce808c780547842a1a82cb7eca01d0a8fdd018c054414b2b5be24a6f`。

- 工作簿 1,929 行、1,929 个唯一隐患 ID：621 条“已修订”、1,308 条“原审查通过/保留”；
- `knowledge/hazards` 2,014 个文件、2,014 个唯一对象 ID，文件名与对象 ID 一致；
- 1,929 个目标 ID 全部直接存在于 knowledge，`target-missing=0`；
- 目标集实际分类：1,409 `target-current`、512 `target-proposed`、8 `target-merged-alias`；
- knowledge 目标外 85 条不是“85 条重复”：56 条 merged 历史、21 条 split 父项、1 条正向事实非隐患历史、7 条 active 目标外待复核；
- 全库 64 条 `mergedInto` 边：缺失目标 0、循环 0；
- 工作簿标题与 knowledge 标题逐字一致 1,861 条；统一中英文标点和空格后一致 1,920 条；另 9 条为实质表述差异，需确认是已审阅专业化改写还是同步遗漏；
- 8 个目标内 merged alias 已统一为 `superseded`，不删除稳定 ID、merge 去向或证据；
- 7 个目标外且缺少完整正式 Gate 的实体已统一为 `proposed`，其 8 条 link review 已退回 rejected 并重绑上下文；
- 9 个实质标题差异均有 verified hazard review，且 Git 历史显示来自正式核验/官方来源核验批次，保留 knowledge 的专业化表述；
- 最终 lifecycle 库存：1,409 active、519 proposed、86 superseded，共 2,014；
- `validate_all.py` PASS，`strict_release_audit.py` PASS（blocker 0），正式包现场重建/verify PASS（releaseHash=`9acfc43cba1f2b58bc78307b7ac097e31d09872ebba63b0f470357fd95b47ec0`）；正式发布仍为 1,409 / 55 / 1,193 / 1,524，公网候选 0；
- pipeline 单元测试 26/26 PASS，Node 测试 13/13 PASS；reconciliation 连续重跑结果确定一致。

可重复执行工具：`tools/maintenance/reconcile_hazard_target_set.py`；受限状态修复工具：`tools/maintenance/apply_hazard_reconciliation_status.py`。机器映射：`docs/hazard-reconciliation.jsonl`。人类报告：`docs/HAZARD_RECONCILIATION.md`。工作簿未修改；私有母库、SQLite、archive 未修改。

### PHASE 6：519 条候选法规证据回绑 — PASS

完整人类报告：`docs/PHASE6_FINAL_DISPOSITION.md`；机器明细：`docs/phase6-final-disposition.jsonl`；可重复执行工具：`tools/maintenance/finalize_phase6.py`。

- PHASE 6 基线 519 条 `proposed` 全部生成最终处置，覆盖率 **519/519**；
- 110 条 exact current reviewed clause 候选全部重新复核，不再把 locator 相同直接等同为可转正；
- 20 条对象、现行条款逐字原文、官方/原始证据、适用性和当前上下文 review 全部闭环，经 Gate 后转为 `active`；
- 499 条继续 `proposed`，每条在机器处置清单中保留原因和下一证据动作；其中大量项目属于“未找到精确当前已核条款”或“仅 locator 匹配但语义适用性未证明”，另有错误条款对象、混合对象、数值口径变化、推荐性措辞、原文质量异常等明确原因；
- 新纳管现行《江苏省生产经营单位安全风险管理条例》（2024-11-01施行），建立 law/version/evidence/review 及第8、11、12、16条逐字官方证据链；对江苏风险辨识、风险管控清单、较大以上风险公示等候选优先采用当前更强、更直接的现行地方性法规；
- 关键保守判定包括：GB 55037-2022 第3.4.5条现行坡度上限为10%，不拿来支撑“>8%”；该条没有固定“距外墙5m”阈值；GB 50187-2012 第5.7.4条“出入口数量不宜少于2个”不机械当绝对违法；粉尘防爆第十八条不跨对象支撑一般废气收集、压差、集气罩、选址；GB 12158-2024 第7.6条当前 knowledge 文本质量异常，未转正式链；
- 工作分支最终 lifecycle：**1,429 active、499 proposed、86 superseded，共 2,014**；
- manifest：**103 laws / 106 lawVersions / 2,847 clauses / 2,014 hazards / 1,567 links / 1,161 evidence / 28 successions / 75 requirements**；
- 一次性 PHASE 6 finalization workflow 完整执行成功：`validate_all.py`、`strict_release_audit.py`、Node tests、pipeline Python tests、fresh current bundle build 和 `verify_unified_bundle.py` 均成功；workflow run `35078569190` conclusion=`success`；
- 本批未写私有 SQLite/FTS/archive，未修改既有 hazard 稳定 ID，未合并 PR，未部署 Pages，未做线上发布；一次性 workflow 与 trigger 在成功后已从分支清理。

### PHASE 7：publication / 官方来源 / 全文资料归整 — PASS

完整人类报告：`docs/PHASE7_PUBLICATION_AUDIT.md`；机器审计：`docs/phase7-publication-audit.json`；可重复执行工具：`tools/maintenance/finalize_phase7_publication.py`。

- `source/publication/law-index.json` 从 216 行归整为 **106 个 canonical law-version 行**，与 `knowledge/law-versions` 形成 1:1 身份投影；publication 不再创建第二套法规/版本身份；
- 清理 144 个 stale publication IDs，并在需要时通过 canonical ID、精确官方 URL 或“唯一官方名称 + 生效日期”解析到现有 knowledge 版本，不按标题相似猜测；
- 全文 catalog 从 155 行收口为 **69 个 canonical 来源关系**：其中 **11 份**明确 `official_legal_text` 且 `fullTextReviewed=true` 的获准官方全文继续公开，**58 个**只保留 metadata-only 官方入口；
- 86 个无法解析到 governed knowledge identity 的旧全文目录行退出 public catalog；对应 publication 文本/索引作为可重建派生物清理，不触碰私有原件、SQLite、OCR 或 archive；
- 全文搜索索引确定性重建为 **256 个 gram shards**；proposed hazard 泄漏 **0**，private-boundary marker 泄漏 **0**；
- `knowledge/` 未修改，知识库存继续保持 **103 laws / 106 lawVersions / 2,847 clauses / 2,014 hazards / 1,567 links / 1,161 evidence / 28 successions / 75 requirements**，hazard lifecycle 继续为 **1,429 active / 499 proposed / 86 superseded**；
- 一次性 PHASE 7 workflow run `35095422830` 已 `completed / success`；`validate_all.py`、`strict_release_audit.py`、Node tests、pipeline Python tests、fresh current bundle build 和 `verify_unified_bundle.py` 全部成功；
- 本批未修改私有 SQLite/FTS/archive，未修改稳定 knowledge IDs，未提交 release/current 生成包，未合并 PR，未部署 Pages，未做线上发布。

### PHASE 8：前端与本地私有版一致性验收 — PASS

可重复执行审计：`tools/maintenance/audit_phase8_consistency.py`；公开审计：`docs/phase8-public-audit.json`；私有审计：`docs/phase8-private-audit.json`；本地展示回归测试：`tools/pipeline/tests/test_library_site_phase8.py`。

- 公网 fresh bundle 审计 PASS：**1,429** 个正式隐患、**1,205** 个随正式链发布的条款、**57** 个实际正式法规版本；`knowledge/` 中 499 个 proposed 在公网为 **0**；private-boundary marker 命中 **0**；
- publication 全文/入口边界保持为 **69** 个 catalog documents，其中 **11** 份获准全文、**58** 个 link-only 官方入口；其中 27 个是 catalog-only canonical versions，不被错误当成当前正式法规跳转；
- `web/js/library.js` 已只对实际 formal law index 中的版本显示“查看收录条款与关联隐患”，source-only 全文/入口不再生成无效正式法规跳转；
- 本地 `tools/v4/library_site.py` 使用 `document-aliases.json` 仅做私有展示分组/canonical label，不改变正式 authority；只有实际存在的原始文件才生成“打开原始文件”链接，legacy `evidence/...` provenance 不再变成断链；
- 私有库只读审计 PASS：SQLite **170 documents / 215,326 FTS rows / 215,326 paragraphCountSum / per-document mismatch 0**；132 个 archive-backed document rows 对应 129 个唯一 archive SHA，Drive 当前 archive 中 **129/129** 全部找到；38 条 legacy evidence provenance 保留；unknown prefix 0、archive SHA mismatch 0；
- private alias 共 **18 groups / 36 member document keys / 18 canonicalVersionIds**，missing members 0、knowledge unmapped titles 0；审计未写 SQLite/FTS/archive；
- PHASE 8 finalizer workflow run `35120861560` 已 `completed / success`：frontend/private compatibility tests、`validate_all.py`、`strict_release_audit.py`、fresh current bundle build + verify、公开一致性审计、私有/公开边界检查、公开审计报告提交全部成功；
- 本阶段没有修改 `knowledge/`、`source/publication/` 的业务数据，没有提交 `source/releases/current/` 生成物，没有 merge PR，没有部署 Pages，没有线上发布；一次性 PHASE 8 workflow/trigger 已在成功后清理。

### PHASE 9：全量验证与 Release Candidate — PASS

公开 RC 验收记录：`docs/phase9-rc-public.json`。

- 工作分支：`phase9-release-candidate-20260917`；公共 RC 验证源提交为 `c74a0970f1cc64e5d2bad9944340304c171050f2`，workflow 自动记录提交为 `c58261f77d77ebe79e73e6f0385060caefab764c`；
- GitHub Actions run `35122196162` 已 `completed / success`：Node tests、pipeline Python tests、`validate_all.py`、`strict_release_audit.py`、fresh unified release build、`verify_unified_bundle.py`、PHASE 8 regression audit 全部 PASS；
- 公共 RC 保持 **1,429 hazards / 57 laws / 57 lawVersions / 1,205 clauses / 1,544 links**，strict blockers 0，knowledge 中 499 proposed 在公网仍为 0；publication 仍为 69 个 catalog documents（11 full text + 58 link-only）；
- 使用 run `35122196162` 上传的同一 RC 源码快照，在本地接入真实私有 `fulltext.sqlite3` 与 `document-aliases.json` 后实际执行 `tools/build_local_release.py`，直接退出码 **0**；
- 本地最终版生成成功：**170 documents / 215,326 FTS rows / 215,326 paragraphCountSum / 36 canonical alias members**；生成 170 个法规全文页面及统一入口；
- 私有 SQLite SHA-256 在构建前后均为 `7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`，alias 文件构建前后哈希也一致，确认本地构建只读、未修改私有库；
- 本地重建公开包 verify PASS，releaseHash=`680089d53c1fe793bcc71f420093aa1080126e29e4c4d9b2a043849cf01209a9`；该哈希属于本地当日重建产物，不替代公共 RC 报告中的 GitHub Actions RC releaseHash；
- 本阶段未修改 `knowledge/` 业务数据、未修改私有 SQLite/FTS/archive、未提交 `source/releases/current/` 生成物、未合并 main、未部署 Pages、未做线上验收。

---

## 5. MASTER ROADMAP

状态：`DONE` / `IN PROGRESS` / `PENDING` / `BLOCKED`。

### PHASE 0 — 架构与发布边界收口 — DONE
knowledge 主导；candidate 不发布；upcoming 不提前支撑；current 现场生成。

### PHASE 1 — 私有母库只读实体审计 — DONE
170 documents、archive、incoming、inventory、pending、knowledge 初步身份映射完成。

### PHASE 2 — 母库整理方案与安全变更清单 — DONE
修复/归并分批、备份回滚门禁、维护工具和测试已建立。

### PHASE 3 — 私有母库实际修复与确定性去重 — DONE
FTS 修复和完整 document mapping 已闭环；暂不执行非必要物理去重。

### PHASE 4 — `knowledge/` 法规身份/版本 canonical 化 — DONE
六个 private canonical gaps 已正式纳管，危险化学品目录修订链已显式建模，private alias 已全部映射 knowledge canonical；PR #36 CI Validate/Build 已成功。

### PHASE 5 — 2,014 knowledge 隐患实体 ↔ 1,929 目标集对账 — DONE
完整机器映射和人类报告已生成；目标缺失 0，85 条目标外实体已逐项分类，24 个状态/标题差异已闭环，Gate 和正式包验证通过。

### PHASE 6 — 候选法规证据回绑与转正 — DONE
519/519 候选已形成最终处置；20 条完整 Gate 后转 active，499 条证据/适用性不足继续 proposed 并保留明确原因；110 条 exact 候选全部复核；现行江苏风险管理条例已纳入 canonical 证据链；PHASE 6 验证链全部通过。

### PHASE 7 — publication / 官方来源 / 全文资料归整 — DONE
publication 已收口为 knowledge canonical 身份投影；题录、官方入口、获准全文与搜索索引边界完成归整，proposed/private 泄漏均为 0。

### PHASE 8 — 前端与本地私有版一致性验收 — DONE
公网仅投影正式 Gate 数据；source-only catalog 不生成错误正式法规跳转；本地私有版 canonical alias、全文和原始文件链接边界已验证；公开/私有审计均 PASS。

### PHASE 9 — 全量验证与 Release Candidate — DONE
公共 RC workflow 与真实私有库 local release build 均已完成并 PASS；输入私有库哈希构建前后不变，proposed/private 发布边界保持不变。

### PHASE 10 — 最终合并 main、GitHub Pages 部署、线上验收 — DONE
PR #40 checks 全绿后已合并 `main`；main Validate/Build/Deploy 全部 success；GitHub Pages 发布成功；对实际部署 artifact 完整性、公开边界、搜索索引/法规索引/全文目录执行验收，并通过 GitHub-hosted runner 对公网 URL 做独立 HTTP 抽检，全部 PASS。

### PHASE 11 — 长期维护循环 — IN PROGRESS
长期维护已实际运行：除等待态治理与 publication 门禁外，已完成 GB 46768-2025 收录、搜索修复、电气隐患补录/转正、GB/T 47236-2026 两个专题批次、PHASE 12 exact-locator 批次、PHASE 13 全库 434 backlog 处置闭环（PR #60）、PHASE 14 GB 18597-2023 危废专项收录（PR #61）、证据获取治理规则长期升级（PR #62）以及 PR #60 与 PR #61 系统定点纠偏专项。当前生命周期为 **1,502 active / 426 proposed / 87 superseded（共 2,015）**；母库物理属性与写入前纯净备份完全一致；仅实际阶段变化时更新本文件。

### PR #60 与 PR #61 系统定点纠偏专项 — DONE (LOCAL)
2026-09-19 全面处置此前遗留的 blockers 与模型偏差：
- 危险化学品安全法第五条纠正为全国人大常委会正式法律原文（主席令第六十四号第5条）；
- 删除指向已合并实体的残留链接（`K_XLSX_FT_F2F31FEEE9DC4C57B899A82F`），彻底消除 links to merged hazards 违规；
- 撤销对 GB 12158 5 条 proposed 候选的不当标题合并（`H_12158_10_1_2`、`H_12158_4_2_3_5_2`、`H_12158_6_3_2_2`、`H_12158_8_8_5_3`、`H_1764B7439DFE44C1A680A7393E` 恢复为独立 proposed 候选，proposed 从 421 增至 426，superseded 从 92 降至 87）；
- 依据标准原件 PDF 还原 9 条 active clause 的科学计数法指数及排版（Unicode 上标），文本损坏警告清零；
- 逐条严格重构缩窄 PR #61 转正的 8 条危废隐患（清除旧版附录A、非官方专用设施、越权防火防雷、消防通讯及宽泛选址，补齐触发条件与适用边界），重算 reviews 与 contextHashes；
- 删除多余的 `LV_STD_GB18597_2023`，条款统一切换归并至既有规范版本卡 `L023`（挂靠 `LF_L023`），修正 publication 题录；
- 客观记录私有母库历史写入后恢复备份事实，核实物理指标与写入前纯净备份完全一致；
- 全量门禁（`validate_all.py`、`strict_release_audit.py`、`validate_publication_integrity.py`、`verify_unified_bundle.py`、Node 测试、Python 单元测试及扫描器）全绿。

---

## 6. CURRENT PHASE — 当前阶段

**PR #60 与 PR #61 系统定点纠偏专项已完成本地全量开发、门禁与验收，正处于 Git 提交、推送远端分支、创建 Pull Request 及远端 CI/Pages 闭环阶段。**

最新生命周期：**1,502 active / 426 proposed / 87 superseded（共 2,015）**。
正式公开包指标：**1,502 hazards / 58 law versions / 1,276 clauses / 1,621 links / public proposed 0**，`releaseHash=491d2e5236b2f0b35deb8cc52e029e8731d6cbd46b3d49d8a14d0fd68af61181`。

本地私有母库状态核实：
- 母库文件：`source/library/fulltext.sqlite3`（文件大小 106,958,848 bytes，SHA-256=`4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`，mtime(UTC)=`2026-09-17T10:11:19.831234+00:00`）；
- 已完成备份原位恢复，各项指标与写入前纯净备份完全一致；
- 本地最终版发布包构建成功，耗时正常，退出码 0。

---

## 7. NEXT ACTION — 下一动作

> **推送专有工作分支 `fix-pr60-pr61-remediation-20260919` 至远端 GitHub 仓库，创建指向 `main` 的 Pull Request，跟踪 GitHub Actions check-runs（Validate 与 Build），完成合并并验证线上 Pages 部署与状态一致性。**

未来法规、标准和 proposed 处理长效路线（依 PR #62 规则执行）：
1. **本地证据库优先，但不是唯一来源；本地没有就主动联网查官方来源。**
2. `source/library/` 只是优先使用的本地原件和全文检索库，不是法规正式纳管的前置条件。遇到本地没有某项法规、标准、现行版本或完整条款时，不得因为“本地无原件”停止核验，也不得直接把它长期留在 proposed。
3. 联网优先查询全国人大/国家法律法规数据库、中国政府网/国务院、发布机关及主管部门官网、国家标准全文公开系统/全国标准信息公共服务平台、省市政府及主管部门官网。
4. 官方网页/PDF能核实“法规/标准身份 → 当前适用版本 → 精确条/款/项或标准条号 → 完整逐字原文 → 官方 URL/原始证据 → 隐患适用性”全链条时，直接建立正式 evidence / lawVersion / clause / link / review 并进入 Gate，不需要先下载进母库或写 SQLite。
5. 搜索摘要、AI、OCR、Excel、百科、培训网站、商业法规库和普通第三方转载只能用于找线索，不能代替正式原文。
6. 严禁把“本地没有法规原件”当成无法继续核验的理由。
