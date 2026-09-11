# Safety Basis Chat 续接状态

> 最后更新：2026-09-10。恢复项目必须先读取本文件，并核对 GitHub `chat-v4` 真实 HEAD、`knowledge/manifest.json`、
> `docs/V4_FINAL_ACCEPTANCE_REPORT.md` 与 `source/releases/v4-candidate-20260910/release.json`。
> 真实文件状态优先于聊天历史。分支存在并发施工，写入前必须重新 fetch；**禁止 reset / force push**。

## PROJECT_STATUS

**READY_FOR_ACCEPTANCE** — Phase 16 全部验收已完成，等待用户批准是否进入 Phase 17。

当前知识树实测（`py tools/v4/sync_manifest.py` 可幂等刷新 `knowledge/manifest.json`）：

| 实体 | 数量 |
|---|---:|
| laws | 88 |
| lawVersions | 88 |
| clauses | 196 |
| hazards | 712 |
| links | 839 |
| evidence | 600 |
| requirements | 75 |
| successions | 23 |

候选发布链：**639 publishable hazards / 806 eligible links / strictBlockers 0**，`candidate=true`、`production=false`。

## 当前总目标

在保留 V3 Stable ID、法规/标准身份、版本、条款、可靠隐患、正确关联、证据、历史 release 与网站能力的前提下完成 Chat-first V4。
Phase 16 已通过，下一步是用户批准后的 Phase 17 生产切换。未经明确批准不得修改 `main` 或切换生产网站。

## 当前 Phase

Phase 16 完成，处于 `READY_FOR_ACCEPTANCE`；Phase 17 未启动。

## 当前工作分支

`chat-v4`（`main`、GitHub Pages、production 数据源、V3 SQLite 均未改动）。

## 当前真实基线

- V3 冻结基线：`source/master/safety.sqlite3`，SHA-256 `7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`，全程只读。
- 候选包：`source/releases/v4-candidate-20260910`，`sourceStateHash = 209787cacd1a7a51f15c09bbdd3a87d5783716c3bf00b0d50a20ba857de46613`；`candidate=true`、`production=false`。
- 候选包同时包含网站前端与数据投影，可直接 `py -m http.server` 起静态服务验收。
- 网站投影由 `tools/v4/build_site_data.py` 生成，已接入 CI 与双构建确定性检查。

## 本轮完成

1. **补录 6 部 V3 曾引用、V4 缺失的现行法规**，并在补录中纠正了 V3 的真实错误：
   - 工业企业总平面设计规范 GB 50187-2012：23 条条款 + 32 条 direct 关联。
     V3 的 24 条里 12 条与现行版本不符、4 条条号错挂（2.0.3→3.0.3、4.2.7→5.2.7、4.2.8→5.2.8、6.4.1→6.4.12），
     人行道宽度沿用了已废止版本的 0.75m（现行为 1.0m）。
   - 江苏省工业企业安全生产风险报告规定（省政府令第140号）：6 条 + 12 条 direct。
     V3 把 5 条隐患挂在第三十四条**罚则**上，已改挂第七/十二/十六/十七/十八条等行为规范条款。
   - 特种作业人员安全技术培训考核管理规定（应急管理部令第19号）、特种作业目录（应急〔2026〕45号）。
   - 建设项目安全设施"三同时"监督管理办法（安监总局令第36号）、南京市电动自行车消防安全管理办法。
2. **补齐 Phase 11 网站适配层**：此前发布包用自己的数据格式，与网站前端所需的分片 + `basisRefs` 结构不通，详情页无法显示条款原文。`tools/v4/build_site_data.py` 现在从 `knowledge/` 生成公开投影，浏览器实测通过（搜索、场所筛选、隐患详情的条款原文、法规库反查关联隐患、PWA 注册）。
3. **数据质量清理**：合并完全重复隐患、清理挂在已合并隐患上的悬挂关联与中间态说明、把义务复述型标题改写为现场缺陷事实、证据等级归一、来源补齐、删除重复孤儿条款。
4. **V3 → V4 差异验收**：报告改为运行时生成；V3 已核验的 662 条隐患在 V4 的覆盖率为 **100%**，未发现误删。
5. **门禁加固**：`rebind` 支持同一哈希多处替换、`check_review_binding` 恢复真实失败语义、`gate_link` 检查目标隐患状态、`gate_clause` 检查条款效力。
6. **验收文档一致性复核**：发现 `docs/V4_FINAL_ACCEPTANCE_REPORT.md` 顶部保留了旧 `sourceStateHash` 前缀 `57b565b08f94bb78`，而当前候选包 `release.json` 的真实值为 `209787ca...`。已确认 `build_release.py` 的该哈希仅由 `knowledge/**/*.json` 计算，因此属于报告陈旧值而非候选包异常；已在提交 `0a12b22e89a01f20abd64337037e6c51132b1353` 修正验收报告，并将完整当前哈希记录到本文件。

