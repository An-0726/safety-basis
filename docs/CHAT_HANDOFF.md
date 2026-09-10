# Safety Basis Chat 续接状态

> 最后更新：2026-09-10（复合 Hazard 拆分真实状态校正轮）。恢复项目时必须先读取本文件、`knowledge/manifest.json` 与 `chat-v4` 当前真实 HEAD；如有冲突，以 GitHub / Google Drive 真实文件状态为准。

## PROJECT_STATUS

ACTIVE

## 当前总目标

在保留 V3 有价值数据、Stable ID、法规版本链、历史审计资产和现有网站能力的基础上，完成 V4 / Chat-first 安全隐患整改依据知识库与候选网站；在用户明确批准前不得修改 `main`、不得切换 production 或 GitHub Pages 数据源。

## 当前 Phase

最终验收与遗留项收口阶段。当前重点不是继续 V3→V4 基础迁移，而是校正并发施工后的真实状态、消除严格发布审计阻断项、补齐 backfill link、校准 Requirement 层、完成剩余法规/标准与 merge 语义验收。

## 当前工作分支

`chat-v4`

## 当前真实基线

### GitHub

- 2026-09-10 本轮开始真实 HEAD：`2536aa470333d620a729b253a8dfec4df23bf6c7`。
- `497c413a751e6ca63de075f171a8612b1f976075`：已完成 32 条 pending link 复核与 21 个 composite hazard 拆分；21 个父 hazard -> 50 个单一义务子 hazard；26 link verified、2 rejected、4 保持 pending。
- `2536aa470333d620a729b253a8dfec4df23bf6c7`：对 merge/split lifecycle 变更后的 89 个 hazard content review hash 重绑；66 个 superseded hazard（45 merge + 21 split parent）保留历史状态，23 个 active hazard 的 stale hash 已修复。
- 本轮新增文档提交：`470fa6999b60eee4ae229ea99564ab293a0b3776`，将 `docs/V4_HAZARD_SPLIT_TASKS.md` 从“待施工登记”改为“已完成验收清单”。
- 下一轮仍必须重新读取 `chat-v4` 获取最终真实 HEAD；禁止把上述提交号当成静态最终状态。

### Google Drive

