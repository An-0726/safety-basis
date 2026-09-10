# Safety Basis V4 最终验收与生产切换前收口框架

> 状态：IN_PROGRESS
> 建立日期：2026-09-10
> 适用分支：`chat-v4`
> 本文件是 Phase 16 的唯一总验收清单。各专项报告可以提供证据，但不得用旧报告中的历史数字覆盖当前真实知识树。

## 1. 目标与边界

最终验收的目标不是把历史库存全部清零，而是确认准备进入生产的 V4 候选知识库和网站满足：内容正确、法规版本正确、条款可靠、隐患—依据适用、公开投影完整、私有信息不泄漏、构建可复现、与 V3 的合理差异可解释。

Phase 16 全部通过后，项目状态改为 `READY_FOR_ACCEPTANCE`。只有用户明确批准后才进入 Phase 17；Phase 16 不得修改 `main`、不得切换 GitHub Pages、不得设置 `production=true`。

## 2. 当前验收基线

本框架建立时从真实文件恢复的基线：

- 工作分支：`chat-v4`
- 开工 HEAD：`50eb0b35a13579fba7ac8461822cbddcc4292df6`
- V3 冻结 SQLite：`source/master/safety.sqlite3`
- V3 SHA-256：`7086d945eef1b6ea74b28c1af94e87e37d1b520b18caed2e1064f8855fd76bc8`
- 当前 V4 规模：75 laws / 75 lawVersions / 88 clauses / 712 hazards / 735 links / 75 requirements / 567 evidence / 23 successions
- 当前候选发布包：`source/releases/v4-candidate-20260910/`
- 候选发布状态：596 publishable hazards / 666 eligible links / 19 rejected links / 0 pending links
- 候选 `sourceStateHash`：`6b0adf8953769c5aa84b017ff9b0160ea8b0baddaf1bc35f87b2864c09cee9a7`
- 候选标志：`candidate=true`，`production=false`

任何知识文件发生变化后，上述候选只能作为旧快照，必须重新构建并重新验收。

## 3. 总验收判定规则

每个检查域使用以下状态：

- `PASS`：证据充分，满足生产切换前要求。
- `WARNING`：有非阻断遗留，但不影响公开内容真实性或安全性；必须记录原因。
- `REVIEW_REQUIRED`：需要继续专业复核，Phase 16 不得结束。
- `BLOCKED`：存在可能导致错误发布、数据破坏或隐私泄漏的问题。
- `NOT_RUN`：尚未执行。

最终进入 `READY_FOR_ACCEPTANCE` 的必要条件：所有硬检查域均为 `PASS`；允许存在经明确分类、不会影响当前公开投影的 `WARNING`；不得存在 `BLOCKED`、`REVIEW_REQUIRED` 或关键项 `NOT_RUN`。

## 4. A — 基线、版本与交接一致性

检查：

1. `chat-v4` 真实 HEAD 与交接文件一致。
2. `knowledge/manifest.json` 的 counts/scope 与真实知识树、candidate 一致。
3. V3 SQLite SHA 与冻结基线一致，且未被写入。
4. candidate 的 `sourceStateHash` 对应当前待验收知识树。
5. 旧报告如果包含历史统计，必须显式标记为历史快照，不能冒充当前结果。
6. `docs/CHAT_HANDOFF.md` 使用用户定义 Phase 1–17，不自行扩展出 Phase 18+。

硬阻断：基线无法确认、candidate 与知识树不一致但被当作最新包、V3 被覆盖、分支状态不清。

当前状态：`REVIEW_REQUIRED`。

已发现：`knowledge/manifest.json.scope` 仍残留旧 68 laws / 662 hazards / 181 links；`docs/V4_STRICT_AUDIT.md` 仍是旧 162 publishable / 209 links 快照；原 handoff 将当前阶段写为“Phase 22”，与项目正式 Phase 1–17 定义不一致。

## 5. B — 数据结构与引用完整性

检查：

- Stable ID 唯一；hazard/law/lawVersion/clause/link/requirement/evidence 引用无断链。
- superseded/merged hazard 的关系闭合，不被公开投影错误发布。
- 法规版本与 clause 父子关系唯一且正确。
- link role 仅允许项目定义的合法值，review 状态与实体绑定正确。
- 私有路径、Drive ID、内部绝对路径、内部审计敏感字段不得进入公开发布数据。

执行证据：`validator_v4.py`、shared release gate、strict audit、公开数据扫描。

当前状态：`PASS (existing evidence) / 需最终重跑确认`。

## 6. C — 法规与标准版本终审

采用风险导向抽查，不以随机数量代替专业判断。至少覆盖：

1. 危险化学品：2026《危险化学品安全法》与既有条例/规章并存、替代和适用边界。
2. 消防：消防法、GB 50016 及当前相关消防技术标准。
3. 电气：低压配电、防爆电气、临时用电等高频直接技术依据。
4. 粉尘防爆：粉尘爆炸危险场所与除尘系统相关标准。
5. 特种设备：气瓶、压力容器、起重/叉车等当前 TSG/法规链。
6. 职业健康与个体防护。
7. 江苏省、南京市高频地方依据。
8. 2025–2026 新实施或替代的标准。

每个抽查对象必须核：身份、版本、实施/废止日期、条款 locator、条款原文证据、适用范围和 succession。

发现无法确认的，不得强行通过；标记 `pending/REVIEW_REQUIRED` 并从当前发布链排除。

当前状态：`NOT_RUN`（最终独立抽查尚未形成统一终审记录）。

## 7. D — Hazard → Clause 适用性与依据角色终审

重点不是再批量增加 links，而是验证现有发布链有没有“看似相关但不直接支持”的错误。

