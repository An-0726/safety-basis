# 隐患依据速查库

面向工贸企业安全检查与评价报告的法规、标准、条款和隐患关联库。国家层面为主，江苏、南京地方依据为补充。

在线站点：<https://an-0726.github.io/safety-basis/>

> **AI / Codex / 新窗口接手：先读根目录 [`AGENTS.md`](AGENTS.md)。** `AGENTS.md` 维护长期工作边界；[PROJECT_STATE](docs/PROJECT_STATE.md) 维护阶段进度与暂停状态；本 README 负责长期架构、数据口径和维护硬规则。当前只认 `main` 一条主线、`knowledge/` 一套正式结构化知识源、`source/library/` 一套本地私有证据库。历史“final/latest/日期版”不留在当前目录树，需要追溯时看 Git。

## 一、当前唯一架构

```text
source/library/ 〔本地私有证据，Git 忽略〕      官方互联网来源
原始 PDF / 网页快照 / OCR / SQLite            全国人大/政府网/主管部门/国家标准平台
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
                  knowledge/
              正式结构化知识源
       法规身份/版本/条款/隐患/关联/审核
                       │
                       ├──────────────► source/publication/
                       │                公开题录/官方入口/获准全文
                       │                不创造第二套正式法规身份
                       ▼
                当前日期链式 Gate
                       ▼
          tools/v4/build_unified_release.py
                       ▼
      source/releases/current/ 〔生成物，Git 忽略〕
                       ▼
            GitHub Pages / dist/local public
```

### 核心职责

| 层级 | 位置 | 职责 |
|---|---|---|
| 正式知识源 | `knowledge/` | 法规身份、真实版本、条款、隐患、关联、审核 |
| 公开来源层 | `source/publication/` | 题录、官方入口、允许公开分发的全文 |
| 私有证据库 | `source/library/` | 原件、archive、incoming、SQLite、OCR；不进 Git |
| 网站源码 | `web/` | 当前公开界面 |
| 发布成品 | `source/releases/current/` | CI/本地现场生成；不提交、不手改 |

本地工作仓库约定：

`D:\ESH\ESH_Codex\work\safety-basis\`

私有法规证据库：

`D:\ESH\ESH_Codex\work\safety-basis\source\library\`

`fulltext.sqlite3` 是检索数据库，不是法律原文最高证据。`source/library/` 是优先使用的本地证据缓存，而不是唯一证据源；本地缺失时必须继续查找权威官方互联网来源。正式引用可以来自已核验的本地原始 PDF / 网页快照，也可以直接来自全国人大、政府网、主管部门官网、国家标准平台等官方网页/PDF，只要版本、条款、完整原文、官方来源和适用性均完成核验。

## 二、正式站与候选彻底分开

正式站只发布当前 `asOf` 日期链式 Gate 通过的 active 隐患。`lifecycle=proposed` 候选继续保存在 `knowledge/`，但**不进入正式公共包**。

候选退出正式包不等于删除：稳定 ID、来源行、待办和审核状态继续保存；只有完成“法规身份 → 适用版本 → 具体条款 → 原文证据 → 隐患适用性 → 审核”后才能转正。

2026-09-19 当前基线（长期维护模式，五边完全一致）：

### 1. 正式公开站发布基线（Public Release Bundle）
- **1,744 条正式隐患**（全部为 active 状态，公开 proposed 严格为 0 条）；
- **60 个实际引用法规版本**（全部具有现行有效条款支撑）；
- **1,354 条正式条款**（全部包含逐字官方原文）；
- **1,863 个正式关联**（全部通过严格 Gate）；
- **69 个 canonical 来源关系**（11 份获准公开全文 + 58 个官方链接入口）；
- `releaseHash=5df466dec1a67757edd0a6a57f44a9cee0d2d84c40406f5efae69d1c31112f1a`。

### 2. 全库知识源库存（Knowledge Base Total Inventory）
- **104 个法规身份 (laws)**；
- **107 个法规版本 (law-versions)**；
- **3,007 条法规条款 (clauses)**；
- **2,015 个隐患实体 (hazards)**：
  - **1,744 条现行有效 (active)**；
  - **184 条分类保留 (proposed)**（含 149 条 upcoming 等依规保留项）；
  - **87 条归并替代 (superseded)**；
  - 隐患生命周期平衡：`1,744 + 184 + 87 = 2,015`（100% 对账平衡）；
- **1,886 个关联 (links)**；
- **1,197 个官方证据卡 (evidence)**；
- **75 条管理要求 (requirements)**；
- **29 条替代演进关系 (successions)**。

本项目已完成全库 426 proposed backlog 的逐条审查与最终处置闭环（PR #64，242 条转正 active，184 条依规范分类保留），补齐历史遗留证据卡与规整审查记录（dangling evidenceRefs 彻底清零），全量自动化门禁与 GitHub Actions CI 全绿，在线 GitHub Pages（`https://an-0726.github.io/safety-basis/`）100% 验收通过，正式切换为长期维护模式（Long-Term Maintenance Mode），业务范围全面冻结。历史 1,409、1,429、1,502 等基线均为阶段历史过程数字，不再作为当前正式站口径。README / PROJECT_STATE / HANDOFF / knowledge manifest / public manifest 五边数字完全一致。

