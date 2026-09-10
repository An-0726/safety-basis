# Safety Basis V4 最终验收与生产切换前收口框架

> 状态：`IN_PROGRESS / REVIEW_REQUIRED`
> 最后更新：2026-09-10
> 适用分支：`chat-v4`
> 当前 Phase：Phase 16
> 本文件是 Phase 16 的唯一总验收清单。各专项报告提供证据，但不得用历史数字覆盖当前真实知识树。

## 1. 目标与边界

最终验收由 ChatGPT 负责设计、执行和收口。用户在 Phase 16 不需要替代执行验收；只有全部验收完成、项目达到 `READY_FOR_ACCEPTANCE` 后，Phase 17 的正式生产切换才需要用户明确批准。

最终验收确认 V4 候选知识库和网站满足：隐患内容正确、法规版本正确、条款可靠、隐患—依据适用、Requirement 不扩张法定义务、公开投影完整、私有信息不泄漏、构建可复现、V3→V4 差异可解释。

Phase 16 禁止修改 `main`、禁止切换 GitHub Pages 正式数据源、禁止 `production=true`、禁止覆盖 V3 冻结 SQLite。

## 2. 当前真实基线

- 工作分支：`chat-v4`
- 本轮机器终审知识基线：`cd29037630c9f52688692ab3f9212bd7dc9fde9d`
- 后续仅文档提交不会改变 knowledge `sourceStateHash`；如 `knowledge/**/*.json` 再发生变化，必须重新 build/audit。
- V3 冻结 SQLite：`source/master/safety.sqlite3`
- V3 SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- V4：75 laws / 75 lawVersions / 88 clauses / 712 hazards / 735 links / 75 requirements / 567 evidence / 23 successions
- 最新 CI candidate sourceStateHash：`545a828e653fe634754d50699c7e321448dbac25396500b15c1a015f1a0e0e5f`
- candidate：true
- production：false
- publishable hazards：596
- eligible links：666
- link review：716 verified / 19 rejected；其中 666 条通过完整共享链式发布判定
- Requirement：55 verified / 20 pending

当前仓库内历史 candidate 目录不应仅靠手工修改 `release.json` 冒充最新完整候选。Phase 16 每次知识变更后的最新机器候选以对应 GitHub Actions artifact 为准；知识树最终稳定后再生成/提交新的完整 final candidate。

## 3. 总验收判定规则

状态：`PASS / WARNING / REVIEW_REQUIRED / BLOCKED / NOT_RUN`。

进入 `READY_FOR_ACCEPTANCE` 的必要条件：A–I 的所有硬检查均 PASS；仅允许存在已解释且不会影响当前公开内容真实性/安全性的 WARNING；不得存在 BLOCKED、REVIEW_REQUIRED 或关键 NOT_RUN。

## 4. A — 基线、版本与交接一致性

检查：HEAD/交接一致、manifest counts/scope、V3 冻结 SHA、candidate hash、历史报告标识、Phase 编号。

本轮已经：

- 修正 `knowledge/manifest.json` 的旧 68/662/181 scope 数字。
- 将 `migrationPhase` 从错误的 Phase 22 纠正为正式 Phase 16。
- 旧 Strict Audit 与 V3/V4 Diff 已停止冒充当前快照。
- 发现 `docs/V4_GATE_REPORT.md` 曾被并发流程写成 PowerShell/Python traceback，已恢复为当前机器终审结果。

当前状态：`PASS`（最终 handoff 仍需在每轮结束时同步最新 HEAD）。

## 5. B — 数据结构与引用完整性

最新 CI：

- catalogue validator：PASS
- Requirement validator：PASS
- dangling refs：0
- unbound link reviews：0
- stale link review hash：0
- stale hazard context hash：0
- stale clause context hash：0
- exact evidence mismatch：0

当前状态：`PASS`。

## 6. C — 法规与标准版本终审

必须按风险而非随机数量抽查：

1. 2026《危险化学品安全法》与既有危化品条例/规章的并存、替代和边界；
2. 消防法、GB 50016 及相关消防标准；
3. 低压配电、防爆电气、临时用电；
4. 粉尘防爆及除尘系统；
5. 气瓶、压力容器、起重/叉车等特种设备；
6. 职业健康与个体防护；
7. 江苏省、南京市高频地方依据；
8. 2025–2026 新实施/替代标准。

自动扫描待专业判断：

- hazard 旧标准引用候选：14
- partial-replaced standard hazard hits：12
- full-replaced standard hazard hits：0

当前状态：`REVIEW_REQUIRED`。

## 7. D — Hazard → Clause 适用性与 role 终审

当前共享链式发布结果：596 publishable hazards / 666 eligible links。

机器库存已经纠正此前“只剩 1 条未 publishable hazard”的错误说法。真实库存为：

- 49 条 active hazard 无合格 direct/fallback link；它们当前全部不进入公开 release。
- 11 条 verified supporting link；supporting 不能单独赋予发布资格。
- 67 条 superseded/merged hazard；历史保留，不进入当前公开投影。

