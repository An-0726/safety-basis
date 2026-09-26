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

<!-- CURRENT_STATE_BEGIN -->
## 当前统一状态（2026-09-26，逐项审核及本地补查继续）

更新时间：2026-09-26T19:32:25+08:00。当前知识源2127隐患：1667正式、349候选、111历史归并；接手以来新建隐患实体0。编号、归并指向及来源保留。

已上线锚点：PR91合并提交1ac023a1fd6ddd91a0155de33bce1ba05efe24f1，主分支流程36237843174、36237843155成功；19:10:22逐个核官网隐患与条款分片、文件哈希和候选隔离，正式1670条，发布哈希5ffb702771472e7006f06c7bd999b070c137720ca655e7deeb8c6a50f6eb9ed6。证据见docs/ONLINE_VERIFY_20260926_FIRE.json。消防原文纠错、5组归并及20项依据不足撤回已部署。

本批待部署：3组同地区责任制正式实体归并、1个风险档案候选归并；补全安全费用提取使用条文，风险管理责任不泛化为全部安全职责。江苏风险条例59条引文逐条对照人大全文，23条有实质纠正；修正5个风险管理条目的错误场景或整改表述。风险档案使用2026官方完整引文补证，工业企业范围不扩大至全行业。没有新增隐患实体。

原43来源782行基线不变：原45行审核、12行排除，725行续审；725均有初审意见，但初审不等于已核准新增。本次累计339行、408项细分处置，剩余386行尚未进入进一步细审；已细审项含事实或依据待核，不称全部事实确认。历史重合128行指向79个当时当前实体，仅为局部重合结果。另12份来源141行另计，仍需最终适用性核查。

本地来源候选已扩大至1703份Office和234份PDF；文件数不是独立项目数。1697份Office文字可提取，1份损坏XML恢复文字待原件核查，4份为空文件，1份为旧版Word误标后缀；483份包含2026字样不等于483个2026项目。扫描件印刷文字用于定位，手写与签章不以OCR结果作确认。正式版本筛选和全盘补查未完成。

本批55项数据管线和71项前端测试通过；知识一致性检查通过，严格检查0阻断、144库存告警。正式包本地生成1667项，349候选未公开；远端合并、部署及线上核验待完成。企业问题原文、PDF、扫描文字及数据库保留本地，不提交公网。
<!-- CURRENT_STATE_END -->

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

当前正式依据按发布包 `asOf` 日期判断。由于本库用于中国境内法规、标准和地方规则，CI/正式发布统一以 `Asia/Shanghai`（中国标准时间）取得 `asOf` 日历日期，不使用 UTC 日期，以避免实施日当天出现最多 8 小时的效力判断滞后。法规版本只有同时满足以下条件，才能支撑当前隐患：

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

当前数量统一取本页“当前统一状态”与 `knowledge/manifest.json`。知识库库存、通过 Gate 的公开包、原始来源记录、规范实体和历史目标集是不同统计口径，不得混用。历史 1,929 项目标集（621 项修订、1,308 项保留）与历史 16 份检查表/134项来源映射不等于本次2026全量任务已经完成。

历史阶段数字仅代表明确标注的当时结果；当前 `main`、manifest、对应CI产物与实际线上核验共同确定现状。本次仍有725条原始行待逐条审核，不能以已保存台账或算法候选匹配冒充完成去重。

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
node --test tests/*.test.mjs
py -3 -m unittest discover -s tools/pipeline/tests -v
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/validate_publication_integrity.py
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
```

CI 在 `build` job 的数据验证和构建前执行 Node 22 前端测试与 Python pipeline 测试；本地阶段 4 的审查包不等于线上部署结果。

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
