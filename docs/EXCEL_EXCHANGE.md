# Excel 母库编辑往返（exchange-v1）

SQLite 是唯一母库，Excel 是带版本的查看和编辑快照。网站 JSON 仍是构建产物。本工具已经实现 **导出 → 修改 → 差异提案 → 单事务提交**；Excel v1 只更新已有核心记录，不通过新增/删行表达入库和合并。[入库/隐患合并](ADMISSION.md)、[法规目录/标签/别名](CATALOG.md) 及 [核验/隔离发布](VERIFICATION_PUBLISH.md) 使用独立提案接口。

新收到的多布局来源 Excel 先放入 `source/imports/`，使用 `tools/pipeline/imports.py` 和 `source/mappings/registry.json` 按 Sheet/表头路由到私有 intake 数据库；不要把来源文件当作母库编辑快照直接提交。

## 工作簿组织

| Sheet | 内容 | v1 维护范围 |
| --- | --- | --- |
| 说明 | 使用规则、格式版本、母库状态指纹、导出时间 | 工具生成 |
| 隐患库 | 隐患标题、描述、整改、分类、条件等 | 黄色内容列可编辑 |
| 法规库 | 法规身份名称、机关、地域、文种 | 临时身份内容可编辑；已确认身份使用后续身份审查流程 |
| 法规版本 | 每个法规版本的文号、名称、效力、日期、来源 | 黄色内容列可编辑，有效性判断仍需核验 |
| 条款库 | 法规版本 ID、条款定位、完整原文、来源 | 黄色内容列可编辑；已确认或冲突中的定位不能靠 Excel 修改解除 |
| 依据关联 | 隐患与条款 ID、依据角色、优先级、适用性 | 已有关系的黄色内容列可编辑，外键只读 |
| 隐患标签／法规别名／替代关系 | 规范化的附属记录 | 只读查看 |
| 原始来源／来源关联／来源定位 | 文件身份、来源行、Sheet、行号、JSON Pointer | 只读追溯 |
| 核验记录 | 核验对象、revision、结果、审核人和证据 ID | 只读查看，不能用单元格制造通过记录 |

灰色列只读，黄色列可编辑；行排序不会改变身份。长条款保留全文，默认行高设上限，可展开行高或编辑栏阅读。文本列保持文本类型，日期输入 `YYYY-MM-DD`。内容超过 Excel 的 32767 字符单元格限制会拒绝导出，不截断。

来源追溯路径是：`实体 ID → 来源关联.source_row_id → 来源定位.source_id → 原始来源`。原文仍保留在原件归档，法规与条款不再嵌入每条隐患。

## 三个命令

在仓库根目录安装依赖：

```text
python -m pip install -r tools/pipeline/requirements.txt
```

1. 从最新母库导出，文件名每轮更换，已有文件绝不覆盖：

```text
python tools/pipeline/exchange.py export --output source/exchange/master-round-001.xlsx
```

2. 修改黄色内容列，在该行“操作”填写 `update`，保存后生成提案：

```text
python tools/pipeline/exchange.py propose --workbook source/exchange/master-round-001.xlsx --output source/proposals/round-001.json
```

程序输出变更数量和对象 ID。JSON 提案完整列出修改字段、修改前后内容、自动状态调整、基础 revision、工作簿 SHA-256 和母库状态指纹；它是程序生成的审阅材料，不要求人工编写。

3. 审阅具体差异后提交，并登记操作者：

```text
python tools/pipeline/exchange.py apply --proposal source/proposals/round-001.json --actor reviewer-name
```

`--db` 是全局参数，必须放在子命令前；默认定位仓库内 `source/master/safety.sqlite3`，不依赖当前运行目录。演练时指定母库副本：

```text
python tools/pipeline/exchange.py --db path/to/test.sqlite3 apply --proposal source/proposals/round-001.json --actor test-reviewer
```

操作者字段是本地审计信息，不是账号权限或签名认证。提案校验和用于检查文件损坏；即使有人重算校验和，提交器仍独立执行同一套字段权限、降级、值域和审计一致性规则。

## 校验与事务规则

- 读回先验证全部 Sheet、固定列、ID 集合、revision、外键、类型和只读内容。新增行、删行、重复 ID、修改外键、未知有值列、公式、错误单元格均拒绝，不静默丢弃。以文本保存的 `=...` 是普通原文，导出时不会转为公式。
- 有修改却未标记 `update`，或标记了 `update` 却没有变化，都会提示修正。原样读回和仅排序为零差异。
- 采用保守的整个母库状态指纹。导出后任何其他内容或核验记录发生变化，本轮工作簿和提案都视为过期，须重新导出并重新提出修改；v1 不自动合并并发编辑。
- 导出和提案各使用一个只读事务；工作簿哈希与解析使用同一份字节。提交使用 `BEGIN IMMEDIATE` 串行写入，锁内再次核对母库和所有变更。
- 修改增加实体 `revision`、清空其旧 `checked`，并把当前核验状态改为 `待核验`。已失效、已废止、已合并或已排除记录保持关闭，内容修改不重新启用它们。法规版本的有效性判断与核验状态分开，填“现行有效”不会获得“已核验”。
- 不新增 `verification.passed`，不删除历史核验。涉及条款定位的修改也不能新造重复条款；旧的两组定位冲突保留，需后续身份审查解决。
- 全部实体更新与 `change_sets/change_events` 一次提交，历史记录保存前后值和版本并禁止覆盖/删除。旧母库首次实际提交时才增加变更记录表，升级与数据变更共同回滚。空提案返回 `no_changes`，不写数据库。
- 数据库缺失、过期提案、约束异常、输出文件已存在等情况返回非零退出码。输出先写完整临时文件再原子安装，不能覆盖数据库、输入工作簿或其他已有成果。

## 与现有迁移、网站的关系

`master.py verify` 是“是否完整迁移旧来源”的对账工具；正常编辑之后，它仍会报告与旧来源的差异，这不等于编辑失败。编辑流程自身检查 SQLite 完整性、外键、快照、版本和业务规则，变更历史记录解释内容为什么变化。迁移原件、旧 raw payload、来源定位和 `restore` 能力继续保留。

当前母库没有接入生产构建，本工具不会写 `content/` 或 `data/`。既有公开发布门禁不变。严格母库发布器现已逐层检查 hazard/law/version/clause/link 的当前 revision、依赖版本、核验证据和失效状态；输出为新隔离目录，不能仅凭 Excel 状态列发布。

通用原始 Excel 导入继续使用 `intake.py`，与这里的“编辑已有母库实体”分工不同；2776 条仍只是其中一个来源。新增法规/条款/一般依据关联、法规身份合并与条款冲突解决需继续补齐受控提案接口。

工作簿、提案、SQLite 和原件归档放在 `source/exchange/`、`source/proposals/`、`source/master/`、`source/archive/`，已由 Git 忽略。定期一起备份；仓库提交工具、模式、文档和测试即可。
