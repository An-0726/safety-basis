# 1,929 目标隐患与 knowledge 全量对账

> 本报告由 `tools/maintenance/reconcile_hazard_target_set.py` 从修订工作簿与当前 `knowledge/` 确定性生成。工作簿只用于目标 ID 和编辑状态核对，不作为法规原文证据。

## 输入与结论

- 工作簿：`隐患库_1929条_新版口径全部整改完成_20260914.xlsx`，SHA-256 `c84ec965ce808c780547842a1a82cb7eca01d0a8fdd018c054414b2b5be24a6f`，`隐患明细_修订后!A2:R1930`。
- 工作簿有 1929 行、1929 个唯一 ID；knowledge 有 2014 个唯一 hazard 实体。
- 1,929 个目标 ID 全部直接存在于 knowledge；目标缺失 0，knowledge 目标外实体 85。
- `2,014 - 1,929 = 85` 只是集合差额，不等于 85 条重复。85 条已逐项分类见机器映射和附录。
- merge 图共有 64 条边；缺失目标 0，循环 0。
- 标题逐字一致 1861 条；统一中英文标点和空格后仍有 9 条实质表述差异。

## 目标集分类

| 分类 | 数量 | 解释 |
| --- | ---: | --- |
| `target-current` | 1409 | 当前 active、无 mergedInto；与现有 1,409 条正式发布基线一致。 |
| `target-merged-alias` | 8 | 工作簿目标 ID 仍保留，但已指向另一目标 ID；不是独立发布实体。 |
| `target-proposed` | 512 | 仍为 proposed，保留在 knowledge，不进入正式公网。 |

### 621 修订与 1,308 保留的实际去向

| 工作簿状态 | knowledge 分类 | 数量 |
| --- | --- | ---: |
| 原审查通过/保留 | `target-current` | 1273 |
| 原审查通过/保留 | `target-merged-alias` | 4 |
| 原审查通过/保留 | `target-proposed` | 31 |
| 已修订 | `target-current` | 136 |
| 已修订 | `target-merged-alias` | 4 |
| 已修订 | `target-proposed` | 481 |

## 目标外 85 个 knowledge 实体

| 分类 | 数量 | 解释 |
| --- | ---: | --- |
| `knowledge-extra-historical-non-hazard` | 1 | 经终审认定为正向事实、非隐患，仅保留追溯。 |
| `knowledge-extra-merged-history` | 56 | 已有 mergedInto 的历史稳定 ID。 |
| `knowledge-extra-proposed-non-target` | 7 | 不在目标工作簿且缺少完整正式 Gate，作为 proposed 范围复核 backlog 保留。 |
| `knowledge-extra-split-parent` | 21 | 已拆分为更具体子隐患的历史父项。 |

## 状态复核结果

### 目标集内已合并并保留为 superseded alias（8）

| 工作簿行 | ID | 标题 | mergedInto | review |
| ---: | --- | --- | --- | --- |
| 244 | `H_128CF6B2AEFB46EA98D63BE037` | 排放有腐蚀性的气体时,排气筒,未采用防腐设计 | `H_45A24EA090E13562E178D67F6E_1` | superseded |
| 833 | `H_15577_6_3_2_1` | 直接用于盛装起电粉料的器具、输送粉料的管道（带）等，未采用金属或防静电材料制成 | `H_12158_9_10_1` | superseded |
| 834 | `H_6F52BBD3B8764A2EB1BD84D811` | 管道连接法兰,未采用跨接线 | `H_15577_8_1_5_1` | superseded |
| 851 | `H_15577_4_7_1` | 粉尘爆炸危险场所的出入口、生产区域及重点危险设备设施等部位，未设置显著的安全警示标识 | `H_C8694BE798B94E39B4566EAB6B` | superseded |
| 973 | `H_998C5607F7EAB6589B9DD35598_2` | 依法应当进行消防验收的建设工程，未经消防验收或者消防验收不合格，擅自投入使用 | `H_E802C3AF73D1BDF70B0251EE4A_1` | superseded |
| 979 | `H_A6FFD804B89A850BBF832DC4_1` | 储存危险化学品的单位未建立危险化学品出入库核查、登记制度 | `H_03BA3BFFA73DDEFE94C3ACED_1` | superseded |
| 1077 | `H_GB12801_5_4_6_1` | 危险性作业场所未设置安全通道 | `H_B085FE55797E498897B61DCA10` | superseded |
| 1816 | `H_3B764981E731EA8D2F1B2B0C59_1` | 设备和管线未按有关标准的规定涂识别色、识别符号和安全标识 | `H_608147EE09234EBC92B53F842A` | superseded |

