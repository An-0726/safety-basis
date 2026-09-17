from pathlib import Path

p = Path('docs/PROJECT_STATE.md')
text = p.read_text(encoding='utf-8')

replacements = [
    (
        '2026-09-17 首轮 PHASE 11 维护完成三组实际动作：',
        '2026-09-17 首轮 PHASE 11 维护完成四组实际动作：'
    ),
    (
        '- PR #45：新增 1 个正常通过 + 6 个失败场景的合成回归测试，并固定 catalog / search-index / full-text / gram schema 与 catalog/search `asOf` 一致性。',
        '- PR #45：新增 1 个正常通过 + 6 个失败场景的合成回归测试，并固定 catalog / search-index / full-text / gram schema 与 catalog/search `asOf` 一致性。\n- 当前-main 本地验收：在独立临时 worktree 上检出 `c2ffe2042a316881f229eea8899156fa897f601d`（与当时最新 `origin/main` 完全一致），复用真实私有 `source/library/` 后执行 `py -3 tools/build_local_release.py`，`validate_all.py`、`strict_release_audit.py`、`validate_publication_integrity.py` 与 `verify_unified_bundle.py` 全部 PASS；完整记录见 `docs/PHASE11_LOCAL_ACCEPTANCE_20260917.md`。'
    ),
    (
        '私有本地版仍以 PHASE 9 已通过的真实 SQLite 验收为准：170 documents / 215,326 FTS rows / 36 canonical alias members；SQLite SHA-256 `7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`。本轮 PHASE 11 未写 SQLite/FTS/archive。',
        '私有本地版已在 PHASE 11 对**当前正式 main**重新完成真实母库验收：独立 worktree HEAD=`c2ffe2042a316881f229eea8899156fa897f601d`，现场重建为 **1,429 active / 499 proposed / public proposed 0 / 57 formal law versions / 1,205 clauses / 1,544 links / publication 69（11 full_text + 58 link_only）/ 170 private document carriers**，全部 Gate 与 unified bundle verify 均 PASS。真实 SQLite 仍为 170 documents / 215,326 FTS rows / 215,326 paragraphCountSum / mismatch 0，SHA-256 `7b6916e314bb10b686b3595b7760b408816b893795d7fc4b7b6d535d07dca629`，构建前后 SHA/size/mtime 完全不变；本轮未写 SQLite/FTS/archive。'
    ),
    (
        '远端治理仍有一个明确未自动完成项：Issue #44 记录 `main` 当前 `protected=false` 且仓库 rulesets 为空，以及历史远端分支清理分类。当前 GitHub 连接器没有创建 branch protection / ruleset 或删除 branch ref 的管理写接口，因此该项保持显式 OPEN，不把它伪装成已完成。Issue #44 同时明确禁止把 `chat-v4`、`phase3-local-alias-grouping-20260914`、`verify-batch-003` 的历史独有提交误当成当前待合并业务。',
        '远端治理仍有一个明确未自动完成项：Issue #44 记录 `main` 当前 `protected=false` 且仓库 rulesets 为空，以及历史远端分支清理分类。本机进一步确认 `gh` CLI 未安装且没有 `GH_TOKEN` / `GITHUB_TOKEN` 管理凭据；当前 GitHub App 对 protection/ruleset 管理写接口返回 `403 Resource not accessible by integration`，因此该项继续显式 OPEN，不把它伪装成已完成。Issue #44 同时明确禁止把 `chat-v4`、`phase3-local-alias-grouping-20260914`、`verify-batch-003` 的历史独有提交误当成当前待合并业务。'
    ),
    (
        '> **当前没有新的正式业务数据待处理；PHASE 11 保持长期维护等待。下一次触发来自新法规/版本/隐患/证据、候选转正条件满足、CI/Pages 异常、私有库维护不变量异常，或 Issue #44 的仓库治理条件具备。**',
        '> **当前没有新的正式业务数据待处理；当前-main + 真实私有母库的本地最终版已在 PHASE 11 重新验收通过。PHASE 11 继续保持长期维护等待；下一次触发来自新法规/版本/隐患/证据、候选转正条件满足、CI/Pages 异常、私有库维护不变量异常，或 Issue #44 的仓库治理条件具备。**'
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'expected exactly one match, found {count}: {old[:100]}')
    text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8', newline='\n')