## 三、法规身份、版本、来源必须分开

固定模型：

```text
法规身份 → 法规版本 → 具体条款 → 原文证据 → 隐患关联 → 审核记录
```

规则：

- 同一法规、同一真实版本、不同官方来源 → **一个版本，多来源**；
- 同一法规、不同真实版本 → 分别保留，记录生效、替代和废止关系；
- publication 题录/平台记录只是来源资料，不因来源不同生成第二张正式法规卡；
- 正式法规页只包含正式条款实际引用的 `knowledge/law-versions`；
- 正式法规必须至少有一条正式条款；
- knowledge 若出现同一 `lawId + versionKey` 两个正式版本 ID，构建器拒绝发布，先人工对账；
- 不按标题模糊删除法规或隐患；
- `LF_* / LV_* / C_* / H_*` 是稳定关系键，不为了界面好看随意重编号。

## 四、“最新发布”不等于“当前适用”

当前正式依据按发布包 `asOf` 日期判断。法规版本只有同时满足以下条件，才能支撑当前隐患：

- `validityStatus=active`；
- `effectiveDate <= asOf`；
- `endDate` 为空，或 `asOf < endDate`；
- 法规身份、版本、条款、证据和关联审核链均通过 Gate。

`upcoming` 表示已经发布但尚未实施。它可以保留在知识库、私有证据库和“法规全文/资料库”，但实施日前**不能作为当前正式隐患依据**。

## 五、正式法规引用硬门禁

正式依据至少必须满足：法规身份明确、版本明确、效力明确、具体条款定位明确、有逐字原文、有官方 URL 或可追溯证据快照、条款号与原文一致、条款确实适用于对应隐患、审核记录仍绑定当前内容。

### 证据来源路线

- **先查本地，不限于本地。** 本地私有母库有可靠原件时优先复用；本地没有、版本不全或原文不完整时，必须主动联网查官方来源，不得把“本地无原件”本身当成证据缺口的终点。
- **官方网络证据可以直接正式纳管。** 全国人大/国家法律法规数据库、中国政府网/国务院、发布机关和主管部门官网、国家标准全文公开系统/全国标准信息公共服务平台、地方政府或主管部门官网等，只要能确认现行版本、精确条款、完整原文和适用范围，就可以直接建立 evidence / lawVersion / clause / link / review。
- **不要求先导入私有库。** 从官方网页/PDF核验成功后，可以直接形成正式证据链；是否另存私有原件、是否写入全文 SQLite 是离线保存/检索维护事项，不是法规转正前置条件。
- 普通搜索结果、AI摘要、OCR、Excel“条款要点”、百科、培训网站、商业法规库及第三方转载只能辅助定位；不能单独替代正式法规原文。官方页面只有题录而没有可核验条文时，也不能据此编造条款。

证据不足就保持候选/待核实，不编造；但必须继续按“本地原件 → 官方互联网原文”的路线主动补证，而不是因为本地库缺失直接停止。

## 六、数量必须按层次报告

当前知识源/库存与正式发布不是同一个数字：

- knowledge：103 个法规身份、107 个法规版本、2,940 条条款、2,015 个隐患实体（1,502 active / 421 proposed / 92 superseded）、1,645 个关联；
- 新版 Excel 目标集：1,929 个唯一隐患 ID（621 条修订、1,308 条保留）；
- 当前正式发布：1,502 / 59 / 1,276 / 1,621（隐患 / 实际引用法规版本 / 条款 / 关联）；
- 当前 proposed：421，仅后台；
- publication：69 个 canonical 来源关系（11 full_text + 58 link_only），不等于正式法规数；
- 私有全文当前已核：171 份全文、215,464 个检索段落；更细的母库审计状态见 `docs/PROJECT_STATE.md`。