### 目标外 proposed 范围复核 backlog（7）

| ID | 标题 | hazard review | links（verified/rejected/无审阅） |
| --- | --- | --- | --- |
| `H_02FEFD347E114E1E979C9589AF` | 生产经营单位未急预案分为综合应急预案、专项应急预案和现场处置方案 | rejected | rejected=1 |
| `H_0647B65088564B789D64080EF1` | 按照国家标准、行业标准配置消防设施、器材,设置消防安全标志。 | rejected | rejected=1 |
| `H_1F19FA1B951D46C1971E9B59B4` | 门窗,未朝外开启 | verified | rejected=1 |
| `H_23D109AF79FF0519BCD1837EC6_1` | 未尽量选用自动化程度高的设备 | verified | 0 |
| `H_3A5DEC6C74244A949CE3BC9A42` | 空压机房内配电柜柜门未保持常闭状态 | verified | rejected=1 |
| `H_5B89D7164D2C4B6E983663B009` | 具备与本单位所从事的生产经营活动相未的安全生产知识和管理能力 | rejected | rejected=2 |
| `H_6E7E9CD077AD4918962EBA6EAE` | 当不可避免时,必须具有可靠的防洪、排涝措施 | rejected | rejected=2 |

### 工作簿与 knowledge 标题规范化后仍不同（9）

这些 ID 集合一致，且对应 hazard review 均为 verified；Git 历史显示其在正式核验/官方来源核验批次中改写，按已审阅专业化表达保留，不用工作簿旧句式反向覆盖。

| 工作簿行 | ID | 工作簿标题 | knowledge 标题 |
| ---: | --- | --- | --- |
| 135 | `H_AD6D645EFFCC4F3FB9624C20C4` | 气瓶暂存区域无标识,未设置安全警示标示 | 气瓶暂存区域无标识，未设置安全警示标识 |
| 899 | `H_SGSG_26_1` | 事故调查组有权向有关单位和个人了解与事故有关的情况，并要求其提供相关文件、资料，有关单位和个人拒绝 | 有关单位或个人拒绝配合生产安全事故调查或提供相关文件资料 |
| 945 | `H_JSXF_72_2` | 任何单位和个人擅自清理、移动火灾现场物品，隐瞒事实真相或者干预、阻挠火灾事故的调查处理 | 擅自清理、移动火灾现场物品或干预、阻挠火灾事故调查 |
| 949 | `H_85ED13719789340D08661C69ED_1` | 任何单位和个人阻挠和干涉对事故的依法调查处理 | 阻挠、干涉生产安全事故依法调查处理 |
| 950 | `H_SGSG_7_1` | 任何单位和个人阻挠和干涉对事故的报告和依法调查处理 | 阻挠、干涉生产安全事故报告或依法调查处理 |
| 1200 | `H_21EE48E691609CFAFE81743D58_3` | 大型群众性活动的举办者需要设置临时性建筑物、构筑物及设施设备的，未对其安全性进行检测、检验等 | 大型群众性活动临时建筑、构筑物及设施设备未经安全检测检验 |
| 1263 | `H_D42B615FCB78B8498CE2F6C9D6_2` | 对重大生产安全事故隐患，安全总监有权直接向负有安全生产监督管理职责的部门报告，生产经营单位干涉其依法履行职责 | 生产经营单位干涉安全总监依法报告重大生产安全事故隐患 |
| 1828 | `H_3AA7E23DF886452F6C6808D991_1` | 调查组有权向有关单位和个人了解与火灾事故有关的情况，并要求其提供相关文件、资料，有关单位和个人拒绝 | 有关单位或个人拒绝配合火灾事故调查或提供相关文件资料 |
| 1834 | `H_80308DC66C8AAA60F187214351_3` | 赶赴火灾现场或者应急救援现场的消防人员和调集的消防装备、物资，需要铁路、水路或者航空运输的，有关单位未优先运输 | 应急救援人员、装备和物资需要铁路水路航空运输时有关单位未优先运输 |

