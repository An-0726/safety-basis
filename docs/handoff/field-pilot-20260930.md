# 现场隐患 24 例试点云端交接

正式项目仍为 An-0726/safety-basis。本分支是供云端继续工作的代码快照，基线为 `d71bde1c57d71e960f1fa64a3ef1eb731a7269cb`，快照时间为 2026-09-30 07:48:03 UTC；未合并、未部署、未作整包验收结论。

## 恢复

本分支公开 9 个安全代码和通用说明文件及本交接资料。24 个候选记录、18 个证据记录，以及内部来源核验材料保存在私有 An-0726/codex-cloud 的 `handoff/field-pilot-20260930` 分支，目录 `projects/safety-basis/field-pilot/20260930T074803Z`。公开试点测试和试点构建需要先恢复该私有覆盖层；仅检出公开分支不能运行完整的 24 例试点。

在有权限的云环境检出本分支，另行检出私有分支。先阅读私有目录内 README 和 exclusions.json，再运行 `python <私有目录>/restore.py --repo <本项目目录>`。恢复器校验压缩包、每个文件的 SHA-256 和现有公开代码，再复制私有候选数据；出现本地差异会拒绝覆盖。没有权限的阅读者只能取得安全代码与通用说明。

## 当前状态与接续范围

共有 24 例：18 个正例、6 个反例。R2 记录为 17 个 candidate_basis_checked 和 7 个 candidate_basis_gap，缺口为 FP_P01、FP_P02、FP_P03、FP_P04、FP_P05、FP_P08、FP_P09；正式批准数量为 0。这是候选依据核验进展，不能等同于当前现场事实成立或法规依据正式获批。

继续完成当前阶段整包验收：逐例补齐依据核验、逐项验收清单和实际搜索验证，完成后交给架构审核。不得擅自发布、提升正式批准状态或扩大到下一阶段。历史 R1 handoff/output-checks 不代表当前 R2 最终验收。

## 检查与预览

私有数据恢复后运行：

```sh
node --test tests/field-pilot-search.test.mjs
python -m unittest discover -s tools/pipeline/tests -p test_field_profiles_pilot.py
python tools/v4/build_unified_release.py --out <独立预览目录> --as-of 2026-09-30 --field-profiles-pilot
```

在预览页实际验证可燃气体报警、防爆电气、灭火器及反例分流。构建器校验候选审核指纹，内容或上游依赖变化后必须重新审核，不能自动重签。普通构建不加试点开关；不要向 current 或 dist 构建试点。

## 隐私与部署

内部企业材料、法律原文/PDF和原始工作簿不进入本公开分支。凭据和个人敏感信息不进入交接上传；待核或已扣留内容记录在私有 exclusions.json。原始母库完整性核查不属于本次上传范围。

已检查基线的三个 GitHub Actions 工作流：生产部署仅 push/main 或 workflow_dispatch/main；本 handoff 分支 push 不触发生产部署。原执行分支、main、仓库可见性和访问权限均未修改。交接不创建 PR，不触发发布。
