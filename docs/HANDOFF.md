# 接手说明

- 长期工作边界：[AGENTS.md](../AGENTS.md)。
- 阶段、已核事实、暂停状态和恢复计划：[PROJECT_STATE](PROJECT_STATE.md)。该文件标注核验日期，不代表每次读取时重新验证；如与远端 `main`、当前 commit 或 Actions 事实冲突，以远端事实为准。
- 架构与维护说明：[README](../README.md)；长期维护触发条件见 [MAINTENANCE](MAINTENANCE.md)。
- 确需跨环境协作：[执行协议](../AGENT_EXECUTION_PROTOCOL.md)。

**2026-09-21 工程级审计整改及商贸集团检查全量补库已正式上线。** PR #76 已合并 `main`（merge commit `fdd973190e76d53b02a1cfaddea1c2b6af9dcdca`）。本次读取当前商贸集团检查文件夹 16 份 Word，134 条来源事项 134/134 有知识库去向；main Validate、Build、GitHub Pages Deploy 和部署后真实 Chromium Online Verify 均已通过。

当前 checkout 的 `knowledge/manifest.json`：**104 laws / 107 law versions / 2,993 clauses / 2,101 hazards / 1,924 links / 1,201 evidence / 26 successions / 75 requirements**；生命周期 **1,681 active / 323 proposed / 97 superseded**。

当前正式公开包（`asOf=2026-09-21`）：**1,681 hazards / 59 laws / 59 law versions / 1,304 clauses / 1,791 links / public proposed 0**；`releaseHash=c69264f35bb6e046692b60f1833d1d808c7c764bc56b6f626c17e771770902e3`。main Validate run `35553278277`、Build/Deploy/Online Verify run `35553278312` 全部通过。

本轮关键处置：在工程审计基础上，进一步全量读取商贸集团当前16份检查记录，将134条现场事项去企业化后逐条映射；新增48个通用隐患（1 active、47 proposed）和1条已核 direct 关联。复合问题拆分，已有 canonical 不重复造 ID；“现场无法确认”“需先核SDS/场所条件”等问题保留 proposed/待补证，不强行转正。

接手后先核对远端 `main` / Actions 与线上站点；当前项目已转入长期维护。后续新增法规、隐患或网页修改继续遵循 Gate、PR、Pages 部署和线上复验流程。