## 本轮修改文件

- 工具：`tools/v4/{build_site_data.py(新), build_release.py, rebind.py, scan_quality_v4.py, diff_v3_v4.py, sync_manifest.py}`
- 门禁与 CI：`.github/workflows/v4-final-acceptance.yml`
- 知识：`knowledge/` 下 laws / law-versions / clauses / links / evidence / hazards / reviews 的相应实体
- 文档：`docs/V4_FINAL_ACCEPTANCE_REPORT.md`、`docs/V3_V4_DIFF_REPORT.md`、`docs/CHAT_HANDOFF.md`、`docs/reviews/H_1F19FA1B...{DATA_QUALITY_REVIEW,CLAUSE_VERIFICATION}_20260910.md`
- 测试：`tests/test_master.py`（修正 Windows 下无法删除被占用目录导致的既有失败）

## 本轮校验

- `validate_all.py` 六项全 PASS（check_catalogue / check_requirements / check_review_binding / scan_evidence_exact / scan_quality / version_impact），BLOCKING failures: none。
- `gate_v4.py` 六阶段全 PASS；`strict_release_audit.py`：`strictVerdict=PASS`、`blockerCount=0`。
- 搜索回归 20/20；双构建产物逐字节一致；隐私公开投影扫描 723 个文件零命中。
- 单元测试 135 项全部通过。
- 本轮额外核对：`release.json` 与最终验收报告的 `sourceStateHash` 已一致。

## 当前项目状态

- 可发布隐患 640 / 712；合格关联 799 / 827（verified 799 / rejected 21 / superseded 7 / pending 0）。
- 不可发布的 72 条 = 71 条 `superseded`（已合并或已拆分）+ 1 条 `H_1F19FA1B951D46C1971E9B59B4`。

## 未完成事项

1. **两条隐患维持不发布**（描述本身不成立，不强行补依据）：
   - `H_1F19FA1B951D46C1971E9B59B4`（门窗未朝外开启）——门与窗混指、场景不明；
   - `H_3A5DEC6C74244A949CE3BC9A42`（空压机房配电柜柜门未保持常闭）——无适用于所有工业企业的强制条款。
   因此 `activeHazardsWithoutQualifyingLink = 2` 是**有意保留**，不是遗漏。
2. **19 条隐患标题仍是法条原文照抄**（如"起重机械有下列情形之一仍继续使用的,,未判定为重大事故隐患。a)未经首次检验。b)…"），
   现场人员难以理解，应改写为现场事实表述；不影响发布合规性，可独立成批处理。
3. 法规全文视图（`library.html`）在候选包内可用，但 `data/fulltext/` 尚未投影，待与版权边界一并确定。
4. Phase 17 生产切换未启动，部署方式（GitHub Pages 分支／目录、`main` 合并方式）待用户确定。

## 下一轮第一步

等待用户对 `READY_FOR_ACCEPTANCE` 的复核结论。若批准，再规划 Phase 17：确认最终发布的具体 Release、`main` 合并方式与 GitHub Pages 切换步骤；未获批准前不做任何生产侧改动。

## 法规/标准待核验队列

- `GB/T 12801-2008` 有效期至 **2026-09-30**，新版 `GB 12801-2025《生产过程安全基本要求》` 自 2026-10-01 实施，届时应切换引用（已在条款审核记录与相关隐患说明中登记）。
- 18 条已被替代的历史 `lawVersion` 无官方在线来源，如实留空，不编造链接。
- 7 对"整条/分款"并存的条款属粒度设计选择，不做高风险合并。

## 风险 / 阻塞

- 本分支存在并发写入者，**每次写入前必须重新 fetch**；出现冲突时人工合并，禁止 reset / force push。
- 候选包内 `data/_internal/` 为内部审计视图（含未通过门禁的全量隐患），若将来部署该包，必须排除该目录。

## 用户待决策事项

1. 是否批准进入 Phase 17（合并 `main`、切换生产网站、更新 GitHub Pages）。
2. `H_1F19FA1B951D46C1971E9B59B4` 能否从原始报告恢复场景；若不能，是否长期保留为待核验实体。
3. `data/fulltext/`（法规全文视图）的公开范围与版权边界。

## 明确禁止事项

未经用户明确批准：不进入 Phase 17、不修改 `main`、不切换生产网站、不改动 V3 SQLite 冻结基线。
