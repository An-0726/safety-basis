# 数据流水线

架构决策与迁移验收见 [DATA_ARCHITECTURE_V3.md](../docs/DATA_ARCHITECTURE_V3.md)。

已实现：原始来源导入、SQLite 无损迁移、多 Sheet Excel 编辑往返、候选入库/检查项拆分、隐患合并、证据核验记录和严格发布包生成。
`content/` 仍是过渡期生产构建输入，`data/` 仍由原构建器生成；新发布器生成隔离包，尚未切换生产。

- [母库迁移与备份](../docs/MASTER_MIGRATION.md)
- [Excel 编辑往返](../docs/EXCEL_EXCHANGE.md)
- [多来源入库、检查项拆分与合并](../docs/ADMISSION.md)
- [核验、发布命令与真实试跑结果](../docs/VERIFICATION_PUBLISH.md)

```text
source/
  imports/          本地投递，忽略 Git
  archive/          按文件 SHA256 保存原件，忽略 Git
  staging/          intake.sqlite3：来源、原始行、候选、导入记录，忽略 Git
  mappings/         可复用字段映射配置，提交 Git
  schemas/          表结构、Excel 交换契约，提交 Git
  master/           safety.sqlite3 正式母库，忽略 Git
  exchange/         Excel 导出、隔离试跑与私有差异报告，忽略 Git
  proposals/        模型分批结果与提交提案，忽略 Git
  releases/         仅已核验、已审阅公开字段的自动发布快照，提交 Git
```

导入及基础检查：

```bash
python -m pip install -r tools/pipeline/requirements.txt
python tools/pipeline/intake.py source/imports --mapping source/mappings/default.json
python -m unittest discover -s tools/pipeline/tests -v
node --test tools/tests/*.test.mjs
node tools/build-data.mjs
```

支持 `.xlsx`、UTF-8 CSV、对象数组 JSON。未知布局只需增加映射文件；不根据文件名写专用程序。
Excel 合并表头、标题行等用 `sheet` / `headerRow` 明确指定。歧义或缺少字段会报错，原件仍归档。
同一文件同一解析配置重复导入不增加记录；不同文件完全相同的候选归并，但各自原始行保留。
导入成功不表示法规核验通过。`.xls` / PDF / 扫描图像暂不支持，先保留原件后由独立适配器转换。

检查表使用 `source/mappings/inspection-summary.json`，符合项原始描述留白而保留依据/原文；通用隐患模板另行拆分。新增法规/条款/一般依据关联、法规身份合并及条款冲突解决接口仍待实现。

生成隔离网站数据包：

```text
python tools/pipeline/manage.py publish --as-of YYYY-MM-DD --output source/exchange/release-preview-001
```

当前真实公开样板为 `source/releases/pilot-20260909/release.json`，只有 4 个隐患，不能替代整站数据。母库、原件与私有工作材料须另行备份，Git 不包含这些文件。
