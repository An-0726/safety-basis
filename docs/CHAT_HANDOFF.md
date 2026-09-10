# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（Requirement 专业校准批次 002：新增完成 4 条 verified Requirement）。恢复项目时必须先读取本文件、`knowledge/manifest.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub / Google Drive 真实文件状态为准。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

Phase 22 / 最终验收与遗留项收口。基础迁移、link applicability 复核、复合 Hazard 拆分、V3 verified backfill、merge 验收和严格发布审计主链已基本闭合。当前主要施工目标为 Requirement 层逐条专业校准；校准到可收口批次后，同步 manifest、重建 candidate release，并重新执行 validator / gate / strict audit，完成最终 V3→V4 验收准备。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub

- 本轮开工读取到的真实 HEAD：`a2aab65fe375730de62626c9edd7d8d5c11529fb`。
- 该 HEAD 晚于上一版 handoff，commit message 为 `link-backfill: 29 new verified links (dust collection/electrical wiring/fire safety/safety signs/pipeline marking/extinguisher inspection/coating direct); strict PASS`。因此上一版 handoff、`knowledge/manifest.json` 和既有 candidate 中的 332 links 统计已经滞后，不能继续视为当前真实 link 总量。
- 本轮 Requirement 校准数据提交：
  - `17f1371580690c423349373f3d4a005ebcfd0afe` — `RQ_3E61FC35056F5D4B84AF45`
  - `b4427ff782663f35cdcf511b65427fc545cf4344` — `RQ_621590EF88B8FC87CC1CB0`
  - `b6b46946a51c50448b96be20916b3f04662460e0` — `RQ_7207BD4D2D1EB0ADEBF4CF`
  - `454a24ab0622d945c17c017c9a889f4dfc64bd18` — `RQ_8F2BF75246AB87FEBDB0B4`
- 本 handoff 提交位于上述数据提交之后；下一轮仍必须重新读取 `chat-v4` 获取真实最终 HEAD，禁止把本文记录的 SHA 当作永远不变的分支状态。

### Google Drive