旧批次“1250”、Excel“1929”、knowledge“2014”、publication 目录数、旧法规卡“223”不能互相当成同一种“数据库总数”。

## 七、为什么 Git 不再保存 `source/releases/current/`

以前把生成包提交进仓库，会出现“knowledge 已经更新，current 还是上一次生成”的双版本问题。现在：

- `source/releases/current/`、`source/releases/site-selection.json`、`*.review.json` 均为生成物并加入 `.gitignore`；
- GitHub Actions 每次从当前 `knowledge + source/publication + web` 重新构建并严格校验后部署；
- `tools/build_local_release.py` 每次也会先重建正式公开包，再只读组合本地 `fulltext.sqlite3`；
- 发布包不再反向成为数据源。

因此仓库只保存**权威源 + 构建规则**，不会再留一套容易过期的“current 快照”。

## 八、本地 agent 安全边界

本轮仓库整理不修改：

- `source/library/fulltext.sqlite3`；
- 私有 PDF、archive、incoming；
- OCR 和私有全文索引；
- 既有稳定 ID。

本地最终版运行：

```powershell
py -3 tools/build_local_release.py
```

它会先执行 knowledge 校验、严格 Gate、重建和验证正式公开包，然后只读使用私有 SQLite 生成 `dist/local/`。

## 九、当前主线文档

只维护以下当前文档：

- `AGENTS.md`：长期工作边界；`docs/PROJECT_STATE.md`：唯一阶段状态与恢复计划；
- `README.md`：项目入口和维护硬规则；
- `docs/ARCHITECTURE.md`：架构；
- `docs/MAINTENANCE.md`：日常维护；
- `docs/LEGAL_STATUS_POLICY.md`：效力/版本规则；
- `docs/CANDIDATE_REVIEW.md`：候选处理；
- `docs/HANDOFF.md`：人类当前交接摘要；
- `source/README.md`、`source/releases/README.md`：source 和生成发布目录说明。

当前树不再保留多个日期版 handoff、final、latest、history 或旧发布包。历史从 Git 恢复。

## 十、验证与部署

`main` 是唯一自动部署分支。核心检查：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/validate_publication_integrity.py
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
```

其中 `validate_publication_integrity.py` 是长期只读硬门禁：要求 publication 保持 knowledge canonical 1:1 身份投影，并检查全文 catalog、物理 `texts/`、全文搜索 index/gram shards 的确定性一致性与公开/私有边界。它同时运行在 Validate 和实际 Pages Build 路径；失败不得通过修改业务数据“凑绿”。

严格审计存在 release blocker 或 publication integrity 失败时，CI 必须失败。未来版本、历史版本、候选和待回绑项作为库存/backlog 管理，不得偷偷进入正式投影。

## 十一、2026-09-14 架构收口阶段改了什么（历史记录）

- 删除旧日期版交接、重复报告和临时 history 文档；
- 前台不再混排候选、零条款目录项和长技术 ID；
- 候选从正式发布数据层彻底退出，只留 knowledge 后台；
- 正式法规索引改由实际正式条款引用的 knowledge 版本生成；publication 退回来源/资料职责；
- 修正 upcoming 门禁，尚未实施版本不得支撑当前正式隐患；
- 严格审计 blocker 现在真正阻断 CI；
- 删除 Git 中旧 `source/releases/current/` 与旧 selection 快照，改为现场确定性生成；
- 本地构建同步改为先重建正式公开包，再只读组合私有全文；
- 新增根 `AGENTS.md` 作为跨聊天窗口的长期接手记忆，阶段状态已迁移至 `docs/PROJECT_STATE.md`，仅实际阶段变化时更新；
- **未修改私有法规母库、PDF、SQLite、OCR 和稳定 ID。**

以后任何影响架构、数据口径、法规归并、候选策略、发布范围、本地母库位置或停用工具的改动，都必须同步更新本 README；实际改变阶段状态或下一步的进展更新 `docs/PROJECT_STATE.md`。提交说明写清：**改了什么、为什么改、影响哪些数据、是否需要重新审核/重建。**

## 十二、隐私与许可证

GitHub 与 GitHub Pages 是公开空间。企业报告、照片、未脱敏附件、私有法规原件、SQLite、OCR 和受版权限制的标准全文不得提交。

代码采用 [MIT License](LICENSE)。
