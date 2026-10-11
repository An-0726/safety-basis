"""公开前台展示投影。

这些函数只负责把正式源字段投影成查询和界面使用的展示字段，不改变任何
knowledge 语义；隐患分类仅按审定映射展示，不对法规效力或强制属性作新的判断。
"""

import re
import unicodedata
from collections import defaultdict


CATEGORY_ALIASES = {
    "用电安全": "电气安全",
    "机械设备安全": "机械与设备安全",
    "安全教育": "安全教育培训",
    "安全生产管理": "安全管理",
    "专项安全与EHS": "综合安全",
    # Exact label variants reviewed against the existing records and bases:
    # H_FORKLIFT_UNATTENDED_KEY, H_WORKPLACE_CHEM_SDS_MISSING, H_CF_GEN_18.
    # Navigation labels only: no equipment/chemical/legal-scope equivalence.
    "特种设备安全": "特种设备",
    "危险化学品安全": "危险化学品与危险物质",
    "设备设施安全": "设备设施",
}

# 仅合并现有展示分类；不改变正式隐患的原始 category 或逐条覆盖表。
CATEGORY_GROUPS = {
    "消防安全": "消防安全",
    "消防疏散": "消防安全",
    "特种设备": "特种设备",
    "电气安全": "电气安全",
    "机械与设备安全": "机械设备与设施",
    "设备设施": "机械设备与设施",
    "安全防护": "机械设备与设施",
    "危险化学品与危险物质": "危化品与燃气",
    "燃气安全": "危化品与燃气",
    "气瓶安全": "危化品与燃气",
    "粉尘防爆": "粉尘防爆",
    "涂装安全": "作业安全",
    "有限空间作业": "作业安全",
    "作业安全与个体防护": "作业安全",
    "职业卫生": "职业卫生",
    "危险废物与环境安全": "危险废物与环境",
    "应急与事故管理": "应急与事故管理",
    "安全管理": "安全管理与培训",
    "安全教育培训": "安全管理与培训",
    "综合安全": "安全管理与培训",
    "现场安全管理": "安全管理与培训",
    "重大事故隐患判定": "安全管理与培训",
    "总图与建筑": "场所与标志",
    "安全标志": "场所与标志",
    "通风与检测报警": "场所与标志",
}

