# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（Requirement 校准批次 001）。恢复项目时必须先读取本文件、`knowledge/manifest.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub / Google Drive 真实文件状态为准。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

Phase 22 / 最终验收与遗留项收口。基础迁移、link applicability 复核、复合 Hazard 拆分、backfill、merge 验收和严格发布审计主链已基本闭合；当前主要施工目标为 Requirement 层逐条专业校准，随后重建 candidate release 并重新执行 validator / gate / strict audit，完成最终 V3→V4 验收准备。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub

- 本轮开工真实 HEAD：`9e612a911082d6a9b81780810d1ff1afda13b5ba`。
- `27c48efac9036b67045457e29ffc99554a3bf21a` 已补齐 TSG 81-2022 law/lawVersion review、同步 manifest、重建 candidate；当时 strict audit 为 PASS，releaseBlockers=0，gate 六阶段全部 PASS。
- `9e612a911082d6a9b81780810d1ff1afda13b5ba` 将 `docs/V4_STRICT_AUDIT.md` 同步为上述 0 blocker / PASS 结果。
- 本轮 Requirement 校准数据提交依次为：
  - `638a7b67f4e708f7345b89de0e29c7d6ed8c7ea7` — RQ_0E0CB15C42FF3DEB990C3D
  - `d1b092bc8de5b0b3d0a3f096406f34758e73eed5` — RQ_0F890599AA1DAAF8957139
  - `471fb532dba2d136c3c21625555a660cd5939d57` — RQ_2C292FBE3E8AFC81EF4DE8
  - `c7531cdbc6cc45d6c18501aaf22f4801e2007535` — RQ_45B4C2AF1539A29CBA3872
  - `a69f26bd5fb0bbdd272562634314ee516d513294` — RQ_7A042553C5343F33D3F8C4
  - `1154f28c1859137cf9f277a87c364d809b365b0f` — RQ_918B9954F531261FFCDA8F
  - `a5de845fbda7c49c8624a1fd0b6814b0c27fd7fc` — RQ_991FD2993E54A823CB2E46
- 本 handoff 提交位于上述数据提交之后；下一轮仍必须重新读取 `chat-v4` 获取真实 HEAD。

### Google Drive

