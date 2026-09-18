# PHASE 11 本地私有库与 current-main 验收记录（2026-09-17）

本记录补充 PHASE 11 首轮维护治理的本机验收证据。目的不是重复 PHASE 9 RC，而是确认**当前正式 `origin/main` + 真实私有 `source/library/`**仍可完整重建本地最终版，并确认本机数据库在构建前后没有发生写入。

## 1. 验收代码快照

- 独立临时 worktree：`D:\ESH\ESH_Codex\work\safety-basis-main-acceptance`
- worktree HEAD：`c2ffe2042a316881f229eea8899156fa897f601d`
- 该 SHA 与验收时最新 `origin/main` 完全一致（PR #46 合并提交）。
- 原工作区保持在原分支/HEAD，没有 reset、覆盖、rebase 或分支删除。

## 2. 真实私有 SQLite 只读验收

真实母库：`D:\ESH\ESH_Codex\work\safety-basis\source\library\fulltext.sqlite3`

- size：`106,958,848` bytes
- SHA-256：`7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`
- Python：3.12.10 / Windows 64-bit
- SQLite：3.49.1
- documents：170
- fulltext_fts：215,326
- `SUM(paragraph_count)`：215,326
- per-document mismatch：0
- `ftsContentSha256`：`1caeed69bc50ab7409d8d6ec40e324ad185294fbc1710e011cdbc2a4ac96c8dd`
- `PRAGMA foreign_key_check`：0 errors
- `PRAGMA integrity_check`：`ok`

搜索抽检：

- `洗眼器`：15
- `危险化学品`：13,864
- `GB 55036`：707（严格连续短语为 704，差额来自正文中无空格的 `GB55036-2022` 等正常文本形态）

Alias/canonical 映射保持：18 groups / 36 members / 170 document carriers。未发生 document 物理折叠、删除、主键改写或 archive 迁移。

Archive/provenance 当前核验：132 archive-backed document rows / 129 unique archive SHA；archive 目录 136 个 SHA 中其余 7 个仍为历史纯文本派生物。没有 broken `archive_ref`，38 条 legacy `evidence/...` provenance 保持原状。

## 3. 当前 main 本地最终版构建

在上述独立 worktree 中，以只读目录联接复用原 `source/library`，执行：

```text
py -3 tools/build_local_release.py
```

结果：exit code 0，完整 PASS。

构建链验收：

- `tools/v4/validate_publication_integrity.py`：PASS
- `tools/v4/validate_all.py`：PASS
- `tools/v4/strict_release_audit.py`：PASS，blockerCount=0
- `tools/v4/verify_unified_bundle.py`：PASS

当前 main 现场重建结果：

- active hazards：1,429
- knowledge proposed：499
- public proposed：0
- formal law versions：57
- clauses：1,205
- links：1,544
- publication：69（11 full_text + 58 link_only）
- private document carriers/pages：170

构建前后 SQLite SHA-256、size 与修改时间均不变，确认当前 main 本地构建对真实母库保持只读。

## 4. GitHub main protection 状态

本机没有安装 GitHub CLI：`gh --version` 与 `gh auth status` 均返回 `gh` 未识别；也没有可用的 `GH_TOKEN` / `GITHUB_TOKEN` 管理凭据。

连接的 GitHub App 管理接口对 branch protection/ruleset 写入返回 `403 Resource not accessible by integration`。因此本轮没有尝试绕过权限或降低安全要求。

验收时远端仍为：

- `main protected=false`
- repository rulesets：`[]`

Issue #44 继续保持 OPEN。后续具有仓库管理权限时，应对 `main` 至少配置：

- require pull request before merging；
- required status checks：实际 check-run contexts `validate` 与 `build`；
- 禁止 force push；
- 禁止删除 `main`。

历史分支清理仍按 Issue #44 分类另行处理；`chat-v4`、`phase3-local-alias-grouping-20260914`、`verify-batch-003` 不得盲删或重新并入当前业务状态。

## 5. 变更声明与结论

本机验收期间：

- SQLite 修改：NO
- knowledge 业务数据修改：NO
- archive 移动/删除/重命名：NO
- 远端 branch 删除：NO
- 原工作区源码覆盖：NO
- Issue #44 关闭：NO

**LOCAL PHASE 11 ACCEPTANCE: PASS WITH WARNINGS**

PASS 部分：当前正式 main 与真实私有母库组合的本地最终版可重复构建，公开/私有边界、正式业务数量、全部长期 Gate 与私有 SQLite 内容不变量均通过。

唯一治理 WARNING：GitHub `main` 尚未由平台技术性强制 PR + required checks + no-force-push + no-delete；该项继续由 Issue #44 显式跟踪。

## 6. 最新主线复验（2026-09-18）

在首轮验收后，PHASE 11 又完成远端治理、GB 46768-2025 收录、搜索修复、电气隐患补录/转正和 GB/T 13869 版本治理校正。为避免把 `c2ffe204` 的历史结果冒充当前状态，本节对最新正式主线重新验收。

### 6.1 代码与远端状态

- 独立验收 worktree HEAD：`125a7afd76d9e1152d9d7f2f9ff70f9cde9e818d`，与复验时 `origin/main` 完全一致；
- PR #54：`Fix GB/T 13869 current/upcoming version governance`，已合并；
- GitHub Validate run `35234313626`：success；
- GitHub Build/Pages run `35234313621`：success；
- open PR：0；open issue：0。

### 6.2 真实私有 SQLite 只读审计

- size：`106,958,848` bytes；
- SHA-256：`4ef901054478a8299cc8180f7b8de78c85baae677f94a828bcaab70a2677467f`；
- documents：171；
- fulltext_fts：215,464；
- `SUM(paragraph_count)`：215,464；
- per-document mismatch：0；
- `ftsContentSha256`：`530b0ff6e6708a84c4e056cad54797e5726d45d2b9f0c578d59625e4e74b3a55`；
- `PRAGMA foreign_key_check`：0 errors；
- `PRAGMA integrity_check`：`ok`。

构建前后数据库 SHA-256、size、mtime 完全一致；未写 SQLite/FTS/archive。

### 6.3 最新本地最终版重建

在同一独立 worktree 中执行 `py -3 tools/build_local_release.py`，exit code 0。`validate_all.py`、`strict_release_audit.py`、`validate_publication_integrity.py` 和 `verify_unified_bundle.py` 全部 PASS，blockerCount=0，bundle `ok=true`。

- active hazards：1,442；
- knowledge proposed：487；
- public proposed：0；
- formal law versions：58；
- published clauses：1,216；
- published links：1,558；
- private document carriers：171；
- releaseHash：`b1f29e07b00e9e56c53bf4eb1ea7d0c13e84ec31657b895b3a7bdc3c8a2dd094`。

首轮验收中的 GitHub 治理 warning 已由后续 PR #48/#49 解决。本次结论为：**LOCAL PHASE 11 CURRENT-MAIN ACCEPTANCE: PASS**。
