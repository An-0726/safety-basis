# releases 目录

本目录不保存提交到 Git 的发布快照。

- `current/`：由 `tools/v4/build_unified_release.py`、GitHub Actions 或 `tools/build_local_release.py` 现场生成；已加入 `.gitignore`。
- `site-selection.json`：构建时根据 `current/release.json` 的 `releaseHash` 生成；已加入 `.gitignore`。
- `*.review.json`：构建审阅报告；已加入 `.gitignore`。

正式数据权威源是 `knowledge/`；公开来源和获准全文在 `source/publication/`；网站源码在 `web/`。发布包只是这三者经过当前日期 Gate 后的确定性生成物，不得人工编辑，也不得作为数据源反向覆盖 knowledge。

GitHub Pages 每次从 `main` 重新构建并验证后部署；本地最终版每次运行 `py -3 tools/build_local_release.py` 也会先重新构建，因此仓库不再存在“源码已更新但 current 仍是旧版本”的双版本问题。
