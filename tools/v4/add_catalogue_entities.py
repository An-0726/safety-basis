# -*- coding: utf-8 -*-
"""
Phase 10: 补齐 catalogue law / lawVersion / clause / succession。

本轮核验依据（官方来源）：
- 《危险化学品安全法》：2025-12-27 十四届全国人大常委会第十九次会议通过，
  2026-05-01 施行，10 章 127 条，主席令第六十四号。
  http://www.npc.gov.cn/npc/c2/c30834/202512/t20251227_450708.html
- 《危险化学品安全管理条例》：国务院令第591号公布（2011-12-01 施行），
  国务院令第645号修订（2013-12-07）；截至 2026 年仍现行（2026 年第 3 号公告仍引用）。
  https://www.gov.cn/flfg/2011-03/11/content_1822902.htm
- TSG 08-2026：2026 年第 6 号公告，2026-05-01 施行，TSG 08-2017 同步废止。
  https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/tzsbs/art/2026/art_ccfd987974c9490ab5d8c0792593f1d3.html
- TSG 92-2026：2026 年第 9 号公告，2026-07-01 实施，整合 TSG ZF001-2006 / TSG ZF003-2011。
  https://www.samr.gov.cn/tzsbj/zcfg/aqjsgf/aqjsgf/art/2026/art_24e7ccdf5d4d4176bc2a65ab34ec2842.html
- GB 2894-2025：2025-05-30 发布，2026-03-01 实施，整合替代 GB 2893-2008 / GB 2894-2008 / GB 7231-2003。
  https://www.chinasafety.net.cn/main/aqscwyhmsc/gzdt/2026-07-06/20198.html
- GB 9448-2025：2025 年发布，2026-08-01 实施（代替 GB 9448-1999）。
  https://www.runan.gov.cn/zwgk/zdly/ggjg/ybjg/aqsczc/202608/t20260804_717721.html
- GB 17120-2025：2026-05-01 实施；GB 15760-2025：2026-08-01 实施。
- GBZ 188-2025：国卫通〔2025〕10号，2025-08-20 发布，2026-08-01 实施，代替 GBZ 188-2014。
  https://www.gov.cn/zhengce/zhengceku/202509/content_7039410.htm
- GB 12158-2024：2026-01-01 实施（代替 GB 12158-2006）。
  https://m.thepaper.cn/newsDetail_forward_32799040
- GB 5083-2023：2023-12-28 发布，2025-01-01 实施，现行。
  https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=EF8DFA874E9A4FB6DD9966E1DABECF3C
- GB 19517-2023：2023-05-23 发布，2024-06-01 实施，全部代替 GB 19517-2009。
  https://std.samr.gov.cn/gb/search/gbDetailed?id=FC83293D549CB452E05397BE0A0A9309
- GB 14444-2025：2025-10-31 发布，2026-08-01 实施，代替 GB 14444-2006。
  https://www.runan.gov.cn/zwgk/zdly/ggjg/ybjg/aqsczc/202608/t20260804_717721.html
- GB 46768-2025：2025-10-31 发布，2026-05-01 实施（有限空间，填补空白）。
  https://www.gov.cn/zhengce/zhengceku/202509/content_7039410.htm (附)
- GB 6514-2023 / GB 15607-2023 / GB 12801-2025：身份已确认（河南应急管理厅/湖南标准平台/政府网站），
  实施日期未获官方确认 -> effectiveDate 留空，标记 pending（不建 succession）。

仅新增实体，不修改既有实体；不触碰 V3 SQLite；不切换 production。
"""
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAWS_DIR = os.path.join(ROOT, "knowledge", "laws")
LVS_DIR = os.path.join(ROOT, "knowledge", "law-versions")
CLAUSES_DIR = os.path.join(ROOT, "knowledge", "clauses")
SUCC_DIR = os.path.join(ROOT, "knowledge", "successions")
MANIFEST = os.path.join(ROOT, "knowledge", "manifest.json")


def _sha(s, n=22):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n].upper()