# 仅用于公开前台的稳定编号展示投影。原始 ``category`` 字段、标题、场所、
# 条件、法规依据及关联关系均保持不变；未列入此表的编号不得因标题相似而
# 自动扩展覆盖范围。
STABLE_ID_CATEGORY_OVERRIDES = {
    "H_06280C62983C4FB2837C0CF2BC": "机械与设备安全",
    "H_612249886BDA48F69E025B509C": "机械与设备安全",
    "H_92653C5782964483B3D154937D": "机械与设备安全",
    "H_F8BD176AF46643EA9E3CC56A6F": "机械与设备安全",
    "H_GBT47236_4_2_2_6": "机械与设备安全",
    "H_07F925FDEFE56C60596FE131": "特种设备",
    "H_5D5ACB4A6D45FD9CEFC4654D": "特种设备",
    "H_5F45555A73771FE1F12AB88F": "特种设备",
    "H_D498594F88F040A2A583731E6F": "特种设备",
    "H_E37EF6102AE03060EDCB51D7": "特种设备",
    "H_F7BCC89D53AC460CB928258D91": "特种设备",
    "H_SZLD_148_3": "特种设备",
    "H_902B8261A176496C9DCA662834": "特种设备",
    "H_135CEF1FEDFF160F80424A5DCB_1": "消防安全",
    "H_32B64EF4F22A7AAC5B023DFCB5_1": "消防安全",
    "H_3BD1ECF362913A2E15E2314DED_1": "消防安全",
    "H_421CE6E205C8069977EB63572A_1": "消防安全",
    "H_68B4D4FA3376550BFD0C19FAC7_1": "消防安全",
    "H_99C14C8150B1AF834ADC8E5121_1": "消防安全",
    "H_99C14C8150B1AF834ADC8E5121_4": "消防安全",
    "H_9BCA80F06AB60F6A4FBF137A87_2": "消防安全",
    "H_B1F6637B204CE085C41B429B3D_1": "消防安全",
    "H_B883CCBBDC5DAECE911760C23D_3": "消防安全",
    "H_3B20B1FE3A9647A9A1AE26FC87": "危险废物与环境安全",
    "H_72C3801D44894633B32B67FD4E": "危险废物与环境安全",
    "H_9284B9BA196043B59022AF0FB7": "危险废物与环境安全",
    "H_D3EB901F4EC14131AEB880C102": "危险废物与环境安全",
    "H_F53C97BEFD7761225C2B413A": "危险废物与环境安全",
    "H_YJF_6_6_1": "危险废物与环境安全",
    "H_YJF_6_9_1": "危险废物与环境安全",
    "H_539E0915B38B64780FF185BE28_3": "职业卫生",
    "H_A915F52BFFC99371A8A67FC150_3": "职业卫生",
    "H_ZJWS_12_1": "职业卫生",
    "H_93650E0ABBD6D466BCB86E8073_2": "职业卫生",
    "H_GBZ188_16_7": "职业卫生",
    "H_462D38828DEBA46C8E23C177D2_3": "应急与事故管理",
    "H_86641EBB2649A7349D99D07AD9_3": "应急与事故管理",
    "H_D105E5E2683449C027B23E4B28_2": "应急与事故管理",
    "H_D105E5E2683449C027B23E4B28_3": "应急与事故管理",
    "H_YJYA_27_1": "应急与事故管理",
    "H078": "安全教育培训",
    "H_F022B667E1108FB90D68C36D19_1": "安全教育培训",
    "H_3227246FFEDB65997424055F": "安全教育培训",
    "H_9F790C9B0EA34E59207BCCC1AD_2": "安全教育培训",
    "H_9F790C9B0EA34E59207BCCC1AD_3": "安全教育培训",
    "H_AQPX_9_1": "安全教育培训",
    "H_D7F4B2B8F70D67B625BE3E5E95_2": "安全教育培训",
    "H_JS140_十七_1": "安全教育培训",
    "H_133DEA3AE07CE30E3CA5CBF4FF_1": "安全管理",
    "H_38586C4D52EB7979AC2D73A14A_1": "安全管理",
    "H_4306C3DA6C19836BDC0CC5A9E7_1": "安全管理",
    "H_5CD35729CF4B26FFA9F9489176_1": "安全管理",
    "H_71323E2862E5D3955E3DE6DE76_1": "安全管理",
    "H_71323E2862E5D3955E3DE6DE76_2": "安全管理",
    "H_96049FDA8623F7EF0CDA4B1F73_1": "安全管理",
    "H_97123DF324DB6A7FB1B4DAB9F1_2": "安全管理",
    "H_B1BBC7FA21B8DE36E1AB2CD21F_1": "安全管理",
    "H_D9B99E085E45534257B178AC2D_2": "安全管理",
    "H_JS140_七_1": "安全管理",
    "H_JS140_十二_2": "安全管理",
    "H_FCB_7_2": "粉尘防爆",
    "H_CF_MAJOR_06": "燃气安全",
    "H_GBT47236_4_2_11_1_1": "燃气安全",
    "H_GBT47236_4_2_5_2_1": "电气安全",
    "H_GBT47236_6_3_3_1": "安全标志",
}