- 工作目录 `ESH_Codex/work/safety-basis` 可正常访问，真实目录仍包含 `.git`、`data`、`docs`、`source`、`tests`、`tools`、`content` 等工作树。
- 本轮没有覆盖或修改 Drive 工作目录中的任何正式文件。
- V3 冻结 SQLite 继续沿用已确认 SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`；本轮未重新下载/重算 hash。

### knowledge / manifest

`knowledge/manifest.json` 当前仍写：laws 68、lawVersions 68、clauses 76、requirements 75、hazards 662、links 181、evidence 552、successions 22；其中 **hazards=662 已被实际 split 提交超越**。

根据提交链的可核实净变化：原 662 个 hazard 文件 + 50 个新 child hazard，父 hazard 不删除而改为 superseded，因此当前实体文件总数应为 **712**。在 `sync_manifest.py` 对当前 HEAD 做真实文件统计前，不把该推导值冒充脚本最终统计；下一轮优先执行 manifest 同步并回读校验。

Link review 真实状态根据 `497c413...` 对旧 32 pending 的完整处理应由旧 128/21/32 更新为：
- verified：154
- rejected：23
- pending：4
- 合计：181

下一轮必须用实际 review 文件统计再次校验这组数字，再写入 manifest / candidate release。

## Candidate release

`source/releases/v4-candidate-20260910/` 当前 `release.json` 仍是 split 前旧快照：
- hazards：662
- reviewStatsByLink：128 verified / 21 rejected / 32 pending
- publishable：113

因此该 candidate 已明确 **stale（滞后）**，不能作为当前真实知识状态的发布验收依据。必须在 manifest 同步后重新构建 candidate，并重新执行 validator / gate / strict release audit。

production 未切换。

## 严格发布审计

上一轮记录的 strictVerdict=BLOCK（157 blockers, 1 warning）已经被随后 split/hash-rebind 施工部分改变，不能继续当作当前最终数字。`2536aa4...` 已消除 active hazard 的 stale content review hash；拆分同时改变 hazard/link 绑定，因此必须在最新 HEAD 上重新跑严格审计。

## 本轮完成

1. 按 HEAD-first 原则恢复真实现场，确认 handoff 与实际 `chat-v4` 已发生偏差。
2. 验证 `497c413...` 已完成 21/21 composite hazard 拆分：50 child hazard、21 parent superseded、26 link verified、2 rejected、4 pending。
3. 验证 `2536aa4...` 已完成 merge/split 后 89 个 hazard review hash 重绑，active hazard 不再存在 stale review hash。
4. 回读首个拆分父实体 `H_0AB8998CB24041C894BB326A69`、两个 child hazard 以及 `K_f0ef428ae23fcba6deb9f379`，确认父子追溯、link 重绑、review decision 均实际落盘。
5. 更新 `docs/V4_HAZARD_SPLIT_TASKS.md`：明确 21 项全部完成，该文档改为验收清单而非待办队列。
6. 核对 Drive 工作目录可访问且工作树仍在；未写入 Drive、未触碰冻结 SQLite。
7. 识别并记录 `knowledge/manifest.json` 与 candidate release 已因并发 split 施工滞后。

## 本轮修改文件

- `docs/V4_HAZARD_SPLIT_TASKS.md`
- `docs/CHAT_HANDOFF.md`

未修改：
- `main`
- production / GitHub Pages 数据源
- V3 SQLite / fulltext
- 任何现有 law / clause / hazard / link 实体数据
- candidate release 内容

## 本轮校验

- `chat-v4` 开工 HEAD 回读：通过。
- `497c413...` commit diff / message 回读：通过，明确 21 composite -> 50 child、32 pending -> 26 verified + 2 rejected + 4 pending。
- `2536aa4...` commit 回读：通过，明确 89 hazard review hash rebind，active stale hazard review hash=0。
- 首个拆分案例父 hazard / 两个 child / link / link review 回读：通过。
- Drive `safety-basis` 根目录回读：通过，源码与 source/tests/tools 等结构仍存在。
- candidate `release.json` 回读：确认仍是 hazards=662、link review=128/21/32 的旧快照，已判定需要重建。

## 当前项目状态

- 21/21 composite hazard 拆分：**完成**。
- 32 条原 pending link：已处理为 26 verified / 2 rejected / 4 pending。
- 当前剩余 pending link：**4 条**，仍需按 review reason 补证，禁止强行 verified。
- split 新增 child hazard：50。
- manifest：**已知滞后，待同步**。
- candidate release：**已知滞后，待重建**。
- Requirement 层：75 条草案仍需逐条校准。
- 20 条 V3 verified backfill hazard：仍需建立可靠新 link。
- 45 组 merge 候选已经发生实际 merge 施工迹象（HEAD rebind 记录显示 45 merged parent），但 `docs/V4_MERGE_CANDIDATES.md` 是否已全部验收闭环需下一轮读取真实文件确认，禁止仅凭旧 handoff 继续重复 merge。

## 未完成事项

1. 用当前 HEAD 真实文件统计同步 `knowledge/manifest.json`；确认 hazards、active/superseded、link review、evidence 等最终数量。
2. 基于同步后的 manifest 重新生成 `v4-candidate-20260910` 或新的候选 release，并重新跑 validator / gate / strict release audit。
3. 处理剩余 4 条 pending link 的证据补强与专业判定。
4. 为 20 条 V3 verified backfill hazard 建立可靠新 link 并逐条 review。
5. Requirement 层 75 条逐条校准 verified + checkItems，禁止批量强行通过。
6. 核对 45 组 merge candidate 的真实施工与验收状态，避免重复 merge。
7. 工贸企业重大事故隐患判定标准新旧版本状态核验入库。
8. GB 50140-2005 / GB 50016-2014 与 GB 55036/55037-2022 partial replacement 复核。
9. 危化品条例处置关系最终验收留存。

## 下一轮第一步

**重新读取 `chat-v4` HEAD 后，运行/复核 `tools/v4/sync_manifest.py` 对当前真实 `knowledge/` 文件做全量计数，先把 `knowledge/manifest.json` 从 split 前状态同步到真实状态；随后回读 manifest 与 candidate 差异，确认是否可以安全重建候选 release。**

## 后续任务

1. manifest 同步 + candidate 重建 + strict audit 重跑。
2. 剩余 4 条 pending link 补证。
3. 20 条 backfill hazard 新 link。
4. Requirement 校准。
5. merge candidate 闭环确认。
6. 剩余法规/标准时效和 succession 验收。
7. 最终 release 对比与生产切换准备。

## 法规/标准待核验队列

- 工贸企业重大事故隐患判定标准新旧版本状态：未完成最终入库核验。
- 剩余 4 条 pending link 涉及专项技术标准/条款证据：按各 review reason 补证。
- GB 50140-2005 / GB 50016-2014 与 GB 55036/55037-2022 partial replacement：待最终复核。
- 危化品条例 partially_replaces 关系：已有核验结论，待最终验收留存。

## 风险 / 阻塞

- 无需要用户立即决策的硬阻塞。
- 并发施工仍活跃：任何写入前必须重读 `chat-v4` HEAD；只允许 non-force fast-forward。
- manifest 与 candidate 当前明确滞后；在重建前不得把旧 release 数字作为当前事实。
- split/merge 施工会改变实体总数、lifecycle 和 review hash；所有统计必须以最新真实文件为准。
- pending 不得为追求完成率强行改 verified。

## 用户待决策事项

仅 Phase 17 生产切换仍等待用户明确批准；当前不授权修改 `main`、GitHub Pages 数据源或 production selection。

## 明确禁止事项

- 不修改 `main`。
- 不切换 production。
- 不切换 GitHub Pages 数据源。
- 不覆盖或修改 V3 冻结 SQLite。
- 不 force push / force update ref。
- 不恢复历史 r8 错误关联。
- 不因关键词相似、任务完成率或批量规则把 pending 强行改为 verified。
- 不使用旧 candidate / 旧 handoff 覆盖更新的真实成果。
