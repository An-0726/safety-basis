# 普通隐患详情的逐K法源适用范围

`hazard.basisRefs` 在原 `clauseId`、`clauseShard`、`role` 之外增加：

- `linkId`：原始当前 Gate 通过的精确 K 稳定ID
- `applicability`：该 K 的原字符串，保留换行与空白，不由 H.conditions、整条规范、相邻依据、行业标签或标题推断
- `jurisdictionCode`：该 K 的原值；缺失时为 null，不擅自补成全国

一个 H 对应多个 K 时，每个 K 单独投影。即使两个K指向同一C且role相同，也分别保留，不能按C去重丢失条件。顺序按role、C、K确定性排列。

新字段只陈述原审核关联的法源范围，不能代替现场事实核验、扩大为全行业适用，或把整条法规中所有列项都当成此H的依据。特别是轻工锂离子电池储存缺陷改连C_PDDB_8时，必须保留K中“轻工企业／第八条第（七）项”的限定；规范页可展示整条第八条，而当前H只能使用经审的具体范围。

UI应在每条依据卡、复制整改条目和复制完整资料中逐K显示“本条依据适用范围”。旧包未提供这些字段时可维持旧呈现，不能在浏览器端猜测或制造边界。新构建的严格verifier则必须逐字段、逐K检查完整新契约。

`tools/v4/basis_refs.py`只做allowlist和类型/常见私有路径检查，无源事实写入。新增文本非法或疑有私有路径时构建中止，不默默删除范围、不序列化内部字段。调用方仅传既有Gate通过且属于该H的K；构建与验证均复用纯投影函数，verifier独立从当前源枚举该H全部当前K，因此换K、串范围、漏K、删边界或重封装哈希均无法冒充有效包。

field profiles的 `bases` 原已保留精确K、applicability和jurisdictionCode，本次不改该payload；验收进一步要求其每个basis与普通hazard.basisRefs的K及范围完全一致。

验证：`python -m unittest discover -s tools/pipeline/tests -p test_basis_scope_release.py -v`，覆盖不同C、同C不同K、不同H、多范围不互串、原样空白/null、拟议关联隔离、私有/畸形字段阻断和重封装篡改。