# 来源：2026-10-09 全量审查逐条复核后的分类纠正，仅用于展示层。
REVIEWED_CATEGORY_CORRECTIONS = {
    # 消防安全
    "H_004D8F2994DD43D1A2F418386F": "消防安全",
    "H_16A5C551A3BE44329C7B5101CB": "消防安全",
    "H_2689A44E234A4483B9121C694B": "消防安全",
    "H_3642D1A7D0A7422A83E1B0E8BA": "消防安全",
    "H_365F2FD05EA345A8A4E71BC9B9": "消防安全",
    "H_3E11F1C21C7041598F346E7FA0": "消防安全",
    "H_440C480EAADB465AAF15204C4E": "消防安全",
    "H_57E393A1257B42E49FCF076877": "消防安全",
    "H_AA8D8CAF77964A0DBC39CDB146": "消防安全",
    "H_B3F07B77A1834B489F43F05A0D": "消防安全",
    "H_FACE4B6C233D4B508D16876838": "消防安全",
    "H_FB8219F504ED46EBA8CC16F3FC": "消防安全",
    "H_GB50140_5_1_3_1": "消防安全",
    "H_JSXF_45_5": "消防安全",
    # 特种设备
    "H_772BE36081184956B7899AA306": "特种设备",
    "H_A4AB60E806794B28A73C3F3C48": "特种设备",
    "H_CCBA1E83E15A914C14219FE7": "特种设备",
    "H_CDCC41FC5CDA320D4E9EB9CA": "特种设备",
    # 电气安全
    "H_052508D94A934DA88563BD06C0": "电气安全",
    "H_62B9B3FCB70F4FF6A3BE35E1D8": "电气安全",
    "H_7CB6B58D9D894DC1BE39E1E7F2": "电气安全",
    # 机械设备与设施
    "H_1AD2E9632F2C494B9FBA1BFDB1": "机械设备与设施",
    "H_210D2E5340A24AF5B9CAD1553E": "机械设备与设施",
    "H_36D21B104AD34CA990E080307B": "机械设备与设施",
    "H_582DD4272FAF4DCA9B0851E6C5": "机械设备与设施",
    "H_58B8DD3B2F5E42F69265ECA65D": "机械设备与设施",
    "H_5F55461A7E7E4BF5A2943EA3C6": "机械设备与设施",
    "H_63B642CC09404DEBB250A63135": "机械设备与设施",
    "H_6B9EB3C3F3A144E4962ACC3FB9": "机械设备与设施",
    "H_75F15C406F67444BB36409571E": "机械设备与设施",
    "H_B032810073CB4F9D934B250454": "机械设备与设施",
    "H_B6DEAFE79F2E4DEAA973C01A0D": "机械设备与设施",
    "H_BC329D96CDE04044A257580182": "机械设备与设施",
    "H_C067799BCC9B44A398A2595C28": "机械设备与设施",
    "H_C0A67E719B304E40AF25E33F6A": "机械设备与设施",
    "H_DC071E7B998C40CB8E96074401": "机械设备与设施",
    "H_DC8FD0AA53E24CBE9C30552E91": "机械设备与设施",
    # 危化品与燃气
    "H_66B2A0967E8B4E4BAD7749DF_1": "危化品与燃气",
    "H_9C23C18DB9EF40A58B8C98F06C": "危化品与燃气",
    "H_D668088455C640A2A99C7BB35C": "危化品与燃气",
    "H_F2C423D851BA4C8782A4B97FB8": "危化品与燃气",
    # 粉尘防爆
    "H_15577_5_4_1": "粉尘防爆",
    "H_15577_6_2_2_1": "粉尘防爆",
    "H_15577_6_2_3_2": "粉尘防爆",
    "H_15577_6_4_2_1": "粉尘防爆",
    "H_15577_6_5_2_1": "粉尘防爆",
    "H_15577_7_2_1_1": "粉尘防爆",
    "H_15577_7_2_2_1": "粉尘防爆",
    "H_15577_7_2_2_2": "粉尘防爆",
    "H_15577_7_3_3_1": "粉尘防爆",
    "H_6CA20375669E46A596BE3866A2": "粉尘防爆",
    "H_FCB_16_1": "粉尘防爆",
    "H_PDDB_6_1": "粉尘防爆",
    # 作业安全
    "H_12158_8_1_17_1": "作业安全",
    "H_15577_6_2_1_4": "作业安全",
    "H_486B128B96EC48BA82C8C0D9FF": "作业安全",
    "H_B552B08A4FD28A8770CDC2BB": "作业安全",
    "H_BDB99227C14D4C7FBE2C5EED54": "作业安全",
    "H_COM_EDGE_PROTECTION": "作业安全",
    "H_COM_HIGH_FALL_PROTECTION": "作业安全",
    "H_COM_SAFETY_NET_DEFECT": "作业安全",
    "H_COM_SCAFFOLD_LOAD": "作业安全",
    "H_EDE4F3F91EC94F4A8B8970393D": "作业安全",
    "H_FC58C02E253472D0EB5E77E178_1": "作业安全",
    "H_YJF_5_4_1": "作业安全",
    # 职业卫生
    "H_0F065B25BAC84C329610C8FBF8": "职业卫生",
    "H_2C354AC8B335CF52A913D6FF41_1": "职业卫生",
    "H_3098720A99F0C4969CF36FD6EC_1": "职业卫生",
    "H_528C6C8455A14D97ADEF524650": "职业卫生",
    "H_5A34A5738C8BAE911FA997CF74_1": "职业卫生",
    "H_62CC3ADCD67E185884603108C7_1": "职业卫生",
    "H_62CC3ADCD67E185884603108C7_2": "职业卫生",
    "H_62CC3ADCD67E185884603108C7_3": "职业卫生",
    "H_7D85AC280234FC8A78C5E07364_4": "职业卫生",
    "H_A1A5AA5EE13A3444450315AB": "职业卫生",
    "H_D0AD6FE92A48431894E9756C00": "职业卫生",
    "H_D2867A52B35286A09860A2A855_1": "职业卫生",
    "H_EF25059676A7C9F3BA7AC2C1E5_1": "职业卫生",
    "H_FC756EA86AAF4A94BA7207A5B5": "职业卫生",
    "H_GBZ188_16_55": "职业卫生",
    "H_ZJWS_17_2": "职业卫生",
    "H_ZJWS_17_5": "职业卫生",
    # 危险废物与环境
    "H_0A9DDC2534BC46FDA9AEE80A89": "危险废物与环境",
    "H_14E04FE43D8A43DC90F7464F41": "危险废物与环境",
    "H_183385CCF77E47A7A4CC4E75D6": "危险废物与环境",
    "H_548F812A3B914C9EA2A02243E5": "危险废物与环境",
    "H_97AE507CED3143C49C42F6B09F": "危险废物与环境",
    "H_97C1C1E87B844BAD9EB2A3D580": "危险废物与环境",
    "H_A1F170AAD1DC4BB893BD27288F": "危险废物与环境",
    "H_AE64CC10CCCDBB67B2A6452E": "危险废物与环境",
    "H_B4C5ACD924F246BEA2B58F7500": "危险废物与环境",
    "H_C0BCA9C2C90042A58EE2F60575": "危险废物与环境",
    "H_CA06E95820E1B8380E415A5F": "危险废物与环境",
    "H_D71C107D07BDC5D8F3BBA2AD9F_1": "危险废物与环境",
    "H_F56DEB1529ADDB0514D511DA64_1": "危险废物与环境",
    "H_YJF_4_7_1": "危险废物与环境",
    # 应急与事故管理
    "H_552711D344C77E0227C90BB100_1": "应急与事故管理",
    "H_944AAA033232AE3F0499A6FB61_1": "应急与事故管理",
    "H_F0FC0DA78ACB0AA17B674816CA_2": "应急与事故管理",
    "H_SGSG_13_3": "应急与事故管理",
    # 安全管理与培训
    "H_12158_8_8_5_3": "安全管理与培训",
    "H_2AF3A77A27777F7C011FCDFD88_2": "安全管理与培训",
    "H_37630CC404984F6FB271662FC8": "安全管理与培训",
    "H_435BAADD179B1A8C0D0E8B9528_1": "安全管理与培训",
    "H_5CD35729CF4B26FFA9F9489176_4": "安全管理与培训",
    "H_6383FA81F7EA567158E6481526_1": "安全管理与培训",
    "H_6B81819B5BCB43149B0148792F": "安全管理与培训",
    "H_7706D9CBFFB04593A7868FC554": "安全管理与培训",
    "H_7A2AAA3D53D03F168C7ECCBB": "安全管理与培训",
    "H_7B2FE1F2A576228A5743ADBB07_2": "安全管理与培训",
    "H_82FB7AF5E0F521EF8D9489136A_3": "安全管理与培训",
    "H_834D2A6260DC443EA53DF89220": "安全管理与培训",
    "H_86641EBB2649A7349D99D07AD9_1": "安全管理与培训",
    "H_87B2F0BEA865AD12A492FF008D_1": "安全管理与培训",
    "H_87B2F0BEA865AD12A492FF008D_2": "安全管理与培训",
    "H_87B2F0BEA865AD12A492FF008D_3": "安全管理与培训",
    "H_A1DC6EDB10B50EFED2A7109DF1_1": "安全管理与培训",
    "H_APJG_19_2": "安全管理与培训",
    "H_B1BBC7FA21B8DE36E1AB2CD21F_3": "安全管理与培训",
    "H_B7ADCDE1235C44A7563498F276_1": "安全管理与培训",
    "H_D5E67682A83F478C8E9A3EC26A": "安全管理与培训",
    "H_D9B99E085E45534257B178AC2D_1": "安全管理与培训",
    "H_DB7FA5121B72C9FE0A33439033_2": "安全管理与培训",
    "H_DB7FA5121B72C9FE0A33439033_3": "安全管理与培训",
    "H_EC8F2729F72B49F0B049BE541C": "安全管理与培训",
    "H_JS140_十_1": "安全管理与培训",
    "H_JS140_十二_1": "安全管理与培训",
    # 场所与标志
    "H_2303005CE94D49BD88F75C7DC7": "场所与标志",
    "H_70CF6BE6FCDB433192C9456223": "场所与标志",
    "H_CB60731890BF4F388E3225E634": "场所与标志",
    "H_D938BDABA6238F3520F00B78": "场所与标志",
    "H_F0D64F91542E4B0399D83D670D": "场所与标志",
    "H_ZDY_18_1": "场所与标志",
}


