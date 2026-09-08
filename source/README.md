# 数据流水线（第一阶段）

架构决策与迁移验收见 [DATA_ARCHITECTURE_V3.md](../docs/DATA_ARCHITECTURE_V3.md)。

原始来源导入原型独立运行，不接入生产构建、不修改既有核验状态。
现已完成第二阶段第1步：正式 SQLite 母库与旧数据无损迁移，运行方式见 [MASTER_MIGRATION.md](../docs/MASTER_MIGRATION.md)。Excel 双向编辑和发布切换尚未启用。
`content/` 仍是过渡期构建输入，`data/` 仍由原构建器生成。

```text
source/
  imports/          本地投递，忽略 Git
  archive/          按文件 SHA256 保存原件，忽略 Git
  staging/          intake.sqlite3：来源、原始行、候选、导入记录，忽略 Git
  mappings/         可复用字段映射配置，提交 Git
  schemas/          表结构、Excel 交换契约，提交 Git
  master/           第二阶段 safety.sqlite3 正式母库，忽略 Git
  exchange/         第二阶段 Excel 导出与修改提案，忽略 Git
  proposals/        第二阶段模型分批结果，忽略 Git
  releases/         第二阶段仅已核验、已脱敏的自动发布快照，提交 Git
```

第一阶段可执行：

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

正式母库的历史迁移已实现；Excel 双向交换、人工合并提交器、核验发布器的接口已设计，尚未切换生产。详见架构文档的实施边界和母库迁移文档。
