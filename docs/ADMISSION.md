# 多来源入库与隐患合并

`intake.py` 保存原件、原始行和待整理候选；`admission.py` 把审阅后的候选写入规范化母库。两者不推断法规已核验，也不写网站 JSON。母库位置及备份要求见 [迁移与对账](MASTER_MIGRATION.md)。

## 原始检查结果与通用隐患分开

来源查看表的前三列固定表达为：**隐患描述、依据法规、法规原文**。现场不符合时描述实际缺陷；符合时隐患描述留白，依据与原文照常保留。原文件若把“符合”写进隐患描述，原值仍留在来源中，不据此生成一个叫“符合”的隐患。

通用隐患模板另外整理：先确认提取的依据、原文及列对应关系，再把一条检查要求拆成若干独立缺陷。例如原现场结果为“符合”，仍可从对应要求提炼供以后检查使用的缺陷模板；这不改变原报告的现场结论。模板保留适用条件和整改方向，不把规范要求的机械否定当成法规终审结果。

检查项目使用 `recordType=inspection`。程序不会把其标题直接当成隐患；必须审阅拆分、复用已绑定模板或暂缓。

## 多个文件怎样导入

在仓库根目录运行；依赖见 `tools/pipeline/requirements.txt`。

```text
python tools/pipeline/intake.py source/imports --mapping source/mappings/default.json
```

同一配置可导入多个同布局的 XLSX、CSV 或对象数组 JSON。不同布局可分别指定配置，或由注册表按 Sheet 和明确表头组合自动选择；未知布局或同等候选会拒绝并留下诊断。表头别名、Sheet、表头行、CSV 编码、JSON 数组位置由 mapping 描述，不按文件名重写程序。

检查表汇总使用独立映射：

```text
python tools/pipeline/intake.py source/imports/inspection --mapping source/mappings/inspection-summary.json
```

需要让同一目录中的不同 Sheet/表头自动路由时，使用注册表入口（法规台账会写入独立的 `law-registers.sqlite3`）：

```text
python tools/pipeline/imports.py source/imports --registry source/mappings/registry.json
```

注册表中的 `auxiliarySheets` 只按已登记的 Sheet 名和表头签名跳过统计、说明、差异等辅助页，并在逐源回执中记录；未登记的业务 Sheet 会拒绝整本来源并保留诊断。

`inspection-summary.json` 同时保留检查结果、现场情况、来源示例等私有信息。`default.json` 识别到非空检查结果也转为检查项目。字段歧义或缺失会报错；列内容语义错位仍须整理者识别，不能只靠表头判定成功。`.xls`、报告第五章的自动提取、扫描件和复杂表格适配不在当前导入器范围。

文件 SHA-256、原始行、解析版本和配置均保留。同样的文件与配置重复导入不会增加候选；改名保留新路径，内容变化形成新来源。解析程序版本从 `intake-v1` 升为 `intake-v2` 后，允许重新解析，旧批次不被覆盖。

## 小批次审阅与提交

```text
python tools/pipeline/admission.py plan --limit 3 --output source/proposals/admission-001-review.json
python tools/pipeline/admission.py propose --review source/proposals/admission-001-review.json --output source/proposals/admission-001.json
python tools/pipeline/admission.py apply --proposal source/proposals/admission-001.json --actor reviewer-name
```

先执行 `plan`，由 AI 或整理者填好每项 `decision` 后再执行 `propose`，审阅具体差异后 `apply`。JSON 是 AI 与工具的交换材料，用户无需手写。默认每批 20 项；可用重复的 `--candidate D_...` 精确指定样板，不能依赖候选排序代表 Excel 行号。

`--db`、`--staging` 是全局参数，须放在子命令前。隔离演练同时指定母库副本和 staging；`apply --archive <隔离归档目录>` 可将原件也保存在副本布局内。

| 操作 | 用途 |
| --- | --- |
| `create` | 普通隐患候选新建待整理隐患 |
| `attach` | 普通候选补充既有隐患的来源，或复用本批 `new:<candidateId>` |
| `derive` | 尚未入库的检查项目拆为 1–30 个模板，每个模板单独 create/attach |
| `reuse` | 重复检查项目补充来源，复用此前绑定的全部模板 |
| `defer` | 暂缓处理，保留候选及审阅理由 |

