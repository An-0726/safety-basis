# 数据流水线

架构决策与迁移验收见 [DATA_ARCHITECTURE_V3.md](../docs/DATA_ARCHITECTURE_V3.md)。

已实现：原始来源导入、SQLite 无损迁移、多 Sheet Excel 编辑往返、候选入库/检查项拆分、隐患合并、证据核验记录和严格发布包生成。
另已实现多布局自动导入、法规/版本/条款目录提案、法规身份合并、本地原件库及网站全文检索。最新范围见 [本轮交付](../docs/DELIVERY_20260909.md)。
`content/` 和根 `data/` 只作为过渡期线上基线保留。新流水线生成完整静态发布包，并由选择文件和 CI 在隔离目录验证；尚未切换生产。

- [母库迁移与备份](../docs/MASTER_MIGRATION.md)
- [Excel 编辑往返](../docs/EXCEL_EXCHANGE.md)
- [多来源入库、检查项拆分与合并](../docs/ADMISSION.md)
- [核验、发布命令与真实试跑结果](../docs/VERIFICATION_PUBLISH.md)
- [法规目录与身份合并](../docs/CATALOG.md)
- [全文库与统一网站构建](../docs/FULLTEXT_LIBRARY.md)

```text
source/
  imports/          本地投递，忽略 Git
  archive/          按文件 SHA256 保存原件，忽略 Git
  staging/          intake.sqlite3：来源、原始行、候选、导入记录，忽略 Git
  mappings/         可复用字段映射配置，提交 Git
  schemas/          表结构、Excel 交换契约，提交 Git
  master/           safety.sqlite3 正式母库，忽略 Git
  library/          私有原件、全文索引和待 OCR 文件，忽略 Git
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

检查表使用 `source/mappings/inspection-summary.json`，符合项原始描述留白而保留依据/原文；通用隐患模板另行拆分。新增法规/版本、条款、依据关联、隐患合并和已确认法规身份修订均使用受控提案接口。

生成隔离网站数据包：

```text
python tools/pipeline/manage.py site --as-of YYYY-MM-DD --output source/releases/NEW_RELEASE
python tools/pipeline/manage.py verify-site --output source/releases/NEW_RELEASE
python tools/pipeline/prepare_site.py --output NEW_HOSTING_DIR
```

`source/releases/site-selection.json` 固定 CI 检查的候选包及 releaseHash。分支 CI 只构建 artifact；正式 Pages 发布仅允许在 `main` 手动触发。当前候选范围见 [架构验收](../docs/ARCHITECTURE_ACCEPTANCE_20260909.md)。母库、原件与私有工作材料须另行备份，Git 不包含这些文件。
