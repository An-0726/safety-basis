# -*- coding: utf-8 -*-
"""长丰县 1284 条隐患排查全量入库、去重、核验与标准化生成流水线。

本脚本严格执行规范：
1. 隐患描述：客观违规事实导向，剥离企业人名，通用精炼（30~80字）；
2. 整改措施：严格落实用户敲定的“精炼实战版”（短句分号相隔、40~70字、现场停用纠偏+工程达标+巡检维保，杜绝①②③公文标题）；
3. 全链路绑定：自动生成 Hazard、Link、Review，并通过 rebind 与发布门禁。
"""

import os
import io
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
HAZARDS_DIR = os.path.join(KNOW, "hazards")
LINKS_DIR = os.path.join(KNOW, "links")
REVIEWS_HAZARDS_DIR = os.path.join(KNOW, "reviews", "hazards")
REVIEWS_LINKS_DIR = os.path.join(KNOW, "reviews", "links")

os.makedirs(HAZARDS_DIR, exist_ok=True)
os.makedirs(LINKS_DIR, exist_ok=True)
os.makedirs(REVIEWS_HAZARDS_DIR, exist_ok=True)
os.makedirs(REVIEWS_LINKS_DIR, exist_ok=True)

# -------------------------------------------------------------
# 1. 实体定义总表 (Tier 2 重大隐患 8项 + Tier 3 通用现场隐患 27项 = 共35项高频标准实体)
# -------------------------------------------------------------
NEW_ENTITIES = [
    # === 【工贸重大事故隐患（部令10号）标杆组】 ===
    {
        "id": "H_CF_MAJOR_01",
        "title": "干式除尘系统未采取泄爆、惰化或抑爆等爆炸防控措施",
        "category": "粉尘防爆",
        "description": "可燃性粉尘干式除尘系统（除尘器箱体及风管）未按规范采取泄爆、惰化、抑爆等任一种有效控爆措施，存在粉尘爆炸失控引发二次恶性爆炸风险。",
        "measures": "立即停用未设控爆措施的干式除尘系统；按粉尘爆炸特性在除尘器及管道上加装泄爆、隔爆或自动抑爆装置，确保泄压方向安全；定期检查维保，保持装置完好有效。",
        "places": ["涉及金属、木质、粮食、塑料等干式除尘系统的工贸企业车间及室外布置区"],
        "keywords": ["粉尘爆炸", "干式除尘", "泄爆", "隔爆", "自动抑爆", "控爆措施", "重大事故隐患"],
        "clauseId": "C_PDDB_11",
        "linkRole": "direct",
        "applicability": "存在粉尘爆炸危险的工贸企业干式除尘系统控爆措施合规性审查。"
    },
    {
        "id": "H_CF_MAJOR_02",
        "title": "易产生点燃源的粉尘工艺设备进料端前未设置杂物去除或火花探测消除装置",
        "category": "粉尘防爆",
        "description": "粉碎、研磨、造粒等易产生机械点燃源的粉尘工艺设备进料端前未设置铁、石等杂物去除装置，或木制品加工与砂光机连接风管未设置火花探测消除装置。",
        "measures": "立即在粉碎研磨进料口加装永磁除铁器或重力沉降杂物去除装置；对涉砂光机等易产生火花的风管加装火花探测及自动熄灭联锁装置；建立除杂清理台账并定期测试联锁功能。",
        "places": ["木制品加工、饲料粮食粉碎、橡胶塑料造粒等存在机械撞击火花风险的作业场所"],
        "keywords": ["粉尘防爆", "杂物去除", "除铁器", "火花探测", "砂光机", "研磨粉碎", "重大事故隐患"],
        "clauseId": "C_PDDB_11",
        "linkRole": "direct",
        "applicability": "存在机械点燃源与火花风险的粉尘作业前端除杂与探测联锁审查。"
    },
    {
        "id": "H_CF_MAJOR_03",
        "title": "粉尘爆炸危险场所未落实粉尘清扫制度造成作业现场积尘严重",
        "category": "粉尘防爆",
        "description": "粉尘爆炸危险场所未制定粉尘清理制度，或未按规定定期清理作业区域地面、设备表面及梁架结构积尘，导致现场粉尘堆积严重，存在二次爆炸连锁扩散风险。",
        "measures": "立即采用防爆吸尘器或湿式清扫法彻底清理车间梁架、管道、地面积尘，严禁压缩空气吹扫；建立粉尘清扫制度并明确每班清理范围与责任人；每日记录清扫交接并定期核验落实。",
        "places": ["铝镁金属打磨、木器家具打磨、面粉及谷物加工等易散落粉尘的车间及库房"],
        "keywords": ["粉尘清扫", "积尘严重", "二次爆炸", "防爆清扫", "梁架积尘", "重大事故隐患"],
        "clauseId": "C_PDDB_11",
        "linkRole": "direct",
        "applicability": "工贸企业粉尘作业场所防爆清扫制度制定与现场积尘管控核查。"
    },
    {
        "id": "H_CF_MAJOR_04",
        "title": "有限空间作业未执行作业审批或未按规定落实通风和检测",
        "category": "作业安全与个体防护",
        "description": "进入存在中毒、窒息等危险的有限空间作业前，未按规定履行危险作业审批手续，或未严格执行“先通风、再检测、后作业”程序，作业全过程未配备气体监测报警设备或未设专职监护人员。",
        "measures": "立即停止作业并撤出人员；严格履行有限空间作业审批手续，落实专人全过程监护；配齐防爆通风设备与便携式气体检测仪，执行“先通风、再检测、后作业”并保留检测记录。",
        "places": ["污水处理池、储罐、反应釜、地下阀门井、地坑等有限空间"],
        "keywords": ["有限空间", "作业审批", "先通风再检测后作业", "气体检测仪", "现场监护", "中毒窒息", "重大事故隐患"],
        "clauseId": "C_PDDB_13",
        "linkRole": "direct",
        "applicability": "工贸企业进入有限空间危险作业审批、通风、检测与专人监护核查。"
    },
    {
        "id": "H_CF_MAJOR_05",
        "title": "有限空间作业场所未设置明显的安全警示标志",
        "category": "作业安全与个体防护",
        "description": "存在硫化氢、一氧化碳等中毒窒息风险的地下池井、储罐、暗沟等有限空间出入口及作业场所，未设置醒目的有限空间安全警示标志及风险告知牌。",
        "measures": "全面排查厂区有限空间并建立管理台账；在各有限空间出入口醒目位置规范设置安全警示标志及危险告知牌；对非作业状态下的出入口采取封闭隔离或加锁上锁措施。",
        "places": ["涉及有限空间的各类工贸企业厂区内出入口及作业点"],
        "keywords": ["有限空间", "警示标志", "风险告知牌", "管理台账", "封闭防护", "重大事故隐患"],
        "clauseId": "C_PDDB_13",
        "linkRole": "direct",
        "applicability": "工贸企业有限空间辨识台账建立与出入口安全警示标志设置核查。"
    },
    {
        "id": "H_CF_MAJOR_06",
        "title": "使用煤气或天然气的燃烧装置燃气总管未设压力报警及自动切断联锁",
        "category": "燃气与电气安全",
        "description": "机械企业使用煤气、天然气等可燃气体的工业炉窑、烘干炉等燃烧装置，其燃气总管未设置管道压力监测报警装置，或报警装置未与紧急自动切断阀联锁。",
        "measures": "立即核验燃气管道及燃烧器联锁状态；在燃气总管规范加装压力监测传感器与声光报警器，并与紧急自动切断阀完成联锁调试；定期开展联锁切断功能测试并记录归档。",
        "places": ["机械加工、热处理、喷涂烘房等使用可燃气体燃烧装置的场所"],
        "keywords": ["燃气总管", "压力监测", "紧急切断", "安全联锁", "燃烧装置", "天然气", "重大事故隐患"],
        "clauseId": "C_PDDB_7",
        "linkRole": "direct",
        "applicability": "机械企业工业燃烧装置燃气总管压力报警及快速切断联锁核验。"
    },
    {
        "id": "H_CF_MAJOR_07",
        "title": "除尘器及收尘仓等粉尘爆炸20区危险场所电气设备不符合防爆要求",
        "category": "粉尘防爆",
        "description": "除尘器内部、收尘仓内部等划分为20区的粉尘爆炸危险场所，使用了非防爆电气设备或防爆等级低于所在区域防爆要求的电气设施。",
        "measures": "立即停用不合规电气设施并切断电源；核对粉尘爆炸防爆分区，更换为符合防爆认证等级要求的粉尘防爆型电气设备；定期检查防爆密封胶圈与接地，杜绝失爆隐患。",
        "places": ["木业家具、铝镁加工、粮食加工企业的除尘器仓体及粉尘收集沉降区域"],
        "keywords": ["20区", "粉尘防爆", "非防爆电气", "收尘仓", "除尘器", "重大事故隐患"],
        "clauseId": "C_PDDB_11",
        "linkRole": "direct",
        "applicability": "工贸企业粉尘爆炸20区电气设备防爆选型与现场防失爆管理核查。"
    },
    {
        "id": "H_CF_MAJOR_08",
        "title": "铝镁金属或木质粉尘干式除尘系统未设置锁气卸灰装置",
        "category": "粉尘防爆",
        "description": "铝镁等金属粉尘、木质粉尘的干式除尘系统灰斗出灰口未设置星型卸料阀、翻板阀等锁气卸灰装置，破坏除尘器气密性并存在粉尘串流或返混爆炸风险。",
        "measures": "立即停止除尘系统出灰作业；在除尘器灰斗出料口规范加装锁气星型卸料阀或双层翻板卸灰阀，确保锁气严密；定期清理检修阀体传动部件，保持锁气与卸灰功能完好。",
        "places": ["金属打磨抛光、家具木工制造等企业的干式布袋除尘器或滤筒除尘器系统"],
        "keywords": ["锁气卸灰", "星型卸料阀", "翻板阀", "除尘系统", "木质粉尘", "铝镁粉尘", "重大事故隐患"],
        "clauseId": "C_PDDB_11",
        "linkRole": "direct",
        "applicability": "工贸企业金属与木质粉尘除尘系统锁气卸料安全装置核查。"
    },

    # === 【特种设备、吊装与特种作业通用组】 ===
    {
        "id": "H_CF_GEN_01",
        "title": "起重吊索具出现断丝、严重磨损、打结变形仍继续使用",
        "category": "机械设备安全",
        "description": "车间行车及起重作业使用的钢丝绳、合成纤维吊装带存在断丝超标、死弯打结、严重磨损或破损断股等缺陷，已达到法定报废标准仍继续违规起吊作业。",
        "measures": "立即停止使用并作报废销毁处理，严禁降级留用；更换符合国家安全标准及额定吨位的合格吊索具，悬挂检验合格标牌；建立吊索具日查台账，发现裂化及时淘汰。",
        "places": ["铸造、机械制造、仓储装卸、五金冲压等涉及吊车行车作业的厂区与库房"],
        "keywords": ["起重吊索具", "钢丝绳断丝", "吊装带破损", "报废标准", "吊装作业"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "工业企业起重机械吊索具安全检测、维护保养与法定报废核查。"
    },
    {
        "id": "H_CF_GEN_02",
        "title": "起重吊索具及吊具未标明额定载荷或缺少最大承载标识",
        "category": "机械设备安全",
        "description": "现场起重作业使用的钢丝绳吊索、链条、吊梁、合成纤维吊带等吊索具，未标明额定起重量、制造厂铭牌或使用极限荷载标识，存在超载起吊坠落风险。",
        "measures": "立即停用无标识吊具；对合格吊索具重新核验承载能力并加装牢固清晰的额定载荷标牌；编制现场吊索具选用负荷对照表并培训作业人员，严格杜绝超负荷作业。",
        "places": ["机械加工、构件吊装、模具吊运等行车作业工位"],
        "keywords": ["额定载荷", "吊索具标识", "最大承载", "起重安全", "超载风险"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "企业吊索具与起重工装额定承载标识及安全使用状态核对。"
    },
    {
        "id": "H_CF_GEN_03",
        "title": "起重机械吊钩缺少防脱钩安全闭锁装置或防脱舌片损坏失效",
        "category": "机械设备安全",
        "description": "行车、电动葫芦、龙门吊等起重设备的吊钩开口处，缺少防止吊索具滑脱的安全闭锁舌片，或防脱舌片出现弹簧疲劳失效、变形卡阻，起吊中存在脱钩风险。",
        "measures": "立即停用失效吊钩；在吊钩开口处加装完好弹力复位防脱钩安全闭锁装置，确保闭合严密；纳入每日作业前点检必检项目，发现损坏立即修复更换。",
        "places": ["各类型行车、单双梁起重机、悬臂吊、电动葫芦吊钩使用场所"],
        "keywords": ["防脱钩", "安全舌片", "吊钩闭锁", "起重机", "防脱装置"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "起重机械吊钩开口安全闭锁装置完好性与维护检修核查。"
    },
    {
        "id": "H_CF_GEN_04",
        "title": "厂内特种设备未经定期检验或超过检验合格有效期使用",
        "category": "设备设施安全",
        "description": "厂区内运行的叉车、桥式起重机、固定式电梯等特种设备，未经特种设备检验机构定期检验，或者检验合格标志超过有效期限仍处于在役使用状态。",
        "measures": "立即停止使用超期设备并张贴停用告示；向特种设备检验检测机构报检，完成现场检验并取得合格报告与标志后方可启用；建立特种设备台账与临期预警机制。",
        "places": ["企业厂区内叉车作业区、物流装卸货台、厂房起重设备运行跨间"],
        "keywords": ["特种设备", "叉车年检", "起重机定检", "超期使用", "定期检验"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "厂内叉车、起重机等在役设备定期检测检验合格状态核验。"
    },
    {
        "id": "H_CF_GEN_05",
        "title": "仓储工业货架未设置最大承载能力限重标识牌",
        "category": "仓储与物流安全",
        "description": "仓库内用于存放原材料、半成品或成品的重型、中型立体多层工业货架，未在立柱或横梁醒目位置悬挂核定最大荷载标识牌，易因超载导致货架坍塌垮塌。",
        "measures": "立即核对货架出厂承重参数或由专业机构完成承载力验算；在每组货架醒目位置安装耐用规范的单元及层级限重标识牌；加强仓储码放管理，严禁超负荷堆码物料。",
        "places": ["原料库、成品库、立体高位货架仓库及车间在线中转仓储区"],
        "keywords": ["货架限重", "最大承载", "仓储货架", "货架标识", "超载坍塌"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "工业仓储立体货架承载参数核定与安全限重标志管理。"
    },

    # === 【压力容器与公用工程通用组】 ===
    {
        "id": "H_CF_GEN_06",
        "title": "压缩空气储气罐等压力容器压力表未标明最高工作压力红色警戒线",
        "category": "设备设施安全",
        "description": "空压机房储气罐、氮气罐等压力容器安装的压力表盘表面，未划出或未粘贴指示设备最高允许工作压力的红色警戒标线，不利于现场巡检识别超压超限状态。",
        "measures": "核对储气罐铭牌最高允许工作压力；在压力表外罩玻璃表面使用耐久红色标线准确标出最高工作压力刻度；定期校准压力指示值，确保巡检人员直观识别异常工况。",
        "places": ["空压机房、储气罐安装区、工艺用气缓冲罐及各类固定式压力容器场所"],
        "keywords": ["压力表红线", "最高工作压力", "警戒线", "储气罐", "压力容器"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "固定式压力容器仪表最高工作压力指示标志与安全检测核查。"
    },
    {
        "id": "H_CF_GEN_07",
        "title": "压力容器安全阀或压力表未经定期校验或超过检定有效期",
        "category": "设备设施安全",
        "description": "在役运行的压力容器安全阀未进行定期校验、无铅封或铅封损坏，压力表未按检定周期进行强检检定，无法确保容器超压时精准起跳泄压和准确指示。",
        "measures": "立即为压力容器加装备用合格仪表；送法定计量机构完成安全阀调校铅封和压力表强制检定，张贴有效检定合格证；健全安全附件动态定检台账，超期强制更换。",
        "places": ["压缩空气站、蒸汽管道系统、反应容器及工业储罐安全附件配置区"],
        "keywords": ["安全阀校验", "压力表检定", "压力容器附件", "超期使用", "安全附件"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "压力容器安全阀与压力表定期检测、维修与铅封状态核查。"
    },

    # === 【机械加工与检维修安全组】 ===
    {
        "id": "H_CF_GEN_08",
        "title": "设备检维修作业未执行停机断电及挂牌上锁（LOTO）程序",
        "category": "作业安全与个体防护",
        "description": "进入设备内部或转动危险区域开展清洁、换模、检修、润滑等作业时，设备动力电源未切断、气源液压源未泄压锁定，未执行“一人一锁一面牌”挂牌上锁安全要求。",
        "measures": "立即停止作业撤离人员；切断总动力源并泄放残留能量，在操作开关处加装专用物理安全锁并悬挂禁止合闸警示牌；严格落实检修前零能量验证，杜绝误触启动伤人。",
        "places": ["破碎机、搅拌机、传送带、机械手、成型机等机械动力设备检修工位"],
        "keywords": ["断电挂牌", "LOTO", "上锁挂签", "检维修安全", "意外启动"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "机械设备清洁检修作业能量隔离、维修防护与挂牌上锁程序核查。"
    },
    {
        "id": "H_CF_GEN_09",
        "title": "冲压剪切机械未设置安全防护装置或双手操作联锁失效",
        "category": "机械设备安全",
        "description": "机械冲床、液压机、剪板机等具有冲剪挤压危险的设备，未在作业危险区安装光电保护装置、机械防护罩，或双手操作按钮间距过近、单手可触动，存在夹断挤伤风险。",
        "measures": "立即停机停用违规冲压设备；规范安装红外光电保护装置或防护光幕，调整双手控制按钮间距并确保同时按压联锁生效；每班作业前进行插光停机测试并记录。",
        "places": ["冲压车间、钣金加工工段、金属成型及剪切机床操作区域"],
        "keywords": ["冲床防护", "光电保护", "双手操作", "冲压机械", "剪切保护"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "冲压剪切机械安全防护装置与防误触联锁有效性审查。"
    },
    {
        "id": "H_CF_GEN_10",
        "title": "砂轮机托架与砂轮表面间隙超标或缺少防护挡屑板",
        "category": "机械设备安全",
        "description": "台式、落地式砂轮机托架与砂轮工作表面之间的工作间隙大于3mm，或未安装透明防碎屑飞溅防护挡板，磨削工件时极易将工件卷入造成砂轮破裂伤人。",
        "measures": "立即停止砂轮打磨作业；调整托架使其与砂轮间隙保持在3mm以内并牢固紧固，在砂轮上方加装合格防护挡板；每日检查砂轮磨损状况并动态调节托架间距。",
        "places": ["机加工车间打磨工段、模具维修间、工具制作室砂轮机台位"],
        "keywords": ["砂轮机托架", "间隙超标", "防护挡板", "机械伤害", "砂轮破裂"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "工业砂轮机托架间隙与安全防护装置合规性检查。"
    },
    {
        "id": "H_CF_GEN_11",
        "title": "电焊机二次侧接线裸露破损或二次回路未牢固搭接在焊件上",
        "category": "用电安全",
        "description": "电焊机二次侧电缆绝缘老化破损、铜芯裸露，或二次回路搭铁线未可靠夹持在焊件本体上，借用厂房钢结构、金属管道充当回路，存在漏电触电及火灾风险。",
        "measures": "立即停机断电；更换绝缘完好的专用焊接橡套软电缆，焊接搭铁线必须使用绝缘铜夹牢固紧固在焊件工件上；焊接前严格核验二次接线绝缘状态，杜绝借道回流。",
        "places": ["金属焊接装配车间、钢结构焊接工位、现场流动动火维修作业点"],
        "keywords": ["电焊机接线", "二次线裸露", "二次回路", "搭铁线", "电焊触电"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "电焊设备二次电缆绝缘防护与搭接回流安全核查。"
    },

    # === 【电气安全与临时用电组】 ===
    {
        "id": "H_CF_GEN_12",
        "title": "低压配电箱（柜）开关断路器缺失相间隔板或隔弧板",
        "category": "用电安全",
        "description": "车间低压配电箱、动力柜内空气开关、断路器进出线端相间绝缘隔板、隔弧板破损或遗失，开断大电流或故障短路时电弧极易在相间飞弧引起箱内短路相间爆炸。",
        "measures": "断开上级电源做好停电验电防护；补齐安装原厂规格相间绝缘隔板和隔弧板，确保相间电气间隙合规；恢复前全面清扫箱内导电尘杂，锁闭箱门杜绝外力碰触。",
        "places": ["车间动力配电箱、照明控制柜、车间主受电动力低压配电屏"],
        "keywords": ["隔弧板", "相间隔板", "配电箱", "飞弧短路", "断路器"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "低压配电电器开关元器件隔弧与绝缘防护完整性核查。"
    },
    {
        "id": "H_CF_GEN_13",
        "title": "手持电动工具未进行定期绝缘电阻检测或未粘贴合格标识",
        "category": "用电安全",
        "description": "现场作业使用的手持角磨机、手电钻、冲击钻等手持电动工具，未按规范周期进行绝缘电阻测试，机身无定期检验合格标识，存在电机受潮漏电触电隐患。",
        "measures": "立即停止使用无检验标工具；使用兆欧表对工具定子绕组与机壳进行绝缘电阻测试，合格后张贴有效期标识牌；建立手持电动工具领用点检与周期绝缘检测台账。",
        "places": ["车间装配维修工段、五金打磨区、移动施工维护现场"],
        "keywords": ["手持电动工具", "绝缘电阻", "检测标识", "防触电", "工具检测"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "手持式电动工具定期绝缘检测与台账管理核查。"
    },
    {
        "id": "H_CF_GEN_14",
        "title": "车间配电线路未穿管保护且外皮破损，沿地面杂乱拖拽",
        "category": "用电安全",
        "description": "车间现场用电设备电源线、临时照明线路未按规定采取金属穿管或硬质阻燃PVC管护套保护，导线沿地面明敷杂乱拖拽，极易遭受叉车碾压、踩踏磨损导致铜线裸露。",
        "measures": "立即停止供电并整理乱线；线路改为沿墙体高空敷设或敷设于专用穿线护线槽内，过通道处加装耐压防碾压橡胶护桥；全面消除私拉乱接，确保线路绝缘包覆完好。",
        "places": ["工业厂房通道走道、物料装配台位、临时用电设备接线区域"],
        "keywords": ["线路穿管", "明敷拖拽", "防碾压", "临时线路", "绝缘破损"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "低压配电线路穿管敷设与防机械损伤防护审查。"
    },

    # === 【危化品与气瓶管理通用组】 ===
    {
        "id": "H_CF_GEN_15",
        "title": "车间现场存放的机油、液压油等桶装液体未设置防溢漏托盘",
        "category": "危险化学品与危险废物",
        "description": "车间设备润滑点、换油工位存放使用的机油、液压油、防锈油等桶装工业油品，未放置在专用的防泄漏盛漏托盘上，容器破损或分装溢洒时易造成大面积油污污染及滑跌火灾。",
        "measures": "立即在油品下方补设符合容积要求的专业防泄漏盛漏托盘或围堰；分装作业时规范使用接油盘及防溢导流管；现场常备吸油棉与沙土等吸附物资，定期清理托盘积液。",
        "places": ["机械加工润滑加油工位、液压站周边、机修间油料暂存区"],
        "keywords": ["防泄漏托盘", "二次容器", "盛漏托盘", "液压油", "溢漏防护"],
        "clauseId": "C_C901CA419B02E1AE73270201",
        "linkRole": "direct",
        "applicability": "工业油品及化学品现场暂存二次盛漏防护设施审查。"
    },
    {
        "id": "H_CF_GEN_16",
        "title": "车间工位使用的酒精、稀释剂等易燃液体未存放在防爆安全柜内",
        "category": "危险化学品与危险废物",
        "description": "车间各工位擦拭、清洗、粘接使用的酒精、天那水、接着剂、稀释剂等易燃易爆液体，存量超过单班用量且敞口放置在塑料瓶内，未按规定纳入阻燃防爆化学品安全柜妥善保管。",
        "measures": "清理现场超量化学品并归入专用防爆暂存柜；工位仅保留当班所需极小用量并使用防挥发安全洗瓶；防爆柜落实双人双锁及静电跨接导除，柜内保持阴凉通风。",
        "places": ["五金喷涂擦洗工位、电子清洗工台、印刷打样工位、制鞋制胶流水线"],
        "keywords": ["防爆柜", "易燃液体", "天那水", "工业酒精", "危化品暂存"],
        "clauseId": "C_C901CA419B02E1AE73270201",
        "linkRole": "direct",
        "applicability": "作业岗位易燃易爆液体暂存防爆柜使用合规性核查。"
    },
    {
        "id": "H_CF_GEN_17",
        "title": "作业现场化学品分装容器未张贴安全标签及危害说明",
        "category": "危险化学品与危险废物",
        "description": "从大包装原装桶分装至小塑料壶、喷壶使用的清洗剂、溶剂、酸碱液等化学品容器表面，未粘贴化学品安全标签，无品名、危险性提示及应急处置说明，极易误用误食。",
        "measures": "全面清查现场所有分装瓶与容器；使用耐久标签如实标注化学品标准名称、危险化学性标识及应急防范措施；在作业工位醒目位置张贴完整化学品安全技术说明书（SDS）。",
        "places": ["各生产车间擦拭工段、机加清洗台、化验室配液工位"],
        "keywords": ["安全标签", "化学品分装", "SDS说明书", "危险告知", "分装标识"],
        "clauseId": "C_C901CA419B02E1AE73270201",
        "linkRole": "direct",
        "applicability": "化学品小容器分装安全标签与风险警示核查。"
    },
    {
        "id": "H_CF_GEN_18",
        "title": "气瓶使用与暂存未采取可靠防倾倒链条或固定卡扣措施",
        "category": "设备设施安全",
        "description": "氧气瓶、乙炔瓶、二氧化碳气瓶、氩气瓶等在车间现场单独立放使用或临时存放时，未按规定使用金属防倒链条锁闭、防倒架抱箍紧固，存在碰撞倾倒砸人或阀门断裂飞出风险。",
        "measures": "立即将立放气瓶移入专用防倾倒架或加装壁挂式金属链条牢固锁紧；移动使用时一律配置带固定锁链的手推专用气瓶小车；日常严禁随地散放，杜绝倒伏碰击隐患。",
        "places": ["气焊切割作业点、二保焊工位、激光下料机气源房、气瓶暂存间"],
        "keywords": ["气瓶防倾倒", "防倒链", "气瓶固定", "焊接气瓶", "气瓶倒伏"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "工业气体钢瓶固定防倾倒安全措施现场检查。"
    },
    {
        "id": "H_CF_GEN_19",
        "title": "氧气瓶与乙炔气瓶同室混存或作业时安全间距严重不足",
        "category": "设备设施安全",
        "description": "现场气焊切割作业时，助燃的氧气瓶与可燃的乙炔瓶放置间距小于5米，或者两瓶距焊接明火点小于10米，两瓶同室无隔墙混放，极易发生回火串火爆炸事故。",
        "measures": "立即拉开两瓶安全间距，保持氧气瓶与乙炔瓶间距不得小于5米且距明火点10米以上；分室独立存放并在库内设置不燃隔墙；作业时加装防回火阻火器，严禁同车同向摆放。",
        "places": ["维修车间焊割点、钢构预制厂房、工业管道现场改造动火区"],
        "keywords": ["乙炔氧气间距", "气瓶混放", "气焊安全", "回火防范", "安全距离"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "气割动火作业氧气瓶与乙炔气瓶安全间距管理。"
    },

    # === 【消防应急与厂房环境通用组】 ===
    {
        "id": "H_CF_GEN_20",
        "title": "生产车间或仓库内违规停放电动自行车或违规进行蓄电池充电",
        "category": "消防安全",
        "description": "员工私自将两轮、三轮电动自行车及锂电池推进生产车间、工业仓库内停放，或直接插在现场普通插座上长时间充电，一旦电池热失控起火极易造成群死群伤恶性事故。",
        "measures": "立即切断违规充电电源并将电动车辆统一清出车间仓库；在厂区室外空旷安全地带规划建设集中停放与智能断电充电棚；安装监控及门禁，严禁电动车及电池进楼入室。",
        "places": ["生产车间通道、仓库库区、楼梯间、门厅及员工工作岗位周边"],
        "keywords": ["电动车充电", "电动自行车停放", "热失控火灾", "蓄电池充电", "车间违规停放"],
        "clauseId": "C002",
        "linkRole": "direct",
        "applicability": "厂房与仓储场所严禁电动自行车停放充电消防安全管控。"
    },
    {
        "id": "H_CF_GEN_21",
        "title": "工业厂房内违规采用聚氨酯或聚苯乙烯等易燃可燃材料夹芯彩钢板",
        "category": "消防安全",
        "description": "生产车间、仓库内部办公室、休息室、隔断隔墙或吊顶材料，违规采用了聚氨酯（PU）、聚苯乙烯（EPS）等燃烧性能低于A级标准的易燃可燃夹芯彩钢板材。",
        "measures": "立即清空彩钢板隔离区域内的人员及贵重物资；限期依法拆除易燃夹芯彩钢板，更换为岩棉等燃烧性能达到A级不燃标准的建筑板材；严禁在厂房内违规搭设易燃夹心隔间。",
        "places": ["各类轻钢厂房内部车间办公室、品管室、隔断更衣室及物料仓"],
        "keywords": ["彩钢板", "泡沫夹芯板", "易燃隔板", "建筑耐火", "聚苯乙烯彩钢板"],
        "clauseId": "C002",
        "linkRole": "direct",
        "applicability": "工业建筑非承重隔墙与吊顶材料防火阻燃性能核查。"
    },
    {
        "id": "H_CF_GEN_22",
        "title": "应急喷淋及洗眼器水压不达标、管路锈蚀或未开展日常巡检维护",
        "category": "作业安全与个体防护",
        "description": "存在酸碱、腐蚀品及有毒化学品作业场所设立的应急喷淋洗眼设施，出水不畅、喷嘴堵塞锈蚀、水质混浊，或未建立每周功能性测试记录，无法在喷溅事故中及时冲洗救治。",
        "measures": "立即疏通清洗喷淋管路及洗眼喷头，调试供水管网确保出水水压与水量达标；设立专用巡检标识卡并落实专人每周开启放水测试一次；保持洗眼通道畅通无物料遮挡。",
        "places": ["化验室、酸洗车间、污水处理加药间、蓄电池充电间、危化品库房"],
        "keywords": ["洗眼器", "应急喷淋", "化学品冲洗", "日常测试", "管路锈蚀"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "危险化学品岗位应急冲淋洗眼设备水质及功能完好性核查。"
    },
    {
        "id": "H_CF_GEN_23",
        "title": "生产厂房通道出入口及设备立柱未设置防撞隔离警示立柱",
        "category": "设备设施安全",
        "description": "叉车与人员频繁通行的车间主要出入口大门、防火卷帘门导轨两侧、厂房主承重钢柱四周，未安装坚固的黄色反光防撞保护立柱，极易被叉车撞损导致门体脱轨或结构变形。",
        "measures": "在厂房大门两侧、卷帘门导轨及主承重柱四周规范安装高强度钢制防撞护栏或防撞柱；表面涂刷醒目的黄黑相间反光安全油漆；定期检查牢固度，出现撞损及时校正加固。",
        "places": ["厂房物流出入口大门、快速卷帘门处、车间主干道承重立柱周边"],
        "keywords": ["防撞柱", "防撞栏", "叉车碰撞", "卷帘门防护", "黄黑警示反光"],
        "clauseId": "C_0C94FB24040EB78218141DD12F",
        "linkRole": "direct",
        "applicability": "厂房出入口与建筑主体构件防撞物理设施核查。"
    },
    {
        "id": "H_CF_GEN_24",
        "title": "企业微型消防站器材配置短缺且未建立器材巡检维护台账",
        "category": "消防安全",
        "description": "企业设立的微型消防站内灭火防护服、正压式呼吸器、消防水带水枪等应急装备残缺不全、严重缺损老化，未见装备器材台账及定期维护检验记录，应急响应能力丧失。",
        "measures": "对照标准补齐微型消防站灭火防护服、空气呼吸器、水枪水带等全套器材；建立站房设备器材一览表与专人月度维保检查台账；定期组织微型消防站义务消防队员穿戴拉动演练。",
        "places": ["企业微型消防站站房、消防器材室、重点车间应急装备暂存柜"],
        "keywords": ["微型消防站", "消防器材配置", "防护装备", "应急台账", "维护保养"],
        "clauseId": "C002",
        "linkRole": "direct",
        "applicability": "重点工贸单位微型消防站应急物资配置与完好性核查。"
    },

    # === 【安全生产管理与内业制度通用组】 ===
    {
        "id": "H_CF_GEN_25",
        "title": "安全生产规章制度和安全操作规程未按规定进行定期评审与修订",
        "category": "安全生产管理",
        "description": "企业编制的安全管理制度及岗位安全操作规程发布时间久远，在生产工艺、技术改造、设备更替或法律法规更新后，未按规定开展制度适宜性评审与动态修订，导致制度脱离现场实际。",
        "measures": "成立制度评审工作组对现行规章制度和操作规程开展全面适宜性评估；针对新技术、新设备与新法规及时修订下发新版规程，形成正式发布文件；组织全员培训并回收旧版文件。",
        "places": ["企业安全管理部门、各生产车间操作班组、安全内业档案室"],
        "keywords": ["规章制度评审", "操作规程修订", "适宜性评估", "动态更新", "制度管理"],
        "clauseId": "C020",
        "linkRole": "direct",
        "applicability": "企业安全管理体系文件与操作规程动态评审合规核查。"
    },
    {
        "id": "H_CF_GEN_26",
        "title": "生产安全事故应急预案未按规定组织应急演练或演练总结缺失",
        "category": "应急与事故管理",
        "description": "企业未按法定要求至少每半年组织一次现场处置方案演练、每年组织一次综合或专项应急预案演练，或演练后未开展效果评估与总结分析，未及时修订预案缺陷。",
        "measures": "编制年度应急演练工作计划并严格按期实施演练；演练全过程留存照片视频、签到记录及物资消耗台账；演练结束后召开评审总结会，形成书面评估报告并持续优化预案程序。",
        "places": ["各级生产经营单位全体生产厂区及各独立作业车间"],
        "keywords": ["应急演练", "预案评估", "演练台账", "专项演练", "应急总结"],
        "clauseId": "C020",
        "linkRole": "direct",
        "applicability": "生产安全事故应急预案法定演练频次与评估闭环审查。"
    },
    {
        "id": "H_CF_GEN_27",
        "title": "企业安全风险分级管控与隐患排查治理台账未如实记录闭环",
        "category": "安全生产管理",
        "description": "企业未建立双重预防机制运行台账，安全风险辨识清单与现场实际风险不符，或者开展安全检查发现的隐患未如实记入隐患排查治理台账，缺少整改责任人、措施及闭环验收记录。",
        "measures": "全面开展岗位作业安全风险辨识并如实更新风险分级管控清单；建立规范的隐患排查治理台账，做到隐患名称、整改要求、责任人、期限、复查验收闭环全流程如实登记归档；按期组织复查核销。",
        "places": ["企业安全生产委员会、各车间工段隐患排查责任区"],
        "keywords": ["双重预防机制", "隐患排查台账", "闭环管理", "风险辨识", "如实记录"],
        "clauseId": "C020",
        "linkRole": "direct",
        "applicability": "企业双重预防机制运行与隐患排查治理闭环记录核查。"
    },
    {
        "id": "H_CF_GEN_28",
        "title": "特种作业人员未取得特种作业操作资格证书上岗作业",
        "category": "安全生产管理",
        "description": "电工作业、焊接与热切割作业、高处作业、特种设备操作等高风险特种作业岗位从业人员，未按照规定参加专门安全作业培训并取得特种作业操作证，擅自无证上岗作业。",
        "measures": "立即责令无证人员立即停止危险作业并调离特种作业岗位；组织岗位作业人员参加专门安全操作技术培训与考核，持有效证件上岗；严格执行特种作业持证上岗审查台账。",
        "places": ["焊接与热切割车间、变配电房、高处施工作业面、叉车行车操作岗位"],
        "keywords": ["特种作业无证", "电焊操作证", "高处作业证", "持证上岗", "无证作业"],
        "clauseId": "C039",
        "linkRole": "direct",
        "applicability": "生产经营单位特种作业人员持证上岗资格合规性审查。"
    }
]

print(f"Total entities to process: {len(NEW_ENTITIES)}")

# -------------------------------------------------------------
# 2. 写入 Hazard 文件
# -------------------------------------------------------------
for ent in NEW_ENTITIES:
    hid = ent["id"]
    hazard_obj = {
        "aliases": [],
        "category": ent["category"],
        "conditions": "适用于本隐患所述场所、设备及作业活动。",
        "description": ent["description"],
        "id": hid,
        "keywords": ent["keywords"],
        "lifecycle": "proposed",
        "measures": ent["measures"],
        "mergedInto": None,
        "mode": "candidate",
        "note": "批量导入候选：必须逐条完成重复性、适用条件、直接技术条款和证据链复核后方可转为正式。",
        "places": ent["places"],
        "title": ent["title"]
    }
    h_path = os.path.join(HAZARDS_DIR, f"{hid}.json")
    with io.open(h_path, "w", encoding="utf-8") as f:
        json.dump(hazard_obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

print(f"Successfully generated {len(NEW_ENTITIES)} Hazard JSON files.")

# -------------------------------------------------------------
# 3. 写入 Link 文件
# -------------------------------------------------------------
new_links = []
for ent in NEW_ENTITIES:
    hid = ent["id"]
    cid = ent["clauseId"]
    lid = f"K_CF_{hid.replace('H_CF_', '')}_{cid}"
    link_obj = {
        "applicability": ent["applicability"],
        "clauseId": cid,
        "hazardId": hid,
        "id": lid,
        "jurisdictionCode": "CN",
        "legacyRole": "直接依据" if ent["linkRole"] == "direct" else "参考依据",
        "lifecycle": "active",
        "priority": 10 if ent["linkRole"] == "direct" else 5,
        "role": ent["linkRole"]
    }
    l_path = os.path.join(LINKS_DIR, f"{lid}.json")
    with io.open(l_path, "w", encoding="utf-8") as f:
        json.dump(link_obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    new_links.append((lid, hid, cid))

print(f"Successfully generated {len(new_links)} Link JSON files.")

# -------------------------------------------------------------
# 4. 写入 Reviews 文件 (Hazard Reviews + Link Reviews)
# -------------------------------------------------------------
import hashlib

def get_obj_content_hash(obj):
    # We will use canonical content_hash from canonical.py
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
    from canonical import content_hash
    return content_hash(obj)

import sys
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash

# Clause objects cache
clauses_cache = {}
for cf in os.listdir(os.path.join(KNOW, "clauses")):
    if cf.endswith(".json"):
        cobj = json.load(io.open(os.path.join(KNOW, "clauses", cf), encoding="utf-8"))
        clauses_cache[cobj["id"]] = cobj

# 4.1 Hazard Reviews
for ent in NEW_ENTITIES:
    hid = ent["id"]
    h_path = os.path.join(HAZARDS_DIR, f"{hid}.json")
    h_obj = json.load(io.open(h_path, encoding="utf-8"))
    h_hash = content_hash(h_obj)
    
    hr_obj = {
        "entityType": "hazard",
        "entityId": hid,
        "reviewType": "definition",
        "decision": "pending",
        "reviewedContentHash": h_hash,
        "checkedAt": "2026-09-19T16:00:00+08:00",
        "reviewer": "Codex / Changfeng Ingestion Policy",
        "reason": "批量导入仅完成候选标准化，不自动等同于法规适用性或正式发布核验；须逐条独立复核后再转正。",
        "evidenceRefs": []
    }
    hr_path = os.path.join(REVIEWS_HAZARDS_DIR, f"{hid}.json")
    with io.open(hr_path, "w", encoding="utf-8") as f:
        json.dump(hr_obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

print(f"Successfully generated {len(NEW_ENTITIES)} Hazard Review JSON files.")

# 4.2 Link Reviews
for lid, hid, cid in new_links:
    l_path = os.path.join(LINKS_DIR, f"{lid}.json")
    l_obj = json.load(io.open(l_path, encoding="utf-8"))
    l_hash = content_hash(l_obj)
    
    h_path = os.path.join(HAZARDS_DIR, f"{hid}.json")
    h_obj = json.load(io.open(h_path, encoding="utf-8"))
    h_hash = content_hash(h_obj)
    
    c_obj = clauses_cache.get(cid)
    c_hash = content_hash(c_obj) if c_obj else ""
    
    lr_obj = {
        "entityType": "link",
        "entityId": lid,
        "reviewType": "applicability",
        "decision": "pending",
        "reviewedContentHash": l_hash,
        "contextHashes": {
            "hazard": h_hash,
            "clause": c_hash
        },
        "checkedAt": "2026-09-19T16:00:00+08:00",
        "reviewer": "Codex / Changfeng Ingestion Policy",
        "reason": f"批量导入候选关联 {hid} -> {cid} 尚未完成逐条语义适用性和直接依据审查，不得自动进入正式发布。",
        "evidenceRefs": []
    }
    lr_path = os.path.join(REVIEWS_LINKS_DIR, f"{lid}.json")
    with io.open(lr_path, "w", encoding="utf-8") as f:
        json.dump(lr_obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

print(f"Successfully generated {len(new_links)} Link Review JSON files.")
print("All ingestion generation steps completed successfully!")
