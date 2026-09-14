# 隐患依据速查库

面向工贸企业安全检查与评价报告的法规、标准、条款和隐患关联库。国家层面为主，江苏、南京地方依据为补充。

在线站点：<https://an-0726.github.io/safety-basis/>

> **接手本项目先读本页。** 当前仓库只认 `main` 一条主线、`source/releases/current/` 一个正式发布包、`docs/HANDOFF.md` 一份当前交接。旧阶段文档和旧“最终版”不再留在当前目录树，需要追溯时看 Git 历史。

## 一、唯一当前架构

```text
本地私有法规证据库 source/library/ （不进 Git）
        │ 原始 PDF / 网页快照 / OCR / 全文检索
        │
        ├──────────────┐
        ▼              ▼
knowledge/        source/publication/
正式结构化知识源    公开来源/题录/获准全文
法规身份            只提供来源和全文资料
法规版本            不创造第二套正式法规身份
具体条款
隐患与适用关系
审核记录
        │              │
        └──────┬───────┘
               ▼
tools/v4/build_unified_release.py
               ▼
source/releases/current/
仅当前已核验正式投影
               ▼
GitHub Pages / dist/local 公共部分
```

| 层级 | 位置 | 职责 | 是否人工维护 |
|---|---|---|---|
| 正式知识源 | `knowledge/` | 法规身份、版本、条款、隐患、关联、审核 | 是 |
| 公开来源层 | `source/publication/` | 官方入口、题录、允许公开的全文 | 是，但只维护来源/资料 |
| 私有证据库 | `source/library/` | 原件、归档、SQLite、OCR、待处理资料 | 是，本地维护；不进 Git |
| 当前正式发布包 | `source/releases/current/` | 网站与离线公共成品 | 否，只能由构建器生成 |
| 网站源码 | `web/` | 当前公开界面 | 是 |

本地当前工作仓库约定路径：

```text
D:\ESH\ESH_Codex\work\safety-basis\
```

私有法规证据库：

```text
D:\ESH\ESH_Codex\work\safety-basis\source\library\
```

`source/library/fulltext.sqlite3` 是全文检索数据库，不是法律原文最高证据。正式引用必须回到官方来源或本地保存的原始 PDF / 网页快照。

## 二、正式站、候选和全文资料彻底分开

### 正式隐患

`source/releases/current/` 和 GitHub Pages **只发布当前日期链式 Gate 通过的已核验隐患**。`lifecycle=proposed` 的候选继续保存在 `knowledge/` 中作为内部整改 backlog，但不进入正式公共包，也不通过正式站状态筛选暴露。

候选退出正式包 **不等于删除候选**。它的稳定 ID、来源行、审核状态和待办仍保留，完成法规版本、具体条款、原文证据和适用性审核后再转正。

### 正式法规库

正式“法规库”只由**正式条款实际引用的 `knowledge/law-versions`**生成。`source/publication/law-index.json` 不再作为正式法规列表的主源，只在 ID 已对应时补来源元数据。

因此：

- 同一法规同一版本的多个官方网站/平台来源，不再变成多张法规卡；
- 只有题录、没有正式条款关联的 publication 记录，不出现在正式法规库；
- 正式法规记录必须至少有一条当前正式条款关联；
- `LV_NPC_* / LV_META_* / LV_STD_*` 等内部来源/版本 ID 不再决定前台“有几部法规”。

### 法规全文 / 资料库

“法规全文”页面继续使用 `source/publication/fulltext/`，可以保留：公开全文、题录、官方入口、未来版本和当前尚未被隐患引用的资料。这是**资料目录**，不是正式法规身份目录。

## 三、法规身份、版本、来源的统一规则

必须区分三个概念：

1. **法规身份**：同一法规/标准一个身份；
2. **法规版本**：真实不同版本分别保存，并记录替代、生效、废止关系；
3. **来源记录**：国务院、国家法律法规数据库、标准平台、PDF 原件等只是该版本的来源证据。

处理规则：

- 同一法规、同一版本、不同来源 → 一个版本，多来源；
- 同一法规、不同真实版本 → 都保留，建立版本关系；
- publication 题录与 knowledge 正式版本重复 → 题录归来源层，不生成第二张正式法规卡；
- knowledge 内如果出现同一 `lawId + versionKey` 两个正式版本 ID，构建器直接拒绝发布，必须先人工对账；
- 完全重复隐患 → 当前发布只保留 canonical 记录，旧 ID 仅在确有追溯需要时保留映射；
- 不得只凭标题相似自动删除法规或隐患。

稳定内部 ID（`LF_* / LV_* / C_* / H_*`）用于关系绑定和历史追踪，不能为了前台好看随意重编号。

## 四、当前版本与 upcoming 的硬规则

正式站的“当前依据”按发布包 `asOf` 日期判断。法规版本只有同时满足以下条件，才可以支撑当前隐患：

- `validityStatus=active`；
- `effectiveDate <= asOf`；
- `endDate` 为空，或 `asOf < endDate`；
- 法规身份、版本、条款、证据和关联审核链均通过 Gate。

`upcoming` 表示**已发布但尚未实施**。它可以保留在知识库、私有证据库和“法规全文/资料库”中，但实施日前不能作为当前正式隐患依据。

“最新发布版本”不等于“当前适用版本”。正式引用必须结合检查日期、实施日期、废止/替代关系判断。

## 五、正式法规引用硬门禁

进入正式依据链至少要满足：

