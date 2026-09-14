# 隐患依据速查库

面向工贸企业安全检查与评价报告的法规、标准、条款和隐患关联库。国家层面为主，江苏、南京地方依据为补充。

在线站点：<https://an-0726.github.io/safety-basis/>

> **接手本项目先读本页。** 当前仓库只认 `main` 一条主线、`source/releases/current/` 一个发布包、`docs/HANDOFF.md` 一份当前交接。旧阶段文档和旧“最终版”不再留在当前目录树，需要追溯时看 Git 历史。

## 一、唯一当前架构

```text
本地私有法规证据库 source/library/ （不进 Git）
        │ 原始 PDF / 网页快照 / OCR / 全文检索
        │
        ├──────────────┐
        ▼              ▼
knowledge/        source/publication/
正式结构化知识源    公开来源/题录/获准全文
法规身份            不单独创造第二套法规身份
法规版本
具体条款
隐患与适用关系
审核记录
        │              │
        └──────┬───────┘
               ▼
tools/v4/build_unified_release.py
               ▼
source/releases/current/
               ▼
GitHub Pages / dist/local 公共部分
```

| 层级 | 位置 | 职责 | 是否人工维护 |
|---|---|---|---|
| 正式知识源 | `knowledge/` | 法规身份、版本、条款、隐患、关联、审核 | 是 |
| 公开来源层 | `source/publication/` | 官方入口、题录、允许公开的全文 | 是，但只维护来源信息 |
| 私有证据库 | `source/library/` | 原件、归档、SQLite、OCR、待处理资料 | 是，本地维护；不进 Git |
| 当前发布包 | `source/releases/current/` | 网站与离线公共成品 | 否，只能由构建器生成 |
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

## 二、当前网站只展示什么

正式网站的默认视图已经收口为：

- **隐患速查**：只展示通过链式 Gate 的 `已核验` 隐患；`proposed` 候选继续留在 `knowledge/` 中审核，但不和正式结果混排。
- **法规库**：只展示存在正式收录条款的法规版本；`source/publication/law-index.json` 中只有题录/来源、没有正式条款的记录不再作为第二张法规卡出现。
- **法规全文**：继续承担公开全文、题录和官方入口查阅职责，因此一个法规可以有多个来源记录，但正式法规身份只能有一个。
- `LF_* / LV_* / C_* / H_*` 是后台稳定关系键，不因为前台不好看而重编号；公开页面不再把长技术 ID 当作主要标签展示。

这解决的是“正式展示重复”，不是粗暴删除证据。仍有法律追溯价值的旧法规版本、来源记录和稳定 ID 映射必须保留。

## 三、法规、版本、来源的统一规则

必须区分：

1. **法规身份**：同一法规/标准一个身份；
2. **法规版本**：真实不同版本分别保存，并记录替代、生效、废止关系；
3. **来源记录**：国务院、国家法律法规数据库、标准平台、PDF 原件等都只是该版本的来源证据。

处理规则：

- 同一法规、同一版本、不同来源 → 一个版本，多来源；
- 同一法规、不同真实版本 → 都保留，建立版本关系；
- 新版已发布但未实施 → `upcoming`，不能冒充现行依据；
- publication 题录与 knowledge 正式版本重复 → 题录归到来源层，不再生成第二张正式法规卡；
- 完全重复隐患 → 当前发布只保留 canonical 记录，旧 ID 仅在确有追溯需要时保留映射；
- 不得只凭标题相似自动删除法规或隐患。

## 四、正式法规引用硬门禁

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

不满足时保持候选，不得作为正式法律依据输出。候选处理规则只认 [docs/CANDIDATE_REVIEW.md](docs/CANDIDATE_REVIEW.md)。

## 五、当前数据基线与口径

2026-09-14 已知知识源基线：

- `knowledge/`：96 个法规身份、97 个法规版本、2,843 条条款、2,014 个隐患实体；其中 1,419 active、517 proposed、78 superseded。
- 新版 Excel 目标集：1,929 个唯一隐患 ID；其中 621 条修订、1,308 条保留；8 条重复记录不重复发布。
- 当前已核验隐患：1,409 条；候选仍留在后台继续做精确条款、原文证据和适用性回绑。
- `source/publication/`：216 项公开题录/来源目录、15 份获准公开全文、140 项官方入口。**216 不是法规身份数。**
- 私有全文交接记录：170 份全文、215,326 个检索段落。该数字以后以实际 `fulltext.sqlite3` 复核结果为准。