`derive` 必须填写审阅后的 `basis`、`quote`、`sourceReviewed=true` 和 `hazards` 数组；每个模板包含 `ref/title/conditions/measures/action/target/reason`。`sourceReviewed` 仅表示检查过提取对应关系。原始检查结果与原值不被覆盖；拆分依据、模板和决定另存 `intake_derivations`。

新隐患使用 `H_` 加 UUID 的前 26 位大写十六进制，唯一约束冲突时重试；提交回执保存临时引用到正式 ID 的映射。ID 与标题和 Excel 行号无关，重复提交返回原回执，不重新分配 ID。旧 H001–H081 保留。

新条目一律 `待整理`，不自动创建法规、条款或通过记录。原始法规引用先保存在来源和拆分材料中；正式依据必须经过后续法规身份、版本、条款与关联整理。

## 去重和合并

文件按字节哈希去重；候选按全部已映射语义字段（除外部编号）规范化哈希精确聚合，来源行全部保留。否定词、数字、单位、版本和条号不会被删除。原始现场事件不会因模板复用被认定为同一事件。

知识层相似标题只用来召回建议。整理者仍要比较缺陷对象、阈值、地区、条件和措施；不得按相似度自动合并。两个既有隐患可生成明确合并提案：

```text
python tools/pipeline/admission.py merge --source H_SOURCE --target H_TARGET --reason "经审阅属于同一缺陷和适用条件" --output source/proposals/merge-001.json
python tools/pipeline/admission.py apply --proposal source/proposals/merge-001.json --actor reviewer-name
```

来源隐患保留并标记 `merged`，目标保持 ID 和正文、追加来源及标签并退回待核验。迁入关联重新核验；相同条款的关系差异保存在提案与旧记录中，不静默采用来源结论。合并循环、关闭目标、过期提案和错误外键均拒绝。网页对未进入当前已核验包的旧 ID 显示明确的未发布/已撤下提示；合并去向映射可在后续需要保留旧链接时扩展。

母库更新、来源绑定、合并历史和回执在同一事务完成。原件按内容哈希归档，失败不覆盖旧文件；事务失败时可能留下未引用的内容归档，可保留而不视为成功入库。提交器重新检查来源 SHA、原始行映射和业务规则，重算提案校验和不能绕过检查。

## 已确认法规身份的修订

同一法规身份的不同版本可能具有不同的强制属性。例如 GB/T 12801—2008 与 GB 12801—2025 在官方替代关系确认后共用一个法规身份，身份文种应使用“国家标准”，各版本分别保留推荐性或强制性属性。

已确认身份不能通过普通 Excel 或目录更新直接改写。`identity.py amend` 只允许修订规范名称、制定机关、地区及文种；必须引用已登记的官方原件和具体理由：

```text
python tools/pipeline/identity.py --db source/master/safety.sqlite3 amend --law LF_EXAMPLE --changes source/proposals/identity-fields.json --evidence E_EXAMPLE --reason "官方新旧版本替代关系已确认，修正共同身份文种" --output source/proposals/identity-amendment.json
python tools/pipeline/identity.py --db source/master/safety.sqlite3 apply --proposal source/proposals/identity-amendment.json --actor reviewer-name
```

`identity-fields.json` 是字段对象，例如 `{"document_kind":"国家标准"}`。修订保留法规 ID、各版本 ID 和条款；身份退回待核验、修订号增加，依赖旧身份的核验证明失效。重新审阅身份及受影响版本后才能再次发布。状态和 ID 不可作为修订字段；原件损坏、提案过期及身份冲突会拒绝提交，操作与回执只追加保存。`apply` 自动识别身份合并和身份修订提案。

## 当前边界与真实验收

2026-09-09 用真实汇总 Excel 的 2776 行验证了解析，**只取第 2、3、354 行进入隔离母库，拆出 7 个待整理模板**。没有批量 AI 转译或法规终审。原件和正式母库哈希均未改变。

当前已具备入库、来源复用、隐患合并、已有记录 Excel 编辑和 [核验发布](VERIFICATION_PUBLISH.md)。新增法规/版本/条款/一般依据关联、法规身份合并、条款定位冲突解决、标签维护和完整现场事件表仍需专门的提案接口；不能靠直接写数据库或修改 Excel 只读列补过门禁。