## 85 条目标外实体逐项解释

| ID | 分类 | lifecycle | 归并/拆分去向 | 标题 |
| --- | --- | --- | --- | --- |
| `H058` | `knowledge-extra-merged-history` | superseded | H043 | 仓储场所在岗人员消防安全教育频次不足 |
| `H_02FEFD347E114E1E979C9589AF` | `knowledge-extra-proposed-non-target` | proposed | — | 生产经营单位未急预案分为综合应急预案、专项应急预案和现场处置方案 |
| `H_0647B65088564B789D64080EF1` | `knowledge-extra-proposed-non-target` | proposed | — | 按照国家标准、行业标准配置消防设施、器材,设置消防安全标志。 |
| `H_0AB8998CB24041C894BB326A69` | `knowledge-extra-split-parent` | superseded | H_0E92EFCE7E9E667C7BE84085, H_1810D03B12E593B41007BB5F | 未建立健全全员安全生产责任制,主要负责人(包括法定代表人和实际控制人,下同)是本企业安全生产的第一责任人,对本企业的安全生产工作全面负责 |
| `H_0E92EFCE7E9E667C7BE84085` | `knowledge-extra-merged-history` | superseded | H_14A806AFE9E84CB4B4827662 | 未建立健全并落实本单位全员安全生产责任制 |
| `H_1DB6AE75F00A4EB682FA20136E` | `knowledge-extra-split-parent` | superseded | H_75593A504C1A4EA726DFA2DD, H_431B8FEB2AB957E7454BB140, H_DF6D833C65BF5105247C55E4 | 、暂存区域,未设置安全警示标志,配备相应品种和数量的消防器材及泄漏应急处理设备 |
| `H_1F19FA1B951D46C1971E9B59B4` | `knowledge-extra-proposed-non-target` | proposed | — | 门窗,未朝外开启 |
| `H_22D804731C0D4F90A6BF2A83CD` | `knowledge-extra-split-parent` | superseded | H_03466ADE0A589C7D890736A6, H_CDCC41FC5CDA320D4E9EB9CA | 场(厂)内专用机动车辆有下列情形之一仍继续使用的,,未判定为重大事故隐患。a)定期检验的检验结论为“不合格”。b)电动车辆电源紧急切断装置缺失或失效。c)制动(包括行车、驻车)装置缺失或失效。d)观光列车的牵引连接装置及其二次保护装置缺失或失效。e)非公路用旅游观光车辆超过最大行驶坡度使用 |
| `H_23D109AF79FF0519BCD1837EC6_1` | `knowledge-extra-proposed-non-target` | proposed | — | 未尽量选用自动化程度高的设备 |
| `H_24319B1A510C4747B950BCCA6F` | `knowledge-extra-merged-history` | superseded | H_1E8A5587D5104804BF2EC4FCA4 | 公共实验室内反应釜装置区域防爆电器安装不规范,部分线路未穿管 |
| `H_293D08E1BF204915931B98A457` | `knowledge-extra-merged-history` | superseded | H_B405711EED23418BAC72F90645 | 产生粉尘、毒物的生产设备未采取密闭或通风净化措施 |
| `H_323DCD216820476B95E8153AE1` | `knowledge-extra-merged-history` | superseded | H055 | e)物品堆垛与堆垛之间的距离不小于1m |
| `H_3480C7D3E5894161B3E26CA1B0` | `knowledge-extra-merged-history` | superseded | H_582731EF84014F338DD9B04458 | 可燃性有机溶剂清洗设备设施、工装器具、地面时,未采取防止可燃气体在周边密闭或者半密闭空间内积聚措施的 |
| `H_38AB017ED1E34FCB964087B0EA` | `knowledge-extra-merged-history` | superseded | H_F692794FBBA74CFB83648A73CF | 危险化学品试剂间安全警示标志张贴在门上 |
| `H_3A5DEC6C74244A949CE3BC9A42` | `knowledge-extra-proposed-non-target` | proposed | — | 空压机房内配电柜柜门未保持常闭状态 |
| `H_44549E43707D4EBCB2D1BC7E67` | `knowledge-extra-split-parent` | superseded | H_5D5ACB4A6D45FD9CEFC4654D, H_5F45555A73771FE1F12AB88F, H_E37EF6102AE03060EDCB51D7 | 特种设备有下列情形之一仍继续使用的,未判定为重大事故隐患。a)特种设备未取得许可生产、因安全问题国家明令淘汰、已经报废或者达到报废条件。b)特种设备发生过事故,未对其进行全面检查、消除事故隐患。c)未按规定进行监督检验或者监督检验不合格。d)有4.2~4.10中规定的超过规定参数、适用范围的情形 |
| `H_46DA049AC33E40E88F9FA78093` | `knowledge-extra-merged-history` | superseded | H_3A5DEC6C74244A949CE3BC9A42 | 空压机房内配电柜柜门未保持常闭状态 |
| `H_475C71B0AA9E4C08B82E9C8B29` | `knowledge-extra-split-parent` | superseded | H_8878F6117AAEC0B4576901BA, H_0DB36410770259C5CEEB9C25, H_D9017B3895E8E59531CF8180 | 剧毒化学品、监控化学品、易制毒化学品、易制爆危险化学品,未按规定将储存地点、储存数量、流向及管理人员的情况报相关部门备案,剧毒化学品以及构成重大危险源的危险化学品,未在专用仓库内单独存放,并实行双人收发、双人保管制度 |
| `H_4873DBAC1A394BA7878AF73626` | `knowledge-extra-merged-history` | superseded | H_3B67F679C467451EA96B99072A | 物料堆放不满足要求 |
| `H_4B099AC576B249B6A7A28AE8E0` | `knowledge-extra-split-parent` | superseded | H_B1B83C549A4342EEEC8C2279, H_2CFBFBBF338B36F66DA7600F, H_87C7C1197DD2B651CFCACED5 | 、储存区域,未设置安全警示标志。灌装时,未控制流速,且有接地装置,防止静电积聚。配备相应品种和数量的消防器材及泄漏应急处理设备 |
| `H_5425D2CF14184CBEBB7245567F` | `knowledge-extra-merged-history` | superseded | H_46A4349273C34D2992F88B202F | 危险化学品试剂间内可燃气体报警器接线处护套线腐蚀脱落,未采用防爆挠性管连接 |
| `H_56B7B9F8379B4E6E93F2342596` | `knowledge-extra-split-parent` | superseded | H_14A806AFE9E84CB4B4827662, H_7593B68A4932DCFB6A61F5F7, H_F770D9BE3A5A49C9DDC7A5BF | 未遵守本法和其他有关安全生产的法律、法规,加强安全生产管理,建立健全全员安全生产责任制和安全生产规章制度,加大对安全生产资金、物资、技术、人员的投入保障力度,改善安全生产条件,加强安全生产标准化、信息化建设,构建安全风险分级管控和隐患排查治理双重预防机制,健全风险防范化解机制,提高安全生产水平,确保安全生产 |
| `H_5A680299841F47E3974FB596E4` | `knowledge-extra-merged-history` | superseded | H_54347BF9DA2E435FBB08E2EFF5 | 危化品暂存间未标明储存物品的名称、性质和灭火方法。 |
| `H_5B19995BCDF379CBC019C6BE` | `knowledge-extra-merged-history` | superseded | H_653DF6B73BC04403AD75AE9E27 | 未制定生产安全事故应急救援预案 |
| `H_5B89D7164D2C4B6E983663B009` | `knowledge-extra-proposed-non-target` | proposed | — | 具备与本单位所从事的生产经营活动相未的安全生产知识和管理能力 |
| `H_5F59F50EE244471C81C2757635` | `knowledge-extra-split-parent` | superseded | H_BF7AA7549F8E1B94012882C9, H_C1CE3A649721387F1FC0F7BE, H_1B474A2ABA0E23143E2FE451 | 严格粉尘废屑储存。粉尘废屑,未优先采用机械压块压实处理,确需采用干式储存的,未桶装加盖或袋装封口密闭。粉尘废屑进入储存场所前,未冷却至常温,不同种类的粉尘废屑不得混装储存,严禁与氧化物、过氧化物、酸、爆炸品、易燃物品等在同一场所存放。镁废屑采用袋装储存的,未单层存放,每袋之间保持一定间隙,也可采用不锈钢等不易产生铁锈的货架分层储存,严禁堆垛储存 |
| `H_62A95BDFD9C543AA8643E52470` | `knowledge-extra-merged-history` | superseded | H_05248294EEDD496B9A57C50C91 | 抛丸机区域电气不符合防爆要求 |
| `H_6306B00BE6624819BAC056740D` | `knowledge-extra-merged-history` | superseded | H_36D21B104AD34CA990E080307B | 冲压机双手按压按钮损坏 |
| `H_633B906805A84D82B0AC69088B` | `knowledge-extra-merged-history` | superseded | H_70CF6BE6FCDB433192C9456223 | 厂区通道宽度未满足防火间距等要求 |
| `H_67DD4A08FEA74E05B014D3470C` | `knowledge-extra-merged-history` | superseded | H_5125D7735DF14B5C85E19D7E28 | 设备安装区一处灭火器未成组设置。 |
| `H_6A14A125FBE94A76B2965DEEB8` | `knowledge-extra-merged-history` | superseded | H_D98B4749D74246E2A3825D5B09 | 液化石油气气瓶间缺失少“严禁烟火”、“易燃易爆” 等安全警示标志 |
| `H_6E7E9CD077AD4918962EBA6EAE` | `knowledge-extra-proposed-non-target` | proposed | — | 当不可避免时,必须具有可靠的防洪、排涝措施 |
| `H_73CFA21BD25C4D06B769660539` | `knowledge-extra-merged-history` | superseded | H_63B642CC09404DEBB250A63135 | 现场台钻安全防护罩缺失。 |
| `H_7992BED0E0864FE488C8F4007F` | `knowledge-extra-merged-history` | superseded | H_00DB7A50FF994B5DB5470A3B03 | 企业未对较大以上风险公示 |
| `H_83C122272BA54FE1AB0F410B4F` | `knowledge-extra-split-parent` | superseded | H_F53C97BEFD7761225C2B413A, H_2AE1F443127CB3AE4EFDFAA4 | 未有泄漏液体收集装置、气体导出口及气体净化装置 |
| `H_85705246544142A28E49D13338` | `knowledge-extra-merged-history` | superseded | H_62B9B3FCB70F4FF6A3BE35E1D8 | 丙烷汇流排间的风扇非防爆 |
| `H_8740A8DCB8B04C3F93B030623F` | `knowledge-extra-merged-history` | superseded | H_37630CC404984F6FB271662FC8 | 未根据本单位实际,建立安全生产投入保障、宣传教育培训、隐患排查治理、应急管理、发包(出租)管理等安全生产规章制度 |
| `H_87C7C1197DD2B651CFCACED5` | `knowledge-extra-merged-history` | superseded | H_0B99DA06B696E759C7E87DCA | 危险化学品储存区域未按标准配备相应品种和数量的消防器材及泄漏应急处理设备 |
| `H_89BC396EBC084489B0CC25B02B` | `knowledge-extra-split-parent` | superseded | H_D938BDABA6238F3520F00B78, H_9DA8116AAF559EC8BC14BA1C | 机器上,未有铭牌和操作指示、维护和安全等标牌 |
| `H_8A64C27145D64B229F53234268` | `knowledge-extra-merged-history` | superseded | H_3468C2ACFD8C44CB917C9FD791 | 易发生危险化学品事故的实验室房门未向疏散方向开启或未设置监测报警及自动灭火系统 |
| `H_8C11A178483A4168809767DCFA` | `knowledge-extra-merged-history` | superseded | H_2321884B1CF54225BFB4A9B527 | 喷粉室内有非防爆的开关插座 |
| `H_8C5C628FAFD544CF8FF58A7732` | `knowledge-extra-split-parent` | superseded | H_E3ABC75D6255A1C9F3A37C6A, H_25CEE684DF2F4D9D73BDB1AB, H_0B99DA06B696E759C7E87DCA | 、储存区域,未设置安全警示标志。在传送过程中,钢瓶和容器必须接地和跨接,防止产生静电。搬运时轻装轻卸,防止钢瓶及附件破损,配备相应品种和数量的消防器材及泄漏应急处理设备 |
| `H_8ECDE7A0067044F09C58577BEC` | `knowledge-extra-merged-history` | superseded | H_2176114794644B75A99BD28215 | b)不允许产生粉尘沉积 |
| `H_8FB5E0EC57924DEBB03721D98D` | `knowledge-extra-merged-history` | superseded | H_1094F237782E4FC9A7D58CA44E | 铝粉危废库房未采取通风措施,未安装氢气报警器,未采取防水防潮措施 |
| `H_9257C3284E2644A6BB80CC6B34` | `knowledge-extra-merged-history` | superseded | H_54D18AD4CE504AD2A8F3967B1F | 喷漆房内的可燃气体报警仪电源线路不符合防爆规范 |
| `H_97C294EEF0674528B5099D1C07` | `knowledge-extra-merged-history` | superseded | H_14E04FE43D8A43DC90F7464F41 | 废油漆桶、废稀释剂桶等危险废物未及时收集入库 |
| `H_97D66CC1DFE045BA9BF22CB9A9` | `knowledge-extra-merged-history` | superseded | H_560D75081D1F4B42BEB642811A | 四楼危险化学品试剂间内电气线路未敷设在钢管内 |
| `H_997F60F5C9034C5593A316E08F` | `knowledge-extra-split-parent` | superseded | H_3227246FFEDB65997424055F, H_07F925FDEFE56C60596FE131 | 从事焊接、切割的动火作业人员,未按规定持焊接与热切割或建筑焊工特种作业操作资格证书上岗,从事特种设备相关焊接作业人员,未按规定持特种设备作业人员证上岗,具备相应动火作业安全技能 |
| `H_9A17E143EA5B427989E78C95A3` | `knowledge-extra-merged-history` | superseded | H_0D8FC0AC95BE4E09908AD3A154 | 调漆作业使用了可以发生火花的铁质工具 |
| `H_9BC92F4558404DA9B14A721492` | `knowledge-extra-split-parent` | superseded | H_21A69E2CA823BC59272F464D, H_1C2A273765B749D654E6E278 | 仓储场所的电气线路、电气设备,未定期检查、检测,禁止长时间超负荷运行 |
| `H_9D076BD9D82444DCAA72489164` | `knowledge-extra-split-parent` | superseded | H_914777FE698BBE29C98D5253, H_9916E091141DD0179B0E4EC3, H_5B19995BCDF379CBC019C6BE | 未建立健全各级安全生产责任制和安全规章制度,并制定事故应急救援预案,各级人员,未对其所管辖范围的安全负责 |
| `H_9DCBB0D8DB5441A2A3E4811603` | `knowledge-extra-split-parent` | superseded | H_7A2AAA3D53D03F168C7ECCBB, H_4BCFEF17729F891A6144A8E0 | 未建立健全并落实生产安全事故隐患排查治理制度,定期组织排查本单位的事故隐患,通过相关信息系统如实记录事故隐患排查治理情况,并向从业人员通报。重大事故隐患排查治理情况记录保存期限不得少于五年 |
| `H_A1696721CCC94F65AE95751A5E` | `knowledge-extra-split-parent` | superseded | H_CCBA1E83E15A914C14219FE7, H_A0120A30298373EDAA8F8384 | 压力管道有下列情形之一仍继续使用的,未判定为重大事故隐患。a)定期检验的检验结论为“不符合要求”或“不允许使用”。b)安全阀、爆破片装置、紧急切断装置缺失或失效 |
| `H_A73EC0543AA24DF583F70E566B` | `knowledge-extra-historical-non-hazard` | superseded | — | 危险化学品主要以小包装形式暂存于试剂柜、仓库等处,未见与办公生活区域混杂布置情况 |
| `H_AC55E4B5240544A7AA7A1CB3F8` | `knowledge-extra-split-parent` | superseded | H_BD32095BBE999606E80E376E, H_4786C6AB880D073F73CC1A54 | 压力容器有下列情形之一仍继续使用的,未判定为重大事故隐患。a)定期检验的检验结论为“不符合要求”。b)固定式压力容器改作移动式压力容器使用。c)固定式压力容器、移动式压力容器的安全阀、爆破片装置、紧急切断装置缺失或失效。d)快开门式压力容器的快开安全保护联锁装置缺失或失效。e)氧舱的接地装置缺失或失效。f)氧舱安全保护联锁装置(联锁功能)失效 |
| `H_AD316756AE70497DBE994E0ACD` | `knowledge-extra-merged-history` | superseded | H_67FEC43961B247529D64123BB2 | 货梯缺少警示标识。 |
| `H_AF69989A559F468F8256FC000B` | `knowledge-extra-merged-history` | superseded | H_AD6D645EFFCC4F3FB9624C20C4 | 气瓶暂存区域无标识,未设置安全警示标示 |
| `H_B5737CA0B76C41E3B1F450E277` | `knowledge-extra-merged-history` | superseded | H_A1DD3641D23C4DCB92FFE32354 | 除尘系统的启动,未先于生产加工系统启动,生产加工系统停机时除尘系统,未至少延时停机10min,未在停机后将箱体和灰斗内的粉尘全部清除和卸出 |
| `H_BD9E507F756747359D0DAA6ABF` | `knowledge-extra-merged-history` | superseded | H_6D42C7EBD001444F8FC63A651E | 活性炭吸附装置管道未见安装阻火器(防火阀) |
| `H_BE977CD5E6BF4C5CA4F4A04B8A` | `knowledge-extra-merged-history` | superseded | H_5F55461A7E7E4BF5A2943EA3C6 | 设备上供人员作业的操作位置,未安全可靠,并未满足人机交互功能的要求。其工作空间,未保证作业人员的身体各部位在作业中可正常活动。危险作业点,未留有安全退避空间 |
| `H_BF58DEEC69C04BF7BDAE3A6A27` | `knowledge-extra-merged-history` | superseded | H_A8187D7204164D89B4C4EEF1B4 | 气瓶存放区域未配置灭火器材 |
| `H_C1953CE65F144427890685861E` | `knowledge-extra-merged-history` | superseded | H_8D238C134F7E42E0B22C1989CD | 危废暂存间内部分桶装液体下方无泄漏液体收集装置。 |
| `H_C2B93DD5B7D64183BE5AF8E84C` | `knowledge-extra-merged-history` | superseded | H_6D5EBB4E642F489C9717AED728 | 危险化学品库房内使用非防爆接线盒 |
| `H_C83AFF63E77544D79C00E9C740` | `knowledge-extra-merged-history` | superseded | H_772BE36081184956B7899AA306 | 一行车吊钩防脱钩装置损坏 |
| `H_CB180AFAA53646A7A9A5F9D350` | `knowledge-extra-split-parent` | superseded | H_ABBEECBC007C8F7632553BA9, H_A1A5AA5EE13A3444450315AB | 为了保护工人的职业健康安全当进人设施内部检修时,未提供一次性衣服、防护罩、防护手套等防护用品。在加药药设施旁边还,未设置洗眼液等防护设施 |
| `H_CC00D5CD2332429BBDEF3FFF4A` | `knowledge-extra-merged-history` | superseded | H_98701BEEC7434385A10BCE2AB1 | 喷漆作业结束后未能将不能继续使用的油漆及容器放到危废贮存点 |
| `H_CC4AD0C7B4064A3D8AD9B31CC0` | `knowledge-extra-merged-history` | superseded | H_6DC0BB9AF6BB4D2A9EA6F293CA | 企业较大风险风险公示栏信息错误 |
| `H_CCB3F453BA5643EFAE44FF64BD` | `knowledge-extra-merged-history` | superseded | H_366610E8AA084C77844EFFBAAD | 非水性漆的调漆间、喷漆室未设置固定式可燃气体浓度监测报警装置或者通风设施的 |
| `H_CD4406C1D7904CBB99964C7A30` | `knowledge-extra-merged-history` | superseded | H_438F526ECA2148CFA7098ABDCB | 气瓶临时储存场所无安全警示标志 |
| `H_CEAF10F03D5D472482E621D22E` | `knowledge-extra-merged-history` | superseded | H_B4C3B26745D144BD9DCD70E8F3 | 氧气瓶使用场所未张贴“严禁油脂”安全警示标志 |
| `H_D0E34E3CC9C64F458BCCDA4674` | `knowledge-extra-split-parent` | superseded | H_CA06E95820E1B8380E415A5F, H_AE64CC10CCCDBB67B2A6452E | 危险废物贮存设施选址不满足环境保护要求 |
| `H_D3DD215E0D1E4D4A99E6D2D6A9` | `knowledge-extra-merged-history` | superseded | H_323DCD216820476B95E8153AE1 | e)物品堆垛与堆垛之间的距离不小于1m |
| `H_D5781C59D4BD4E5697FB4569C1` | `knowledge-extra-merged-history` | superseded | H_B7FA977B288F493A98558722B9 | 喷漆室前部开口外侧电器不符合防爆要求 |
| `H_D68030A1FF76475CB16F6AF998` | `knowledge-extra-split-parent` | superseded | H_B552B08A4FD28A8770CDC2BB, H_68196C0A0FBDDAF0354E0F71 | 进行检修和抢修作业时,未携带氨气检测仪和正压式空气呼吸器 |
| `H_DD22573D773E4A1E87BF7CD42D` | `knowledge-extra-merged-history` | superseded | H_A4380E0A9D5B40A3BD6BED5FDF | 镀镍车间传动部位未设置防护罩 |
| `H_DEAE634C1628438D90C18D7B22` | `knowledge-extra-merged-history` | superseded | H_4CB79C3F386A43C883463C2F44 | 试验台敞开边缘未设置护栏 |
| `H_E078DE4989B64F9F826B4C4AF5` | `knowledge-extra-merged-history` | superseded | H_7D37B0E31CA14F5BA652ACE2A8 | 车间内部分消火栓无明显的标志 |
| `H_E144206DA62A4A1F83CCF8F896` | `knowledge-extra-merged-history` | superseded | H_DBB3FBAC606D4719B52CEF1A5E | 组织防火检查,及时消除火灾隐患。 |
| `H_E3ABC75D6255A1C9F3A37C6A` | `knowledge-extra-merged-history` | superseded | H_B1B83C549A4342EEEC8C2279 | 危险化学品储存区域未设置明显的安全警示标志 |
| `H_E715E6B91D5F40C8B186546C65` | `knowledge-extra-merged-history` | superseded | H_D295CB453D4543CD9BD8EE3192 | 铝粉除尘系统未安装锁气卸灰装置 |
| `H_EB182F4D7F44413CBB3C16F674` | `knowledge-extra-merged-history` | superseded | H040 | 的特种作业人员必须按照国家有关规定经专门的安全作业培训,取得相应资格,方可上岗作业 |
| `H_F280E34755FD425A9DBCDDDEB6` | `knowledge-extra-merged-history` | superseded | H_F0DB5879D1424F669BACDE8BD4 | 粉碎区域配电箱无法 正常关闭,无法达到 防尘效果。 |
| `H_F55588551E454FD9B8D1935E3E` | `knowledge-extra-merged-history` | superseded | H_9C4FE3EBE8C149EFB882B60148 | 实验室内一根临时电源线外绝缘层破损 |
| `H_F57270BED8114BB69A556DEBA2` | `knowledge-extra-split-parent` | superseded | H_02E90FC3EF2AC0B2A8FE6504, H_0A4BEEE14031157F804CCCB0 | 贮存化学危险品的仓库未配备专业技术人员或未设专人管理 |
| `H_F7900294DFC14D2785E462A8B5` | `knowledge-extra-merged-history` | superseded | H_436C69C1FB7042A981133868C2 | 吊装作业人员未佩戴安全帽 |

## 下一步

1. 8 个目标内 merged alias 已统一为 `superseded` 并重绑审阅 hash。
2. 7 个目标外且缺少完整正式 Gate 的实体已降为 `proposed`，保留稳定 ID、原审阅结论和既有证据。
3. 9 个标题实质差异均有 verified hazard review，保留 knowledge 的专业化表述。
4. PHASE 5 完成后进入 PHASE 6，按 proposed 候选的证据链缺口分批回绑，不为清零而转正。

机器可读明细：`docs/hazard-reconciliation.jsonl`。