本轮已逐条确认 `H_A73EC0543AA24DF583F70E566B` 是“未见与办公生活区域混杂布置”的正向事实而非隐患，保留 Stable ID 并转 superseded；其原 direct link 继续 rejected，不以泛化法律条款强行发布。

49 条真实队列详见 `docs/V4_FINAL_ACCEPTANCE_INVENTORY.md`。

当前状态：`REVIEW_REQUIRED`。

## 8. E — Requirement 语义终审

Requirement 不得擅自增加原 clause 没有的参数、周期、证件名称、审批流程、保存期限等。

真实状态：

- verified：55
- pending：20
- 总数：75

另有 obligation-restatement candidates：11，需检查是否把条款改写得更宽或更窄。

当前状态：`REVIEW_REQUIRED`。

## 9. F — V3 → V4 差异与回归验收

旧 `docs/V3_V4_DIFF_REPORT.md` 是中途快照，已经标记 `INTERIM — FINAL REFRESH REQUIRED`。

最终必须逐项比较 Stable ID、标题/描述/措施、law identity/version、clause locator/text、link/role、merge/split/superseded、搜索/分类/页面/PWA/隐私，并把差异归类为：

- EXPECTED_STRUCTURAL_CHANGE
- QUALITY_IMPROVEMENT
- CONTENT_CORRECTION
- INTENTIONAL_EXCLUSION
- REGRESSION
- REVIEW_REQUIRED

另有 links to merged hazards 候选：9，需判断是合法历史追溯还是残留断链风险。

当前状态：`REVIEW_REQUIRED`。

## 10. G — Release、构建与门禁验收

已新增 `.github/workflows/v4-final-acceptance.yml`，形成真正的自动闭环：

1. integrated validator；
2. build candidate；
3. 六阶段 Gate；
4. strict release audit；
5. Phase 16 acceptance inventory；
6. 20 组搜索回归；
7. candidate-only 边界；
8. 两次确定性构建 diff；
9. 验收工具不得反向修改 knowledge；
10. 上传验收 artifact。

最新知识基线 `cd290376...` 的 CI run `34453384587`：

- STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE：全部 PASS
- strict audit：PASS
- blockerCount：0
- warningCount：60
- excludedCount：105
- search regression：20/20 PASS
- deterministic build：PASS
- candidate boundary：PASS
- knowledge mutation：0
- sourceStateHash：`545a828e653fe634754d50699c7e321448dbac25396500b15c1a015f1a0e0e5f`

当前状态：`PASS`。

## 11. H — 网站、搜索、页面和 PWA 验收

搜索机器回归 20/20 已通过，但完整页面终审仍需：场所/法规类别筛选、hazard 详情、条款原文/locator、措施/适用说明/fallback、law index、异常/空结果、手机/桌面、PWA/Service Worker、刷新与旧缓存更新、非发布 hazard 不泄漏、私有信息扫描。

当前状态：`REVIEW_REQUIRED`。

## 12. I — Warning 与非发布库存处置

当前 strict warnings：60：

- 49 条 active_hazard_without_qualifying_link
- 11 条 supporting link

当前 excluded：105：

- 67 superseded/merged hazard
- 19 rejected link
- 18 repealed lawVersion
- 1 upcoming lawVersion

不能为了数字清零强行 direct/verified。每类必须给出“生产前修复 / 合法继续排除 / 后续 backlog”的专业理由。

当前状态：`REVIEW_REQUIRED`。

## 13. Evidence scanner 纠偏

本轮发现 `scan_evidence_exact.py` 旧逻辑会把未配置 EXPECT 域名映射的法规来源误报为 mismatch，同时 mismatch 不会可靠返回失败码。

已修正为：

- EXPECT 是逐步扩展的 allowlist，不是 denylist；
- 未配置映射的来源记为 UNMAPPED；
- 真实 mismatch 才计 MISMATCHED；
- MISMATCHED > 0 返回非零，使 CI/Gate 真正阻断。

最新运行：evidence refs inspected 3 / mapped checked 1 / unmapped 2 / mismatched 0。

## 14. J — 最终验收报告与生产准备

A–I 收口后才生成最终验收结论，至少包括最终 HEAD、完整 final candidate/hash、实体和发布规模、Gate/Strict、法规版本抽查、link/Requirement 终审、V3/V4 最终差异、网站/PWA/隐私、warning 处置、回退方案，并明确 `main`/production 尚未切换。

当前状态：`NOT_RUN`。

## 15. 下一执行顺序

1. 对 49 条 active 无合格依据 hazard 做风险排序并逐条判定，优先常见且可从现有/现行法规直接核验的消防、江苏安全管理、危化品、建设项目类；禁止批量强行建链。
2. 并行继续 20 条 pending Requirement 的逐条语义校准。
3. 对 14/12 个标准版本候选做当前官方来源核验。
4. 处理 9 个 merged-hazard link 和 11 个 obligation-restatement 候选。
5. 完成最终 V3/V4 diff。
6. 完成页面/PWA/隐私验收。
7. 知识树稳定后生成新的完整 final candidate，重跑全套终审并生成最终验收报告。
8. 全部通过后将 PROJECT_STATUS 改为 `READY_FOR_ACCEPTANCE`，等待用户是否批准 Phase 17。