DISPLAY_LEVEL_MAP = {
    "法律": "法律",
    "行政法规": "行政法规",
    "地方法规": "地方性法规",
    "部门规章": "部门规章",
    "部门规章（部令）": "部门规章",
    "地方政府规章": "地方政府规章",
    "国家标准": "国家标准",
    "强制性国家标准": "国家标准",
    "强制性国家职业卫生标准": "国家标准",
    "工程建设国家标准": "国家标准",
    "推荐性国家标准": "国家标准",
    "行业标准": "行业标准",
    "环境保护行业标准": "行业标准",
    "地方标准": "地方标准",
    "特种设备安全技术规范": "安全技术规范",
}

ENVIRONMENT_LEVEL_OVERRIDES = {
    "LV_YJFGZ": "行业标准",
}

# UI navigation clues, not legal applicability or a second professional category.
# Only explicit source ``places`` phrases may produce these tags. Never inspect
# titles, keywords, descriptions or conditions; generic professional obligations
# (消防责任、培训、职业卫生等) intentionally remain untagged.
SCENE_RULES = (
    ("通道与出口", ("疏散通道", "疏散走道", "安全出口", "消防车道", "地面通道")),
    ("配电室与配电装置", ("配电室", "配电房", "配电间", "配电箱", "配电柜", "配电屏", "电气控制柜", "照明控制柜")),
    ("电梯", ("电梯",)),
    ("锅炉", ("锅炉",)),
    ("压力容器与储气罐", ("压力容器", "储气罐")),
    ("气瓶", ("气瓶",)),
    ("叉车与场车", ("叉车", "场车")),
    ("起重设备", ("起重", "行车作业", "行车操作", "各类型行车", "吊车", "电动葫芦")),
    ("索道与游乐设施", ("索道", "游乐设施")),
    ("机械加工", ("机械加工", "机加工", "冲压", "剪切机床", "砂轮机", "五金打磨", "机加清洗")),
    ("粉尘与除尘", ("粉尘", "除尘")),
    ("危化品储存场所", ("危化品库房", "危化品储存", "危险化学品仓库", "危险化学品储存")),
    ("危废贮存场所", ("危险废物贮存场所", "危险废物收集、暂存或贮存场所")),
    ("废气与污水处理设施", ("废气治理设施", "污水处理")),
    ("燃气使用", ("燃气使用", "可燃气体燃烧装置")),
    ("有限空间", ("有限空间",)),
    ("动火与焊割", ("动火", "焊接", "气焊", "焊割", "热切割")),
    ("高处作业", ("高处作业", "高处施工", "脚手架")),
    ("涂装作业", ("涂装", "喷漆", "喷粉", "调漆", "喷涂")),
    ("仓储与物流", ("仓储", "仓库", "库房", "库区", "原料库", "成品库", "物料仓", "物流", "装卸", "货台", "冷库")),
    ("生产现场", ("车间", "工位", "流水线", "台位", "操作区域")),
    ("实验与化验", ("实验室", "化验室")),
    ("消防控制与泵房", ("消防控制室", "消防水泵房", "消防水泵控制室")),
    ("电动自行车充电", ("电动自行车停放充电", "电动自行车充电")),
    ("施工现场", ("施工现场", "施工作业面")),
    ("宿舍", ("宿舍",)),
    ("餐饮与厨房", ("餐饮", "厨房")),
)
SCENE_TAGS = tuple(tag for tag, _fragments in SCENE_RULES)
# Keep the existing serialized sentinel for shared routes and older callers.
SCENE_TAG_OPTIONS = SCENE_TAGS + ("未细分场景",)