- `ESH_Codex/work/safety-basis` 对应 `safety-basis` 工作目录本轮重新确认可访问。
- 本轮未写入 Google Drive，也未覆盖任何 Drive 成果。
- V3 冻结 SQLite 继续沿用已确认 SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`；本轮未重新下载或重算 hash。
- fulltext、历史 release、exchange、proposals 等仍按既有冻结/历史资产规则处理，不因本轮 Requirement 校准而覆盖。

### knowledge / manifest

当前 `knowledge/manifest.json` 文件本身仍记录：laws 74、lawVersions 74、clauses 85、requirements 75、hazards 712、links 332、evidence 567、successions 23；scope 中仍写 332 links / 309 verified / 23 rejected / 0 pending 和 `75 requirement drafts`。

该 manifest 现在**明确滞后**：

1. `a2aab65fe375730de62626c9edd7d8d5c11529fb` 在其后新增 29 条 verified links；
2. 本轮又继续把 4 条 pending Requirement 校准为 verified；
3. 因此下次不能直接按旧 manifest 数字生成 release，必须先从真实 `knowledge/` 工作树重算并同步。

不得只用“332+29”的推算数字覆盖 manifest；应通过项目同步脚本或对实际目录/实体状态的完整枚举得出真实统计。

## Candidate release

现有候选包仍为 `source/releases/v4-candidate-20260910/`。

其此前 strict audit / gate PASS 只代表生成当时的知识状态。由于后续已经发生 29 条 link backfill 和 Requirement 内容校准，现有 candidate 已成为旧快照，**不得继续声称它代表当前 HEAD 的最新 PASS 结论**。

后续必须：真实工作树同步 manifest → rebuild candidate → validator → gate → strict audit → 再确认是否 PASS。

## 本轮完成

1. 按 HEAD-first 原则恢复现场，发现 `chat-v4` 已前移至 `a2aab65...`，确认旧 handoff 的基线已过时，没有使用旧状态覆盖并发成果。
2. 核对 `RQ_3E61FC35056F5D4B84AF45`：
   - 上游为 GB 18597-2023《危险废物贮存污染控制标准》11.2；Clause 与 Requirement `sourceQuote` 完全一致；LawVersion 为 active、2023-07-01 实施。
   - 将义务拆分为应急人员、应急装备和物资、应急照明系统 3 项可检查动作。
   - 未增加人员数量、物资品类/储备数量、应急照明参数等原条款未规定内容。
3. 核对 `RQ_621590EF88B8FC87CC1CB0`：
   - 上游为 GB 18597-2023 第 6.2.3 条，Clause 与 `sourceQuote` 完全一致。
   - 将义务拆分为气体收集装置、气体净化设施、排气筒高度符合 GB 16297 三项检查动作。
   - 未增加收集效率、净化工艺、排放限值或监测频次。
4. 核对 `RQ_7207BD4D2D1EB0ADEBF4CF`：
   - 上游为《安全生产法》第四十九条，Clause 与 `sourceQuote` 完全一致。
   - 将义务拆分为承包/承租安全生产统一协调管理、定期安全检查、发现问题及时督促整改 3 项检查动作。
   - 未擅自增加检查周期、台账格式或整改时限。
5. 核对 `RQ_8F2BF75246AB87FEBDB0B4`：
   - 上游为《中华人民共和国危险化学品安全法》第三十六条；Clause 与 `sourceQuote` 完全一致。
   - LawVersion 记录为 2026-05-01 施行、active；本轮另通过全国人大官方公开来源重新核实该法律已于 2025-12-27 通过并自 2026-05-01 起施行。
   - 将义务拆分为按国家/行业标准装备自动控制与安全仪表系统、建立安全风险监测预警系统、与政府有关部门互联互通三项检查动作。
   - 未自行加入 SIL 等级、具体联网接口、数据上传频次等原条款未规定指标。
6. 上述 4 条均设置 reviewer=`ChatGPT`、reviewedAt、reviewReason，并按 `tools/v4/canonical.py` 规则重算 canonicalHash。
7. Google Drive `safety-basis` 工作目录重新确认可访问；本轮未修改 Drive、V3 冻结库、main 或 production。
8. 已识别下一条真实 pending Requirement：`RQ_A81269EEB2C03BD8417C0D`，内容为危险化学品生产、储存单位作业场所通信、报警装置及保持适用状态要求。

## 本轮修改文件

- `knowledge/requirements/RQ_3E61FC35056F5D4B84AF45.json`
- `knowledge/requirements/RQ_621590EF88B8FC87CC1CB0.json`
- `knowledge/requirements/RQ_7207BD4D2D1EB0ADEBF4CF.json`
- `knowledge/requirements/RQ_8F2BF75246AB87FEBDB0B4.json`
- `docs/CHAT_HANDOFF.md`

未修改：

- `main`
- production / GitHub Pages 数据源
- V3 SQLite / fulltext
- 现有 law / lawVersion / clause / hazard / link 实体
- Google Drive 工作文件
- 现有 candidate release 文件

## 本轮校验

- `docs/CHAT_HANDOFF.md` 开工读取：完成。
- `chat-v4` 开工真实 HEAD 回读：完成，发现并正确处理 handoff 滞后。
- 4 条 Requirement 均在写前直接回读并确认确为 pending / checkItems 为空。
- 4 条 Requirement 的 `clauseId` / `lawVersionId` 上游关系均逐项核对；至少对 GB 18597-2023 两条、安法第四十九条、危化品安全法第三十六条确认 Clause 原文与 sourceQuote 一致。
- GB 18597-2023 LawVersion 回读：active、2023-07-01 生效。
- 《危险化学品安全法》LawVersion 回读并通过全国人大官方公开来源重新核验：2026-05-01 生效。
- `tools/v4/canonical.py` 规则回读：canonicalHash 不参与自身 hash，规范化 JSON 后 SHA-256。
- 4 次 GitHub 远端写入全部成功，并分别取得 commit SHA。
- 本轮结束前读取 `chat-v4`，数据提交后的 HEAD 为 `454a24ab0622d945c17c017c9a889f4dfc64bd18`。
- Google Drive `safety-basis` 目录可访问。
- 本轮没有在真实完整工作树执行 `check_requirements.py`、`build_release.py`、`gate_v4.py` 或 strict audit，因此**不得声称本轮修改后的全库 validator/gate 已 PASS**。后续 rebuild 前必须补跑。

## 当前项目状态

- PROJECT_STATUS：ACTIVE。
- 当前 Phase：22 / 最终验收与遗留项收口。
- 45 组 merge：已验收闭环。
- 21 个 composite hazard：已拆分完成。
- V3 verified backfill：已完成。
- Link applicability 历史复核主链：此前已清零 pending；但在旧 manifest 后又有 29 条新增 verified backfill link，真实 link 统计需下一次同步脚本重新枚举确认。
- Requirement：总量仍为 75。本轮新增完成 4 条专业校准；此前已有一部分 verified。**本轮仍未完成全量状态枚举，因此不得宣称当前 verified/pending 精确总数。**
- Candidate：存在，但已落后于当前 HEAD；必须重建后才可重新形成最新发布结论。
- 当前已确认下一条 pending Requirement：`RQ_A81269EEB2C03BD8417C0D`。

## 未完成事项

1. 继续逐条校准剩余 pending Requirement，补齐 checkItems、scope、reviewReason 并重算 canonicalHash；不得批量强行 verified。
2. 对 `RQ_A81269EEB2C03BD8417C0D` 先复核 `LV_HAZCHEM_REG` 当前有效性及与 2026《危险化学品安全法》的替代/并存关系，再决定 Requirement 是否继续按现行依据校准；不得因为历史 Clause 存在就跳过时效判断。
3. 校准到可收口批次后，用真实工作树执行 `tools/v4/check_requirements.py` 全量校验。
4. 从真实 `knowledge/` 状态同步 `knowledge/manifest.json`，特别纠正新增 29 links 和 Requirement 校准状态，不得凭算术推断直接覆盖。
5. 重新运行 `tools/v4/build_release.py` 生成最新 candidate，并执行 V4 gate 与 strict audit。
6. 在最新 candidate 上完成最终 V3→V4 差异验收、搜索/页面/PWA/隐私/发布包验收和生产切换准备。
7. 生产切换仍必须等待用户明确批准。

## 下一轮第一步

**重新读取 `chat-v4` 当前真实 HEAD；随后处理 `RQ_A81269EEB2C03BD8417C0D`。先读取其 Clause、`LV_HAZCHEM_REG`、相关 succession，并联网核验 2026-09-10 时点《危险化学品安全管理条例》相关条款与 2026《危险化学品安全法》的当前并存/替代关系；只有确认该条款仍可作为当前有效依据后，才按 sourceQuote 提炼“设置通信装置、设置报警装置、保持适用状态”的可检查 checkItems。若已被替代或存在适用冲突，保持 pending 并转入法规时效核验队列。**

## 后续任务

1. Requirement 层剩余 pending 逐条专业校准。
2. Requirement 全量 validator 校验。
3. manifest 真实状态同步。
4. candidate rebuild + gate + strict audit。
5. 最终 V3→V4 差异验收与生产切换准备。

## 法规/标准待核验队列

- `LV_HAZCHEM_REG` / 《危险化学品安全管理条例》与 2026《危险化学品安全法》的并存、替代及第二十一条当前适用状态：下一轮优先核验。
- 当前已确认的 2026《危险化学品安全法》第三十六条：本轮已通过全国人大官方公开来源核验现行有效。
- Requirement 校准过程中如发现 sourceQuote、法规版本或标准状态有疑点，必须转入此队列，不能用 Requirement 文本掩盖上游证据问题。

## 风险 / 阻塞

- 无需要用户立即决策的硬阻塞。
- 并发施工仍可能发生；每次写入前必须读取最新 HEAD/目标文件 SHA，禁止旧 handoff 覆盖更新成果。
- `knowledge/manifest.json` 与 candidate 已落后于真实 HEAD；在同步和 rebuild 前不得宣称其统计代表当前状态。
- 新增 29 条 link 的 commit 自述 strict PASS，但其后又发生 Requirement 内容变化；最新全库 gate / strict audit 仍需重新运行确认。
- pending Requirement 不得因数量压力直接改 verified；checkItems 不得跨法规、跨条款引入额外硬指标。
- 如法规/标准时效存在疑点，优先保持 pending 并联网核验，不得使用旧报告或历史实体状态替代当前效力判断。

## 用户待决策事项

仅最终 production 切换需要用户明确批准。当前尚处 Requirement 校准、manifest/candidate 同步与重新验收阶段，不应提前请求切换生产。

## 明确禁止事项

- 不修改 `main`。
- 不切换 production。
- 不切换 GitHub Pages 数据源。
- 不覆盖或修改 V3 冻结 SQLite / fulltext。
- 不 force push / force update ref。
- 不恢复历史 r8 错误关联。
- 不因关键词相似、任务完成率或批量规则把 pending 强行改为 verified。
- 不把其他法规、其他条款中的义务混入当前 Requirement 的 `checkItems`。
- 不未经当前时效核验继续使用有替代风险的法规/标准。
- 不使用旧 candidate / 旧 handoff / 旧 manifest 覆盖更新的真实成果。