1. 法规/标准身份明确；
2. 适用版本明确；
3. 效力和实施状态明确；
4. 定位到具体条、款、项或标准条号；
5. 有对应逐字原文；
6. 有官方 URL 或可追溯证据快照；
7. 条款号和原文核对一致；
8. 条款确实适用于该隐患与场景；
9. 审核记录仍绑定当前内容；
10. AI、搜索摘要、Excel“条款要点”只能辅助发现，不能替代法条原文。

不满足时保持候选或库存资料，不得作为正式法律依据输出。候选处理只认 [docs/CANDIDATE_REVIEW.md](docs/CANDIDATE_REVIEW.md)。

## 六、数据数量怎么读

2026-09-14 的知识库存基线：

- `knowledge/`：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体；其中 1,419 active、517 proposed、78 superseded；
- 新版 Excel 目标集：1,929 个唯一隐患 ID；其中 621 条修订、1,308 条保留；
- `source/publication/`：216 项公开题录/来源记录、15 份获准公开全文、140 项官方入口；
- 私有全文交接记录：170 份全文、215,326 个检索段落，后续以实际 `fulltext.sqlite3` 复核结果为准。

**正式公开数量不再手工写死在 README。** 每次构建后以：

- `source/releases/current/release.json` 的 `counts`；
- `data/manifest.json` 的 `health`；
- `strict_release_audit.py` 的 `eligibleHazards / eligibleLinks`

为准。这样 Gate 规则变化、候选转正或法规生效时，不会让 README 又留下一个过期“最终数字”。

不要再用“1250、1929、2014、216、223”互相比较成同一种“数据库总数”。它们分别可能是历史批次已转正数、Excel 目标数、全部知识实体数、来源目录数和旧发布法规卡数，口径不同。

## 七、仓库整洁规则

当前主线文档固定只认：

- `README.md`：项目总入口与当前规则；
- `docs/ARCHITECTURE.md`：架构；
- `docs/MAINTENANCE.md`：日常维护；
- `docs/LEGAL_STATUS_POLICY.md`：法规效力规则；
- `docs/HANDOFF.md`：当前交接；
- `docs/CANDIDATE_REVIEW.md`：候选处理。

规则：

- 当前树不再保留 `*_YYYYMMDD.md`、`final/final2/latest`、旧发布编号、`docs/history/` 等多套“最终版”；历史由 Git commit 保存；
- `reports/` 不再保存另一份交接副本；当前交接只认 `docs/HANDOFF.md`；
- `source/releases/current/` 是唯一当前正式发布包，不手工修数据；
- `dist/local/`、HTML 阅读页、搜索索引等是可重建生成物，不反向导入母库；
- `tools/pipeline/` 是私有资料导入兼容层，仍有实际依赖时不能为了目录好看删除；
- 私有旧备份放仓库外，例如 `D:\ESH\ESH_Codex\archive\...`，不混回主仓库。

## 八、部署与严格验证

`main` 是唯一自动部署分支。GitHub Actions 每次更新 `main` 都会：

1. 校验 `knowledge/`；
2. 执行严格发布审计；
3. 删除 CI 工作区旧 `source/releases/current/`；
4. 按当天 `asOf` 从 `knowledge + source/publication + web` 重建唯一正式包；
5. 重新计算 `site-selection.json` 的发布哈希；
6. 严格验证完整包后部署 GitHub Pages。

严格审计器现在真正返回失败退出码：只要当前正式发布路径存在 blocker，CI 必须失败；未来版本、历史版本和未完成候选作为 inventory/excluded 管理，不得偷偷进入正式投影。

本地完整检查：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
rm -rf source/releases/current   # Windows 下用对应删除命令
py -3 tools/v4/build_unified_release.py --out source/releases/current --as-of YYYY-MM-DD
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
```

本地最终版重新生成：

```text
py -3 tools/build_local_release.py
```

## 九、2026-09-14 架构收口记录

本轮收口包括：

- 删除旧日期版 handoff、候选清单、回灌阶段说明、重复 report 和临时 history 文档；历史改由 Git 保存；
- `main` 收成唯一部署主线，CI 每次从当前源码重建发布包；
- 正式站前端先停止默认展示候选和零条款法规；
- **进一步把候选从发布数据层彻底移除**：`proposed` 只留在 `knowledge/`；
- **正式法规索引改由 knowledge 被正式条款引用的版本生成**，publication 只补来源/全文资料；
- **恢复正确的时间效力门禁**：upcoming 实施前不得支撑当前正式隐患；
- 严格校验器新增“正式法规必须恰好等于正式条款引用版本”“正式法规不得零条款”“正式包不得有候选”等约束；
- 严格审计存在 blocker 时改为非零退出，CI 不再假通过；
- 长技术 ID 从主要前台展示隐藏，但底层稳定 ID 不重编号；
- 本轮不修改 `source/library/` 私有 PDF、`fulltext.sqlite3`、OCR 和原始证据。

## 十、变更记录要求（必须执行）

以后任何影响架构、数据口径、法规归并、候选策略、发布范围、大批量回灌、本地母库位置或停用工具的改动，都必须同步更新本 README。

提交说明至少回答：**改了什么、为什么改、影响哪些数据、是否需要重新构建/重新审核。**

## 十一、相关文档

- [当前架构](docs/ARCHITECTURE.md)
- [日常维护](docs/MAINTENANCE.md)
- [法规效力规则](docs/LEGAL_STATUS_POLICY.md)
- [当前交接](docs/HANDOFF.md)
- [候选处理](docs/CANDIDATE_REVIEW.md)

## 十二、隐私与许可证

本仓库与 GitHub Pages 是公开空间。企业报告、照片、未脱敏附件、内部台账、私有法规原件和受版权限制的标准全文只进入私有目录。法规原文及标准文本的权利归相应发布机关或权利人所有。

代码采用 [MIT License](LICENSE)。