DISPLAY_MODE_MAP = {
    "direct": "直接适用",
    "conditional": "有条件适用",
}

DISPLAY_ROLE_MAP = {
    "direct": "直接依据",
    "supporting": "辅助依据",
}

NOTE_DATE_PREFIX = "2026-09-11 "
APPROVED_MAINTENANCE_SENTENCES = (
    "修订：原 description 与 title 完全相同，已补写为含情境的完整描述。",
    "修订：原 description 与 title 完全相同，已补写为完整描述。",
    "修订：原整改措施为现状描述或空话，已改写为可执行的整改动作。",
    "修订：原整改措施为现状描述或空话（“已设置…”“符合要求”等），已改写为可执行的整改动作。",
    "修订：原整改措施为空话或模板（“符合规定”“针对上述隐患制定整改措施并落实”等），已改写为针对本隐患的可执行措施。",
    "修订：原 measures 字段直接照抄隐患描述（V3 迁移遗留），已改写为针对该隐患的可执行整改措施；标题、描述与法律依据未改动。",
    "精简：原标题为法条式长句，已压缩为一句缺陷表述；法律依据与整改措施未改动。",
    "精简：原标题为法条式长句（含条款列举），已压缩为一句缺陷表述；法律依据与整改措施未改动。",
    "通用化：原表述含企业现场细节（具体编号/楼层/方位/数量词），已抽象为通用隐患表述，法律依据与整改措施未改动。",
    "修订：原标题为条款原文片段或存在文字损坏，语义不通且无法作为现场隐患表述；此处依其原描述与现有依据改写为可判定的现场事实，未改变依据本身。",
    "修订：原整改措施已改写为可执行动作。",
)
APPROVED_MAINTENANCE_TEXTS = tuple(
    sorted((NOTE_DATE_PREFIX + sentence for sentence in APPROVED_MAINTENANCE_SENTENCES),
           key=len, reverse=True)
)
_MAINTENANCE_RE = re.compile("|".join(re.escape(text) for text in APPROVED_MAINTENANCE_TEXTS))
_PUNCT = re.compile(r"[，。；：、（）()【】\[\]《》“”‘’'\"·•…—–_-]+")