不要再用“1250、1929、2014、216、223”互相比较成同一种“数据库总数”。它们分别可能表示某一批已转正数、Excel 目标数、全部知识实体数、publication 目录数、旧发布法规卡数，统计口径不同。

## 六、仓库整洁规则

当前主线文档固定只认：

- `README.md`：项目总入口与当前规则；
- `docs/ARCHITECTURE.md`：架构；
- `docs/MAINTENANCE.md`：日常维护；
- `docs/LEGAL_STATUS_POLICY.md`：法规效力规则；
- `docs/HANDOFF.md`：当前交接；
- `docs/CANDIDATE_REVIEW.md`：候选处理。

规则：

- 当前树不再保留 `*_YYYYMMDD.md`、`final/final2/latest`、旧发布编号、`docs/history/` 等多套“最终版”；历史由 Git commit 保存。
- `reports/` 不再用于保存另一份交接副本；当前交接只认 `docs/HANDOFF.md`。
- `source/releases/current/` 是唯一当前发布包，不手工改数据。
- `dist/local/`、HTML 阅读页、搜索索引等是可重建生成物，不反向导入母库。
- `tools/pipeline/` 虽属旧 V3 兼容层，但仍被本地私有全文导入/测试依赖；在依赖彻底迁移前不能为了“目录好看”删除。
- 私有旧备份放仓库外，例如 `D:\ESH\ESH_Codex\archive\...`，不混回主仓库。

## 七、部署与验证

`main` 是唯一自动部署分支。GitHub Actions 每次更新 `main` 都会：

1. 校验 `knowledge/`；
2. 执行严格发布审计；
3. 删除 CI 工作区里的旧 `source/releases/current/`；
4. 从当前 `knowledge + source/publication + web` 重新构建唯一 `current` 包；
5. 重新计算 `site-selection.json` 的发布哈希；
6. 验证完整包后部署 GitHub Pages。

本地完整检查：

```text
py -3 tools/v4/validate_all.py
py -3 tools/v4/strict_release_audit.py
py -3 tools/v4/build_unified_release.py --out source/releases/current
py -3 tools/v4/verify_unified_bundle.py --bundle source/releases/current
py -3 -m unittest discover -s tools/pipeline/tests -v
node --test tests/*.test.mjs
```

本地最终版重新生成：

```text
py -3 tools/build_local_release.py
```

## 八、本次 2026-09-14 收口做了什么

- 删除旧的日期版候选手册、旧 Excel 待核验清单、新版回灌阶段说明、重复 handoff/report 和临时 `docs/history/`；历史仍可从 Git 恢复。
- 新建固定文件名 `docs/CANDIDATE_REVIEW.md`，以后不再按日期复制候选手册。
- `web/js/store.js` 的正式投影改为只加载已核验隐患，并只保留有正式条款的法规版本；公开数据导出也只导出当前正式隐患。
- 网站导航收成“隐患速查 / 法规库 / 法规全文”，不再把内部维护状态当作主导航入口。
- 长技术 ID 从主要展示位置隐藏，但底层 ID 不重编号，避免破坏关联。
- GitHub Actions 收成 `main` 唯一自动构建/部署来源，不再监听旧批次分支。

## 九、变更记录要求（必须执行）

以后任何影响架构、数据口径、法规归并、候选策略、发布范围、大批量回灌、本地母库位置或停用工具的改动，都必须同步更新本 README。

提交说明至少回答：**改了什么、为什么改、影响哪些数据、是否需要重新构建/重新审核。**

## 十、相关文档

- [当前架构](docs/ARCHITECTURE.md)
- [日常维护](docs/MAINTENANCE.md)
- [法规效力规则](docs/LEGAL_STATUS_POLICY.md)
- [当前交接](docs/HANDOFF.md)
- [候选处理](docs/CANDIDATE_REVIEW.md)

## 十一、隐私与许可证

本仓库与 GitHub Pages 是公开空间。企业报告、照片、未脱敏附件、内部台账、私有法规原件和受版权限制的标准全文只进入私有目录。法规原文及标准文本的权利归相应发布机关或权利人所有。

代码采用 [MIT License](LICENSE)。