# ---------------- laws ----------------
# (id, canonicalName, documentKind, issuer, lifecycle)
LAWS = [
    ("LF_HAZCHEM_LAW", "中华人民共和国危险化学品安全法", "法律", "全国人民代表大会常务委员会", "active"),
    ("LF_HAZCHEM_REG", "危险化学品安全管理条例", "行政法规", "国务院", "active"),
    ("LF_STD_GB6514", "涂装作业安全规程 涂漆工艺安全及其通风净化", "强制性国家标准",
     "国家市场监督管理总局、国家标准化管理委员会", "active"),
    ("LF_STD_GB15607", "涂装作业安全规程 粉末静电喷涂工艺安全", "强制性国家标准",
     "国家市场监督管理总局、国家标准化管理委员会", "active"),
    ("LF_STD_GB14444", "涂装作业安全规程 喷漆室安全技术要求", "强制性国家标准",
     "国家市场监督管理总局、国家标准化管理委员会", "active"),
    ("LF_STD_GB12801", "生产过程安全基本要求", "强制性国家标准",
     "国家市场监督管理总局、国家标准化管理委员会", "active"),
    # superseded legacy
    ("LF_STD_GB9448_1999", "焊接与切割安全", "强制性国家标准", "国家质量技术监督局", "superseded"),
    ("LF_STD_GB2894_2008", "安全标志及其使用导则", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB2893_2008", "安全色", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB7231_2003", "工业管道的基本识别色、识别符号和安全标识", "强制性国家标准",
     "国家质量监督检验检疫总局", "superseded"),
    ("LF_STD_GB5083_1999", "生产设备安全卫生设计总则", "强制性国家标准", "国家质量技术监督局", "superseded"),
    ("LF_STD_GB15603_1995", "常用化学危险品贮存通则", "强制性国家标准", "国家技术监督局", "superseded"),
    ("LF_STD_GB18597_2001", "危险废物贮存污染控制标准", "强制性国家标准",
     "国家环境保护总局、国家质量监督检验检疫总局", "superseded"),
    ("LF_STD_GB6514_2008", "涂装作业安全规程 涂漆工艺安全及其通风净化", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB15607_2008", "涂装作业安全规程 粉末静电喷涂工艺安全", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB14444_2006", "涂装作业安全规程 喷漆室安全技术规定", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB12801_2008", "生产过程安全卫生要求总则", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB17120_1997", "锻压机械 安全技术条件", "强制性国家标准", "国家技术监督局", "superseded"),
    ("LF_STD_GB15760_2004", "金属切削机床 安全防护通用技术条件", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GBZ188_2014", "职业健康监护技术规范", "强制性国家职业卫生标准", "国家卫生和计划生育委员会", "superseded"),
    ("LF_STD_GB12158_2006", "防止静电事故通用要求", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_GB19517_2009", "国家电气设备安全技术规范", "强制性国家标准",
     "国家质量监督检验检疫总局、国家标准化管理委员会", "superseded"),
    ("LF_STD_TSG08_2017", "特种设备使用管理规则", "特种设备安全技术规范", "国家质量监督检验检疫总局", "superseded"),
    ("LF_STD_TSGZF001_2006", "安全阀安全技术监察规程", "特种设备安全技术规范", "国家质量监督检验检疫总局", "superseded"),
    ("LF_STD_TSGZF003_2011", "爆破片装置安全技术监察规程", "特种设备安全技术规范", "国家质量监督检验检疫总局", "superseded"),
]

# ---------------- lawVersions ----------------
# (id, lawId, officialName, documentNumber, effectiveDate, validityStatus, level, sourceUrl, versionKey)
LVS = [
    ("LV_HAZCHEM_LAW", "LF_HAZCHEM_LAW", "中华人民共和国危险化学品安全法",
     "主席令第六十四号", "2026-05-01", "active", "法律",
     "http://www.npc.gov.cn/npc/c2/c30834/202512/t20251227_450708.html", "2026-05-01"),
    ("LV_HAZCHEM_REG", "LF_HAZCHEM_REG", "危险化学品安全管理条例（2013修订）",
     "国务院令第591号公布，国务院令第645号修订", "2013-12-07", "active", "行政法规",
     "https://www.gov.cn/flfg/2011-03/11/content_1822902.htm", "2013-12-07"),
    ("LV_STD_GB6514", "LF_STD_GB6514", "涂装作业安全规程 涂漆工艺安全及其通风净化",
     "GB 6514-2023", "", "active", "强制性国家标准",
     "https://m.yjglt.henan.gov.cn/2025/03-17/3137649.html", "2023"),
    ("LV_STD_GB15607", "LF_STD_GB15607", "涂装作业安全规程 粉末静电喷涂工艺安全",
     "GB 15607-2023", "", "active", "强制性国家标准",
     "https://www.hnbzw.com/Standard/StdDetail.aspx?ekdHR4nH7qry6rHbsa7bqQ1dDSW9XvXF", "2023"),
    ("LV_STD_GB14444", "LF_STD_GB14444", "涂装作业安全规程 喷漆室安全技术要求",
     "GB 14444-2025", "2026-08-01", "active", "强制性国家标准",
     "https://www.runan.gov.cn/zwgk/zdly/ggjg/ybjg/aqsczc/202608/t20260804_717721.html", "2025"),
    ("LV_STD_GB12801", "LF_STD_GB12801", "生产过程安全基本要求",
     "GB 12801-2025", "", "active", "强制性国家标准",
     "https://m.yjglt.henan.gov.cn/2026/01-20/3311450.html", "2025"),
    # superseded legacy
    ("LV_STD_GB9448_1999", "LF_STD_GB9448_1999", "焊接与切割安全", "GB 9448-1999", "", "superseded",
     "强制性国家标准", "", "1999"),
    ("LV_STD_GB2894_2008", "LF_STD_GB2894_2008", "安全标志及其使用导则", "GB 2894-2008", "", "superseded",
     "强制性国家标准", "", "2008"),
    ("LV_STD_GB2893_2008", "LF_STD_GB2893_2008", "安全色", "GB 2893-2008", "", "superseded",
     "强制性国家标准", "", "2008"),
    ("LV_STD_GB7231_2003", "LF_STD_GB7231_2003", "工业管道的基本识别色、识别符号和安全标识",
     "GB 7231-2003", "", "superseded", "强制性国家标准", "", "2003"),
    ("LV_STD_GB5083_1999", "LF_STD_GB5083_1999", "生产设备安全卫生设计总则", "GB 5083-1999", "", "superseded",
     "强制性国家标准", "", "1999"),
    ("LV_STD_GB15603_1995", "LF_STD_GB15603_1995", "常用化学危险品贮存通则", "GB 15603-1995", "", "superseded",
     "强制性国家标准", "", "1995"),
    ("LV_STD_GB18597_2001", "LF_STD_GB18597_2001", "危险废物贮存污染控制标准", "GB 18597-2001", "", "superseded",
     "强制性国家标准", "", "2001"),
    ("LV_STD_GB6514_2008", "LF_STD_GB6514_2008", "涂装作业安全规程 涂漆工艺安全及其通风净化",
     "GB 6514-2008", "", "superseded", "强制性国家标准", "", "2008"),
    ("LV_STD_GB15607_2008", "LF_STD_GB15607_2008", "涂装作业安全规程 粉末静电喷涂工艺安全",
     "GB 15607-2008", "", "superseded", "强制性国家标准", "", "2008"),
    ("LV_STD_GB14444_2006", "LF_STD_GB14444_2006", "涂装作业安全规程 喷漆室安全技术规定",
     "GB 14444-2006", "", "superseded", "强制性国家标准", "", "2006"),
    ("LV_STD_GB12801_2008", "LF_STD_GB12801_2008", "生产过程安全卫生要求总则",
     "GB 12801-2008", "", "superseded", "强制性国家标准", "", "2008"),
    ("LV_STD_GB17120_1997", "LF_STD_GB17120_1997", "锻压机械 安全技术条件", "GB 17120-1997", "", "superseded",
     "强制性国家标准", "", "1997"),
    ("LV_STD_GB15760_2004", "LF_STD_GB15760_2004", "金属切削机床 安全防护通用技术条件",
     "GB 15760-2004", "", "superseded", "强制性国家标准", "", "2004"),
    ("LV_STD_GBZ188_2014", "LF_STD_GBZ188_2014", "职业健康监护技术规范", "GBZ 188-2014", "", "superseded",
     "强制性国家职业卫生标准", "", "2014"),
    ("LV_STD_GB12158_2006", "LF_STD_GB12158_2006", "防止静电事故通用要求", "GB 12158-2006", "", "superseded",
     "强制性国家标准", "", "2006"),
    ("LV_STD_GB19517_2009", "LF_STD_GB19517_2009", "国家电气设备安全技术规范", "GB 19517-2009", "", "superseded",
     "强制性国家标准", "", "2009"),
    ("LV_STD_TSG08_2017", "LF_STD_TSG08_2017", "特种设备使用管理规则", "TSG 08-2017", "", "superseded",
     "特种设备安全技术规范", "", "2017"),
    ("LV_STD_TSGZF001_2006", "LF_STD_TSGZF001_2006", "安全阀安全技术监察规程", "TSG ZF001-2006", "", "superseded",
     "特种设备安全技术规范", "", "2006"),
    ("LV_STD_TSGZF003_2011", "LF_STD_TSGZF003_2011", "爆破片装置安全技术监察规程", "TSG ZF003-2011", "", "superseded",
     "特种设备安全技术规范", "", "2011"),
]

# ---------------- clauses ----------------
# (lawVersionId, articlePath, quote, sourceUrl)
NPC_URL = "http://www.npc.gov.cn/npc/c2/c30834/202512/t20251227_450708.html"
GOV_URL = "https://www.gov.cn/flfg/2011-03/11/content_1822902.htm"
CLAUSES = [
    # 危险化学品安全法（2026-05-01 施行）
    ("LV_HAZCHEM_LAW", "第五条", "危险化学品单位应当实行全员安全生产责任制，构建安全风险分级管控和隐患排查治理双重预防机制；应当具备法律、行政法规规定和国家标准、行业标准要求的安全条件，建立健全安全管理规章制度和岗位安全责任制度，对从业人员进行安全生产教育和培训，为从业人员提供符合国家标准或者行业标准的劳动防护用品。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第十三条", "生产、储存、使用、经营危险化学品的单位应当按照国家有关规定对危险化学品重大危险源登记建档，进行定期检测、评估、监控，制定应急预案，建立重大危险源安全责任制，并将有关安全措施、应急措施报所在地县级人民政府应急管理部门、消防救援机构和有关部门备案。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第二十八条", "生产、储存危险化学品的单位在公共区域埋地、地面和架空的危险化学品输送管道及其附属设施的安全管理，应当符合法律、行政法规的规定和国家标准、行业标准的要求；应当对其敷设的危险化学品管道设置明显标志，并对危险化学品管道定期检查、检测、巡护。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第三十四条", "生产、储存危险化学品的企业应当建立安全风险分级管控制度，开展安全风险辨识评估，按照安全风险分级采取相应的管控措施；不得使用国家明令淘汰或者禁止使用的危及生产安全的工艺、技术、设施、设备。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第三十六条", "生产、储存危险化学品的企业应当按照国家标准或者行业标准装备自动控制系统和安全仪表系统，建立安全风险监测预警系统，并与政府有关部门实现互联互通。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第三十七条", "生产、储存危险化学品的单位，应当根据其生产、储存的危险化学品的种类和危险特性，在作业场所设置相应的监测、监控、通风、防晒、调温、防火、灭火、防爆、泄压、防毒、中和、防潮、防雷、防静电、防腐、防泄漏以及防护围堤或者隔离操作等安全设施、设备，并按照国家标准、行业标准或者国家有关规定对安全设施、设备进行经常性维护、保养，保证安全设施、设备的正常使用。生产、储存危险化学品的单位，应当在其作业场所和安全设施、设备上设置明显的安全警示标志。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第三十八条", "生产、储存危险化学品的单位，应当在其作业场所设置通信、报警装置，并保证处于适用状态。生产、储存危险化学品的单位，不得关闭、破坏直接关系生产安全的监控、报警、防护、救生设施、设备，或者以其他任何方式影响其正常使用，不得篡改、隐瞒、销毁其相关数据、信息。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第三十九条", "生产、储存危险化学品的企业，应当委托具备国家规定的资质条件的机构，对本企业的安全生产条件每三年进行一次安全评价，提出安全评价报告。安全评价报告的内容应当包括对安全生产条件存在的问题进行整改的方案和整改完成后的结论性意见。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第四十一条", "危险化学品应当储存在专用仓库、专用场地或者专用储存室、储存专柜（以下统称专用储存场所）内，并由专人负责管理；剧毒化学品以及储存数量构成重大危险源的其他危险化学品，应当在专用储存场所内单独存放，实行双人收发、双人保管制度，收发记录的保存期限不得少于三年。危险化学品的储存方式、方法以及储存数量应当符合国家标准或者国家有关规定。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第四十二条", "储存危险化学品的单位应当建立危险化学品出入库核查、登记制度。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第四十三条", "危险化学品专用储存场所应当符合国家标准、行业标准的要求，并设置明显的标志。储存剧毒化学品、易制爆危险化学品的专用储存场所，应当按照国家有关规定设置相应的实体防范、技术防范设施。储存危险化学品的单位应当对其危险化学品专用储存场所的安全设施、设备定期进行检测、检验；检测、检验不合格的，应当停止使用，并按照规定予以维修或者更换。", NPC_URL),
    ("LV_HAZCHEM_LAW", "第五十二条", "本法第三十七条、第三十八条、第四十条第一款、第四十五条关于生产、储存危险化学品的单位的规定，适用于使用危险化学品的单位；第三十四条、第三十五条、第三十六条、第三十九条关于生产、储存危险化学品的企业的规定，适用于使用危险化学品从事生产的企业。", NPC_URL),
    # 危险化学品安全管理条例（2013修订）
    ("LV_HAZCHEM_REG", "第四条", "危险化学品单位应当具备法律、行政法规规定和国家标准、行业标准要求的安全条件，建立、健全安全管理规章制度和岗位安全责任制度，对从业人员进行安全教育、法制教育和岗位技术培训。从业人员应当接受教育和培训，考核合格后上岗作业；对有资格要求的岗位，应当配备依法取得相应资格的人员。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十条", "生产、储存危险化学品的单位，应当根据其生产、储存的危险化学品的种类和危险特性，在作业场所设置相应的监测、监控、通风、防晒、调温、防火、灭火、防爆、泄压、防毒、中和、防潮、防雷、防静电、防腐、防泄漏以及防护围堤或者隔离操作等安全设施、设备，并按照国家标准、行业标准或者国家有关规定对安全设施、设备进行经常性维护、保养，保证安全设施、设备的正常使用。生产、储存危险化学品的单位，应当在其作业场所和安全设施、设备上设置明显的安全警示标志。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十一条", "生产、储存危险化学品的单位，应当在其作业场所设置通信、报警装置，并保证处于适用状态。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十二条", "生产、储存危险化学品的企业，应当委托具备国家规定的资质条件的机构，对本企业的安全生产条件每3年进行一次安全评价，提出安全评价报告。安全评价报告的内容应当包括对安全生产条件存在的问题进行整改的方案。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十四条", "危险化学品应当储存在专用仓库、专用场地或者专用储存室（以下统称专用仓库）内，并由专人负责管理；剧毒化学品以及储存数量构成重大危险源的其他危险化学品，应当在专用仓库内单独存放，并实行双人收发、双人保管制度。危险化学品的储存方式、方法以及储存数量应当符合国家标准或者国家有关规定。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十五条", "储存危险化学品的单位应当建立危险化学品出入库核查、登记制度。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十六条", "危险化学品专用仓库应当符合国家标准、行业标准的要求，并设置明显的标志。储存剧毒化学品、易制爆危险化学品的专用仓库，应当按照国家有关规定设置相应的技术防范设施。储存危险化学品的单位应当对其危险化学品专用仓库的安全设施、设备定期进行检测、检验。", GOV_URL),
    ("LV_HAZCHEM_REG", "第二十八条", "使用危险化学品的单位，其使用条件（包括工艺）应当符合法律、行政法规的规定和国家标准、行业标准的要求，并根据所使用的危险化学品的种类、危险特性以及使用量和使用方式，建立、健全使用危险化学品的安全管理规章制度和安全操作规程，保证危险化学品的安全使用。", GOV_URL),
    ("LV_HAZCHEM_REG", "第三十二条", "本条例第十六条关于生产实施重点环境管理的危险化学品的企业的规定，适用于使用实施重点环境管理的危险化学品从事生产的企业；第二十条、第二十一条、第二十三条第一款、第二十七条关于生产、储存危险化学品的单位的规定，适用于使用危险化学品的单位；第二十二条关于生产、储存危险化学品的企业的规定，适用于使用危险化学品从事生产的企业。", GOV_URL),
]

# ---------------- successions ----------------
# (oldVersionId, newVersionId, relation, legacyRelation, effectiveDate, scope)
SUCC = [
    ("LV_HAZCHEM_REG", "LV_HAZCHEM_LAW", "partially_replaces", "partial_replaced_by", "2026-05-01",
     "《危险化学品安全法》2026-05-01施行后，与法律不一致的条例条款以法律为准；条例未整体废止（2026年应急部等十部门第3号公告仍引用条例规定）。"),
    ("LV_STD_TSG08_2017", "LV_STD_E10C40D4BD9D8DB74D518B2A", "replaces", "replaced_by", "2026-05-01",
     "市场监管总局2026年第6号公告：TSG 08-2026 自2026-05-01施行，TSG 08-2017同步废止。"),
    ("LV_STD_TSGZF001_2006", "LV_STD_AC9450848A37DC769475CCCC", "replaces", "integrated_replaced_by", "2026-07-01",
     "市场监管总局2026年第9号公告：整合修订形成 TSG 92-2026，2026-07-01实施。"),
    ("LV_STD_TSGZF003_2011", "LV_STD_AC9450848A37DC769475CCCC", "replaces", "integrated_replaced_by", "2026-07-01",
     "市场监管总局2026年第9号公告：整合修订形成 TSG 92-2026，2026-07-01实施。"),
    ("LV_STD_GB2893_2008", "LV_STD_25C17FDCEB1B519CAB94DBEA", "replaces", "integrated_replaced_by", "2026-03-01",
     "GB 2894-2025 整合替代 GB 2893-2008 / GB 2894-2008 / GB 7231-2003 三项旧标准（中国安科院宣贯确认）。"),
    ("LV_STD_GB2894_2008", "LV_STD_25C17FDCEB1B519CAB94DBEA", "replaces", "integrated_replaced_by", "2026-03-01",
     "GB 2894-2025 整合替代 GB 2893-2008 / GB 2894-2008 / GB 7231-2003 三项旧标准（中国安科院宣贯确认）。"),
    ("LV_STD_GB7231_2003", "LV_STD_25C17FDCEB1B519CAB94DBEA", "replaces", "integrated_replaced_by", "2026-03-01",
     "GB 2894-2025 整合替代 GB 2893-2008 / GB 2894-2008 / GB 7231-2003 三项旧标准（中国安科院宣贯确认）。"),
    ("LV_STD_GB9448_1999", "LV_STD_872B68E1DA3617B1B2F28BC9", "replaces", "replaced_by", "2026-08-01",
     "GB 9448-2025 于 2026-08-01 实施，代替 GB 9448-1999（应急管理部8月新规清单）。"),
    ("LV_STD_GB17120_1997", "LV_STD_7105B7DEE058E08BA99E40F4", "replaces", "replaced_by", "2026-05-01",
     "GB 17120-2025 于 2026-05-01 实施（5月起新规标准清单）。"),
    ("LV_STD_GB15760_2004", "LV_STD_1EFD5C3AB784E0ECF4C5BF62", "replaces", "replaced_by", "2026-08-01",
     "GB 15760-2025 于 2026-08-01 实施（8月起新规标准清单）。"),
    ("LV_STD_GBZ188_2014", "LV_META_ADA92B569589F2E096A1244F", "replaces", "replaced_by", "2026-08-01",
     "国卫通〔2025〕10号：GBZ 188-2025 自2026-08-01施行，GBZ 188-2014同时废止。"),
    ("LV_STD_GB12158_2006", "LV_STD_A318C93D7F3213B292AD5946", "replaces", "replaced_by", "2026-01-01",
     "GB 12158-2024 于 2026-01-01 实施，代替 GB 12158-2006。"),
    ("LV_STD_GB5083_1999", "LV_STD_2A28FD3FD52E33E6E59E481B", "replaces", "replaced_by", "2025-01-01",
     "GB 5083-2023 于 2025-01-01 实施，代替 GB 5083-1999。"),
    ("LV_STD_GB19517_2009", "LV_STD_9F0C49F748552F616764E7E8", "replaces", "replaced_by", "2024-06-01",
     "GB 19517-2023 于 2024-06-01 实施，全部代替 GB 19517-2009（全国标准信息公共服务平台）。"),
    ("LV_STD_GB18597_2001", "L023", "replaces", "replaced_by", "2023-07-01",
     "GB 18597-2023《危险废物贮存污染控制标准》于 2023-07-01 实施，代替 GB 18597-2001。"),
    ("LV_STD_GB15603_1995", "L012", "replaces", "replaced_by", "2023-07-01",
     "GB 15603-2022《危险化学品仓库储存通则》于 2023-07-01 实施，代替 GB 15603-1995。"),
    ("LV_STD_GB14444_2006", "LV_STD_GB14444", "replaces", "replaced_by", "2026-08-01",
     "GB 14444-2025 于 2026-08-01 实施，代替 GB 14444-2006。"),
]


def main():
    existing_laws = {json.load(io.open(os.path.join(LAWS_DIR, f), encoding="utf-8"))["id"]
                     for f in os.listdir(LAWS_DIR) if f.endswith(".json")}
    existing_lvs = {json.load(io.open(os.path.join(LVS_DIR, f), encoding="utf-8"))["id"]
                    for f in os.listdir(LVS_DIR) if f.endswith(".json")}
    existing_clauses = {json.load(io.open(os.path.join(CLAUSES_DIR, f), encoding="utf-8"))["id"]
                        for f in os.listdir(CLAUSES_DIR) if f.endswith(".json")}
    existing_succ = {json.load(io.open(os.path.join(SUCC_DIR, f), encoding="utf-8"))["id"]
                     for f in os.listdir(SUCC_DIR) if f.endswith(".json")}

    added_laws = added_lvs = added_clauses = added_succ = 0

    for lid, name, kind, issuer, lifecycle in LAWS:
        if lid in existing_laws:
            print("SKIP law (exists):", lid)
            continue
        identity = "{}|{}|cn|{}".format(name, issuer, kind)
        obj = {
            "aliases": [],
            "canonicalName": name,
            "documentKind": kind,
            "id": lid,
            "identityKey": identity,
            "issuer": issuer,
            "jurisdictionCode": "CN",
            "lifecycle": lifecycle,
        }
        with io.open(os.path.join(LAWS_DIR, lid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        added_laws += 1

    for vid, law_id, name, docnum, eff, status, level, url, vk in LVS:
        if vid in existing_lvs:
            print("SKIP lawVersion (exists):", vid)
            continue
        obj = {
            "documentNumber": docnum,
            "effectiveDate": eff,
            "endDate": "",
            "id": vid,
            "lawId": law_id,
            "level": level,
            "officialName": name,
            "scope": "CN",
            "sourceUrl": url,
            "validityStatus": status,
            "versionKey": vk,
        }
        with io.open(os.path.join(LVS_DIR, vid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        added_lvs += 1

    for lv_id, article, quote, url in CLAUSES:
        cid = "C_" + _sha(lv_id + "|" + article, 24)
        if cid in existing_clauses:
            print("SKIP clause (exists):", cid)
            continue
        obj = {
            "articlePath": article,
            "id": cid,
            "lawVersionId": lv_id,
            "lifecycle": "active",
            "quote": quote,
            "sourceUrl": url,
        }
        with io.open(os.path.join(CLAUSES_DIR, cid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        added_clauses += 1

    for old, new, rel, lrel, eff, scope in SUCC:
        sid = "LS_" + _sha(old + "|" + new, 24)
        if sid in existing_succ:
            print("SKIP succession (exists):", sid)
            continue
        obj = {
            "effectiveDate": eff,
            "id": sid,
            "legacyRelation": lrel,
            "newVersionId": new,
            "oldVersionId": old,
            "relation": rel,
            "scope": scope,
        }
        with io.open(os.path.join(SUCC_DIR, sid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        added_succ += 1

    # manifest batch
    if os.path.exists(MANIFEST):
        mf = json.load(io.open(MANIFEST, encoding="utf-8"))
    else:
        mf = {"asOf": "2026-09-10", "batches": []}
    mf["batches"].append({
        "id": "catalogue-v4.1-001",
        "lawsAdded": added_laws,
        "lawVersionsAdded": added_lvs,
        "clausesAdded": added_clauses,
        "successionsAdded": added_succ,
        "selection": ("Phase 10: hazardous-chemical law framework (2026 law + 2013 regulation + key clauses), "
                      "2026 version successions for TSG/GB/GBZ, superseded legacy entities; "
                      "GB 6514-2023/GB 15607-2023/GB 12801-2025 implementation dates pending official confirmation."),
    })
    with io.open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=1)

    print("ADDED laws=%d lawVersions=%d clauses=%d successions=%d" %
          (added_laws, added_lvs, added_clauses, added_succ))


if __name__ == "__main__":
    main()