def display_category(value, hazard_id=""):
    """Return a controlled UI alias while preserving unknown source values."""
    if hazard_id in STABLE_ID_CATEGORY_OVERRIDES:
        category = STABLE_ID_CATEGORY_OVERRIDES[hazard_id]
    elif hazard_id in REVIEWED_CATEGORY_CORRECTIONS:
        return REVIEWED_CATEGORY_CORRECTIONS[hazard_id]
    else:
        category = CATEGORY_ALIASES.get(value or "", value or "")
    return CATEGORY_GROUPS.get(category, category)


def display_level(raw_level, version_id=""):
    """Map only the approved level dictionary and the approved stable-ID exception."""
    if version_id in ENVIRONMENT_LEVEL_OVERRIDES:
        return ENVIRONMENT_LEVEL_OVERRIDES[version_id]
    return DISPLAY_LEVEL_MAP.get(raw_level or "", raw_level or "")


def searchable(parts):
    """Return the deterministic normalized search text shared by build and verify."""
    value = " ".join(str(part) for part in parts if part)
    value = unicodedata.normalize("NFKC", value).lower()
    value = _PUNCT.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()


def project_note(note):
    """Split only the approved complete maintenance sentences, losslessly.

    The source note is never rewritten.  Offsets use Python string positions so
    every segment can be checked against the exact original text.
    """
    if note is None:
        return {"noteSegments": [], "businessNote": "", "maintenanceNote": ""}
    if not isinstance(note, str):
        raise TypeError("note 必须是字符串、null 或缺失")

    segments = []
    maintenance = []
    cursor = 0
    for match in _MAINTENANCE_RE.finditer(note):
        if match.start() > cursor:
            segments.append({"kind": "business", "text": note[cursor:match.start()],
                             "start": cursor, "end": match.start()})
        text = match.group(0)
        segments.append({"kind": "maintenance", "text": text,
                         "start": match.start(), "end": match.end()})
        maintenance.append(text)
        cursor = match.end()
    if cursor < len(note):
        segments.append({"kind": "business", "text": note[cursor:],
                         "start": cursor, "end": len(note)})

    return {
        "noteSegments": segments,
        "businessNote": "".join(segment["text"] for segment in segments
                                  if segment["kind"] == "business"),
        "maintenanceNote": "\n".join(maintenance),
    }