- `ESH_Codex/work/safety-basis` 可访问，根目录仍包含 `.git`、`data`、`docs`、`source`、`tests`、`tools`、`content` 等工作树。
- `source` 下已确认 `master`、`releases`、`library`、`exchange`、`staging`、`archive`、`mappings`、`proposals` 等目录存在。
- 本轮 `source/master` 子项枚举返回空结果，视为 Drive 接口可见性/索引限制，不能据此判断文件删除。
- V3 冻结 SQLite 继续沿用已确认 SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`；本轮未重新下载或重算 hash。
- 本轮未写入 Google Drive。

### knowledge / manifest

`knowledge/manifest.json` 当前 counts：laws 74、lawVersions 74、clauses 85、requirements 75、hazards 712、links 209、evidence 567、successions 23；link review 为 186 verified / 23 rejected / 0 pending。

manifest 的实体数量仍正确，但 scope 中“75 requirement drafts”表述已因 Requirement 校准推进而滞后；不要把该文字当作当前全部 Requirement 都未校准的事实。下一次 sync/build 应同步修正描述或批次元数据。

## Candidate release

当前候选包：`source/releases/v4-candidate-20260910/`。

在本轮 Requirement 修改之前，其 `release.json` 状态为：sourceStateHash=`2ddf4875c0870dca121737404364994becb710db6f184d75d3a3012b8ea5078e`；sourceCounts laws 74 / law_versions 74 / clauses 85 / hazards 712 / links 209 / requirements 75；links 186 verified / 23 rejected / 0 pending；eligibleHazards 162；eligibleLinks 186；production=false。

**注意：本轮已修改 7 个 Requirement 实体，因此上述 candidate 现在是校准前快照。即使实体数量未变化，也必须在后续校准批次收口后重新 build 并重跑 requirement validator、V4 gate 与 strict audit，不能直接沿用校准前 PASS 作为最新结论。**

## 本轮完成

1. 按 HEAD-first 原则恢复真实现场，确认旧 handoff 的“下一轮第一步”已经过时，避免重复执行 manifest 同步、candidate 重建和 pending link 清零。
2. 确认最新严格发布审计在本轮开工基线已经达到 releaseBlockers=0 / PASS，candidate 当时 gate 六阶段全部 PASS。
3. 核对 Requirement 架构规则：Requirement 必须从 Clause 提炼可检查、可判断的原子义务；verified Requirement 不自动代表 Link verified；不得跨法规扩张 sourceQuote。
4. 发现并逐条校准 7 个真实 pending Requirement，全部从 `checkItems=[]` / `reviewStatus=pending` 改为具有专业检查要点的 `reviewStatus=verified`：
   - RQ_0E0CB15C42FF3DEB990C3D：主要负责人建立并落实双重预防机制、督促检查并及时消除隐患。
   - RQ_0F890599AA1DAAF8957139：危化品生产、储存企业每 3 年一次安全评价。
   - RQ_2C292FBE3E8AFC81EF4DE8：危化品储存单位出入库核查、登记制度（条例）。
   - RQ_45B4C2AF1539A29CBA3872：餐饮等行业使用燃气安装并正常使用可燃气体报警装置。
   - RQ_7A042553C5343F33D3F8C4：不得占用、堵塞、封闭疏散通道、安全出口、消防车通道。
   - RQ_918B9954F531261FFCDA8F：电焊、气焊等火灾危险作业人员及自动消防系统操作人员持证上岗并遵守操作规程。
   - RQ_991FD2993E54A823CB2E46：危化品储存单位出入库核查、登记制度（法律）。
5. 每条均设置 reviewer=`ChatGPT`、reviewedAt、reviewReason，并按 `tools/v4/canonical.py` 规则重算 canonicalHash。
6. 明确排除跨条款扩张：未把燃气报警联动切断/安装高度/校准周期、动火证件具体名称/培训学时、危化品登记字段/保存期限/审批流程等未出现在对应 sourceQuote 的要求强行并入。
7. 回读本批首条和末条 Requirement，确认 checkItems、reviewStatus、reviewReason 与 canonicalHash 已实际落盘。
8. 核对 Google Drive 工作目录结构仍存在；未修改 Drive、V3 冻结库、main 或 production。

## 本轮修改文件

- `knowledge/requirements/RQ_0E0CB15C42FF3DEB990C3D.json`
- `knowledge/requirements/RQ_0F890599AA1DAAF8957139.json`
- `knowledge/requirements/RQ_2C292FBE3E8AFC81EF4DE8.json`
- `knowledge/requirements/RQ_45B4C2AF1539A29CBA3872.json`
- `knowledge/requirements/RQ_7A042553C5343F33D3F8C4.json`
- `knowledge/requirements/RQ_918B9954F531261FFCDA8F.json`
- `knowledge/requirements/RQ_991FD2993E54A823CB2E46.json`
- `docs/CHAT_HANDOFF.md`

未修改：
- `main`
- production / GitHub Pages 数据源
- V3 SQLite / fulltext
- law / lawVersion / clause / hazard / link 实体
- 本轮开始时已有 candidate release 文件

## 本轮校验

- `chat-v4` 开工 HEAD 回读：通过。
- candidate `release.json` 回读：通过，确认本轮开工前为 74/74/85/712/209/75，186 verified / 23 rejected / 0 pending，production=false。
- 7 个目标 Requirement 开工时均通过直接回读确认处于 pending 且缺少 checkItems；本轮没有凭完成率批量通过。
- `tools/v4/canonical.py` 规则回读：通过；canonicalHash 不参与自身 hash，使用规范化 JSON + SHA-256。
- RQ_0E0CB15C42FF3DEB990C3D 写后回读：通过，verified + 3 条 checkItems 已落盘。
- RQ_991FD2993E54A823CB2E46 写后回读：通过，verified + 2 条 checkItems 已落盘。
- GitHub 远端连续写入均成功；本地 `git clone` 因当前运行环境 DNS 无法解析 github.com 而失败，因此本轮未在本地执行全仓 `check_requirements.py` / `gate_v4.py` / strict audit。该限制不影响远端已保存数据，但要求后续 candidate 重建前补跑全量校验。

## 当前项目状态

- 45 组 merge：已验收闭环。
- 21 个 composite hazard：已拆分完成。
- V3 verified backfill：20/20 已补齐并进入可发布链。
- Link review：186 verified / 23 rejected / 0 pending。
- 严格发布审计：本轮开工基线为 PASS / 0 blockers；因本轮 Requirement 内容变化，需在后续 rebuild 后重新确认最新结论。
- Requirement：总量 75；已有一部分在此前批次完成 verified，本轮再完成 7 条。**本轮没有完成全量状态枚举，因此不得宣称当前 verified/pending 总数。**
- 当前已确认下一条 pending Requirement：`RQ_3E61FC35056F5D4B84AF45`，来源条款要求贮存设施所有者或运营者配备突发环境事件应急人员、装备和物资，并设置应急照明系统。

## 未完成事项

1. 继续逐条校准剩余 pending Requirement，补齐 checkItems、scope、reviewReason 并重算 canonicalHash；不得批量强行 verified。
2. 校准到可收口批次后，用真实工作树执行 `tools/v4/check_requirements.py` 全量校验。
3. 同步 `knowledge/manifest.json` 中 Requirement 校准进度/描述，保持 counts 与 scope 一致。
4. 重新运行 `tools/v4/build_release.py` 重建 candidate release，并再次执行 V4 gate 与 strict audit。
5. 在最新 candidate 上完成最终 V3→V4 差异验收、搜索/页面/隐私/发布包验收和生产切换准备。
6. 生产切换仍必须等待用户明确批准。

## 下一轮第一步

**重新读取 `chat-v4` HEAD 后，校准已确认 pending 的 `RQ_3E61FC35056F5D4B84AF45`：仅依据其 `sourceQuote` 提炼应急人员、装备和物资及应急照明系统的可检查 `checkItems`，同时复核其 clauseId/lawVersionId 关联；完成并保存后继续按稳定顺序寻找下一条 pending Requirement。**

## 后续任务

1. Requirement 层剩余 pending 逐条专业校准。
2. Requirement 全量 validator 校验。
3. manifest 校准状态同步。
4. candidate rebuild + gate + strict audit。
5. 最终 V3→V4 验收与生产切换准备。

## 法规/标准待核验队列

- 当前 Link applicability pending：0。
- 工贸企业重大事故隐患判定标准新旧关系：已核验。
- GB 50140 / GB 50016 与 GB 55036 / GB 55037 partial replacement：已核验。
- 危化品条例与危化品安全法 partially_replaces：已验收留存。
- Requirement 校准过程中如发现 sourceQuote 或法规版本本身存在疑点，转入法规/标准核验队列，不得用 Requirement 文本掩盖上游证据问题。

## 风险 / 阻塞

- 无需要用户立即决策的硬阻塞。
- 并发施工可能继续发生；任何下一轮写入前必须重读 `chat-v4` HEAD，禁止用旧 handoff 覆盖更新成果。
- candidate 已因本轮 Requirement 内容变化成为校准前快照，后续必须 rebuild 后才能重新声称最新 gate/strict audit PASS。
- 当前运行环境普通 Git 网络通道存在 DNS 解析失败；GitHub 连接器读写正常。若下轮仍无法 clone，应继续通过连接器处理可安全工作，并把全仓脚本校验留到可运行环境，不得伪造校验结果。
- pending Requirement 不得因数量压力直接改 verified；checkItems 不得跨法规、跨条款引入额外硬指标。

## 用户待决策事项

仅最终 production 切换需要用户明确批准。当前尚处 Requirement 校准与候选包重新验收阶段，不应提前请求切换生产。

## 明确禁止事项

- 不修改 `main`。
- 不切换 production。
- 不切换 GitHub Pages 数据源。
- 不覆盖或修改 V3 冻结 SQLite / fulltext。
- 不 force push / force update ref。
- 不恢复历史 r8 错误关联。
- 不因关键词相似、任务完成率或批量规则把 pending 强行改为 verified。
- 不把其他法规、其他条款中的义务混入当前 Requirement 的 `checkItems`。
- 不使用旧 candidate / 旧 handoff 覆盖更新的真实成果。
