# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以远端事实为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

当前分支处于 **阶段 4 本地 UI 治理预览，未部署** 状态。阶段 1–3 的未提交成果保留；本轮未修改 `knowledge/`、`source/publication/`、稳定 ID、法规链接或业务结论，不等于线上站点或 `main` 已更新。

当前 checkout 的 `knowledge/manifest.json` 报告：**103 laws / 106 law versions / 2,992 clauses / 2,015 hazards / 1,886 links / 1,199 evidence / 26 successions / 75 requirements**。

阶段 4 本地预览（`asOf=2026-09-19`）为：**1,716 hazards / 58 laws / 58 law versions / 1,302 clauses / 1,824 links / public proposed 0**，`dataVersion=2026.09.19.stage4`，`releaseHash=a5818cd0f25645aa4e340549767036f2278f5108d35a88fee30f213cd0d3024c`。

阶段 4 外部材料目录：

`D:\codex romate\reviews\safety-basis-20260919\luna-stage4\`

其中包括：

- `STATUS.md`：完成状态、测试和边界；
- `note-routing-stage4.md` / `.json`：备注无损分流、搜索差异和未批准疑似维护内容；
- `classification-decision-stage4.md` / `.json`：19 个未映射场所值、泛化 / 复合分类候选及显式指定 ID 的决策清单；
- `browser-evidence-stage4.md`：桌面与 390 像素本地浏览器证据；
- `public-release/` 与 `site-selection-stage4.json`：本地验收包及选择文件，不是正式 `source/releases/current/`。

接手后先按 `AGENTS.md` 读取边界，再核对远端 `main` / PR / Actions；如文档与远端事实冲突，以远端事实为准。不要把历史批次中的 1250、1502、1680 等数字当作阶段 4 当前统计，也不要因为本地预览通过就宣称线上已部署。业务数据仍按明确维护触发条件处理，未经新的授权不主动扩大范围。