def raw_law_level(law, law_version, publication=None):
    """Match the builder's source precedence for the retained raw ``level`` field."""
    publication = publication or {}
    return (law.get("documentKind") or law_version.get("level") or
            publication.get("level", ""))


def scene_tags(places):
    """Project only recorded place/equipment/activity clues, never applicability."""
    texts = [place for place in (places or []) if isinstance(place, str)]
    return [tag for tag, fragments in SCENE_RULES
            if any(fragment in text for text in texts for fragment in fragments)]


def project_hazard(hazard, hazard_id=""):
    return {
        "displayCategory": display_category(hazard.get("category", ""), hazard_id),
        "sceneTags": scene_tags(hazard.get("places") or []),
        **project_note(hazard.get("note")),
    }


def project_law_level(raw_level, version_id=""):
    return {"displayLevel": display_level(raw_level, version_id)}


def presentation_review(hazards, level_records, modes=None, roles=None):
    """Build an external audit directory for the deterministic projection.

    ``level_records`` maps a stable law-version ID to ``(raw_level, display_level)``.
    The report is intentionally external to the public package so it does not become
    an additional runtime data source.
    """
    place_to_tags = {}
    for hazard in hazards.values():
        for place in hazard.get("places") or []:
            if isinstance(place, str):
                place_to_tags[place] = scene_tags([place])

    mapped = {place: tags for place, tags in place_to_tags.items() if tags}
    unmapped = sorted(place for place, tags in place_to_tags.items() if not tags)
    unknown_levels = defaultdict(list)
    for version_id, (raw, shown) in level_records.items():
        if raw not in DISPLAY_LEVEL_MAP and version_id not in ENVIRONMENT_LEVEL_OVERRIDES:
            unknown_levels[raw].append(version_id)

    mode_values = sorted(set(modes or []))
    role_values = sorted(set(roles or []))
    unknown_modes = [value for value in mode_values if value not in DISPLAY_MODE_MAP]
    unknown_roles = [value for value in role_values if value not in DISPLAY_ROLE_MAP]
    review_prompts = []
    if unknown_levels:
        review_prompts.append("以下依据类型未纳入批准映射，已保留原值，请架构师审查：" +
                              "、".join(sorted(unknown_levels)))
    if unknown_modes:
        review_prompts.append("以下适用方式枚举未纳入中文标签映射，已保留原值，请审查：" +
                              "、".join(unknown_modes))
    if unknown_roles:
        review_prompts.append("以下依据角色枚举未纳入中文标签映射，已保留原值，请审查：" +
                              "、".join(unknown_roles))

    return {
        "categoryAliases": dict(CATEGORY_ALIASES),
        "categoryGroups": dict(CATEGORY_GROUPS),
        "stableCategoryOverrides": dict(STABLE_ID_CATEGORY_OVERRIDES),
        "stableCategoryOverrideCount": len(STABLE_ID_CATEGORY_OVERRIDES),
        "reviewedCategoryCorrections": dict(REVIEWED_CATEGORY_CORRECTIONS),
        "reviewedCategoryCorrectionCount": len(REVIEWED_CATEGORY_CORRECTIONS),
        "displayLevelMap": dict(DISPLAY_LEVEL_MAP),
        "stableIdOverrides": dict(ENVIRONMENT_LEVEL_OVERRIDES),
        "sceneRules": [
            {"tag": tag, "contains": list(fragments)}
            for tag, fragments in SCENE_RULES
        ],
        "sceneCoverage": {
            "sourcePlaceValues": len(place_to_tags),
            "mappedPlaceValues": len(mapped),
            "unmappedPlaceValues": len(unmapped),
            "mapped": mapped,
            "unmapped": unmapped,
        },
        "unknownLawLevels": {
            raw: sorted(ids) for raw, ids in sorted(unknown_levels.items())
        },
        "unknownModes": unknown_modes,
        "unknownRoles": unknown_roles,
        "reviewPrompts": review_prompts,
    }
