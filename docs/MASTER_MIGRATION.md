# 正式母库迁移与对账

本阶段把 `content/` 的四个基础表和 `content/batches/*.json` 全部写入独立 SQLite 母库。迁移会同时归档 `content/`、`data/` 内所有文件的原始字节（包括 README）；文件按 SHA-256 放在 `source/archive/<sha256>/original`，数据库保存来源路径、来源 commit、文件大小和归档引用。默认布局中的归档引用相对数据库目录保存，数据库与归档目录按原有相对布局一起备份，可搬到新目录恢复。

## 执行

在仓库根目录运行：

```text
python tools/pipeline/master.py migrate
```

可用参数是 `--repo`、`--db` 和 `--archive`，用于隔离验收：

```text
python tools/pipeline/master.py migrate --repo <repo> --db <empty>/safety.sqlite3 --archive <empty>/archive
```

首次迁移先解析、检查 ID 和引用，再在临时 SQLite 文件中执行单事务，成功后原子安装到目标路径。任何重复 ID、外键断链、约束错误都会失败并移除临时库；已有母库不会被覆盖。相同内容（由排序后的路径、字节 SHA-256 清单确定）再次运行返回 `already_migrated`，即使 Git commit 变化也不会增加记录。内容变化会明确拒绝并提示使用后续 change-set 流程。

## 对账与恢复

```text
python tools/pipeline/master.py verify --db source/master/safety.sqlite3 --repo .
python tools/pipeline/master.py restore --db source/master/safety.sqlite3 --output <empty-directory>
```

`verify` 以只读方式打开数据库，输出：正式表计数、ID 集合、状态分布、SQLite `integrity_check`、外键检查、逐源文件及归档 SHA-256、逐实体 JSON Pointer/raw payload、正式列与原始字段语义对账、标签/别名顺序、法规替代关系和未解决冲突。对账失败退出码为 1。`restore` 要求目标目录为空，拒绝绝对路径或 `..` 穿越，并从归档还原所有登记的 `content/`、`data/` JSON；还原后可逐文件 SHA-256 对比原库。

## ID、身份与状态

旧 `Hxxx`、`Cxxx` 原样保留。旧 `Lxxx` 作为 `law_versions.id` 保留，同时建立对应的 `laws.id = LF_Lxxx` 身份行；本轮不按相似名称、年份或标准替代关系自动合并，身份标记为 `provisional`。来源明确写出的 `replaces`/`replacedBy` 进入 `law_successions`，不删除任一版本。无 ID 的旧 link 由 hazard、clause、role、priority 的规范化内容稳定生成 `K_` ID。

每个实体保留完整 raw payload、来源文件和 JSON Pointer，未知字段不会丢失。`hazard_tags` 与 `law_aliases` 保存 ordinal，保证数组顺序可恢复。旧状态原样进入正式列；若源对象带有状态，只追加 `verification.result = legacy_inherited`，不生成 `passed`，也不虚构审核人、证据或当日核验结论。

C070/C071（L010 第9条）和 C072/C073（L001 第二十一条）均完整保留。相同法规版本/条款定位的冲突登记在 `migration_conflicts`，状态为 `unresolved`；因此不能用唯一键篡改条款号、拼接原文或丢弃关联。未解决冲突必须在后续人工/模型核验流程中处理后才能进入发布门禁。

`verify` 是原始迁移对账工具，需要传入对应的旧资料快照；将来正常编辑母库后应使用单独的母库业务校验器，不能再要求正式内容等于旧来源。完整 V3 核验发布器和 Excel 双向编辑尚未实现。

本入口只负责历史数据迁移、归档和对账，不编辑 Excel，不导入 2776 来源，不开展法规终审，不修改 `content/`、`data/` 或 `main`，也不执行网站发布。

迁移后的旧法规记录来源和状态继承记录指向 `law_version/Lxxx`；临时法规身份通过 `law_versions.law_id` 追溯。旧 link 没有核验状态，因此93个依据关联初始为待核验，不代表原网站32条隐患的状态被改动。L010/L011保留两个临时身份，本步骤未宣称完成法规身份去重。