抽查矩阵至少覆盖：消防、电气、危化品、粉尘、防爆、燃气、设备设施、特种设备、应急、安全管理、总图建筑、作业安全。

逐条判断：

- 监管对象和现场事实是否一致；
- 条款义务是否真正覆盖 hazard；
- `direct` 是否被高估；
- `fallback` 是否确实只作为兜底；
- 是否存在更直接但当前遗漏的依据；
- 一个泛化上位法是否被错误包装成技术要求。

当前状态：`PASS (既有 666 eligible / 19 rejected / 0 pending) / 需风险抽查确认`。

## 8. E — Requirement 语义终审

Requirement 是现场检查要求，不得创造原法规不存在的义务。

检查：

- obligation 主体、行为、条件、对象和边界均能回指 clause；
- 不擅自增加技术参数、周期、证件名称、审批流程、保存期限；
- 新法/旧法并存时，不把待废止或被替代规则错误写成当前义务；
- 未校准 Requirement 不得伪装为已核验生产要求。

当前状态：`REVIEW_REQUIRED`。现有 75 条 Requirement 中需继续核对实际 review 状态并完成剩余终审。

## 9. F — V3 → V4 差异与回归验收

必须回答“为什么变了”，而不是只追求数字相同。

检查：

- V3 已可靠发布 hazard 是否无故丢失；
- Stable ID 是否变化；
- title/专业描述/整改措施的变化是否有理由；
- law identity/version/clause/link/role 的差异是否属于纠错、拆分、合并或质量提升；
- r8 历史错误不得因为追求覆盖率重新带回；
- `docs/V3_V4_DIFF_REPORT.md` 必须与最终候选重新同步，不得保留中途 543/596 links 等历史数字作为最终验收结论。

当前状态：`REVIEW_REQUIRED`。现有差异报告是中途快照，需要在最终候选稳定后重跑/重写。

## 10. G — Release、构建与门禁验收

最终候选稳定后必须连续执行并保存结果：

1. V4 validator；
2. `gate_v4.py`；
3. strict release audit；
4. candidate build；
5. 再次 validator/gate/strict audit；
6. 至少两次确定性构建，对比 `sourceStateHash` 与公开文件集合；
7. 确认 `candidate=true`、`production=false`。

Hard Gate：STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE 任一关键阶段非 PASS，不得进入 READY_FOR_ACCEPTANCE。

当前状态：`PASS (上一稳定候选) / 最终候选需重跑`。

## 11. H — 网站、搜索、页面和 PWA 验收

必须在候选站点上执行：

- 高频关键词搜索；
- 场所筛选；
- 法规类别筛选；
- hazard 详情；
- 法规原文与条款定位；
- 整改措施与适用说明；
- fallback 标识；
- law index；
- 空结果与异常输入；
- 手机/桌面基本布局；
- PWA / Service Worker 缓存版本；
- 刷新、离线缓存、旧缓存更新；
- 不可发布 hazard 不出现在公开 search-index；
- 无私有信息泄漏。

当前状态：`REVIEW_REQUIRED`。已有历史搜索回归结果不能替代最终 candidate 的完整页面验收。

## 12. I — Warning 与非发布库存处置

库存 Warning 不要求为了“数字清零”而强行通过。

逐类确认：

- 是否只影响非发布实体；
- 是否存在会在未来法规版本切换时影响生产的风险；
- 是否需要在生产前修复；
- 是否可以合法保留为后续 backlog。

每类 warning 必须给出“阻断 / 非阻断”的理由，不允许只写数量。

当前状态：`REVIEW_REQUIRED`。

## 13. J — 最终验收报告与生产准备

全部检查完成后生成最终验收结论，至少包含：

- 最终 HEAD；
- 最终 candidate 路径/hash；
- 实体规模和 publishable 规模；
- validator/gate/strict audit 结果；
- 法规版本抽查结果；
- link 适用性抽查结果；
- Requirement 终审结果；
- V3/V4 最终差异结论；
- 网站/PWA/隐私验收结果；
- warning 清单及处置；
- 回退方案；
- 明确声明 `main`/production 尚未切换。

只有 A–I 收口后，`PROJECT_STATUS` 才可改为 `READY_FOR_ACCEPTANCE`。

当前状态：`NOT_RUN`。

## 14. 本轮首次终审发现

1. `knowledge/manifest.json.scope` 与真实 counts/candidate 不一致，必须修正。
2. `docs/V4_STRICT_AUDIT.md` 仍保留 74 laws / 85 clauses / 209 links / 162 eligible hazards 的历史快照，必须同步或标记为历史。
3. `docs/V3_V4_DIFF_REPORT.md` 仍保留中途 543 publishable / 596 links / 523 eligible links 等统计，不能作为最终差异报告。
4. `docs/CHAT_HANDOFF.md` 使用“Phase 22”，与用户定义的 17 Phase 施工顺序不一致；应纠正为 Phase 16。
5. 由于 `build_release.py` 的 `sourceStateHash` 对 `knowledge/**/*.json` 全量计算，任何 `knowledge/manifest.json` 修改都会使旧 candidate hash 变为历史快照；修正 manifest 后必须重建 candidate 才能重新声明最终 PASS。

## 15. 下一执行顺序

1. 修正 `knowledge/manifest.json.scope`。
2. 修正 handoff Phase 编号与本轮状态。
3. 将旧 strict/diff 报告明确同步或标记为历史，并建立最终报告的新基线。
4. 重建 candidate 并重跑 validator/gate/strict audit；若当前执行环境无法拉取 GitHub，则记录为下一轮第一步，不伪造结果。
5. 开始 C/D/E 风险导向专业抽查。
6. 进行网站/搜索/PWA/隐私完整验收。
7. 生成最终验收报告，达到 `READY_FOR_ACCEPTANCE` 后等待用户是否批准 Phase 17。
