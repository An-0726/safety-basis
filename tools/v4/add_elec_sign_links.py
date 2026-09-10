# -*- coding: utf-8 -*-
"""为 电气安全 + 安全标志 两类无 link hazard 建立法规 link + review（复用已有 clause）。

- 仅使用已有 85 个 clause，不新建 clause。
- role: direct / fallback / supporting，严格按规则判定。
- 不更新 manifest.json，不做 git 操作。
"""
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")

CST = timezone(timedelta(hours=8))
CHECKED_AT = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def h22(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:22].upper()


# (hazardId, clauseId, role, applicability, reason, reasonCodes)
LINKS = [
    # ===== 电气安全 =====
    ("H_0AF2C63369124DA5BCDEFBF340", "C_4cc8db7da64889234b1417aa", "direct",
     "低压配电线路的短路保护与过负荷保护配置",
     "Hazard 指配电线路未装设短路保护、过负载（及接地故障）保护；GB 50054-2011《低压配电设计规范》6.1.1 明确要求配电线路应装设短路保护和过负荷保护，"
     "hazard 描述的保护缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_401DBF6BDB854433832D909892", "C005", "fallback",
     "电气设备金属外壳接地保护（电器产品安装使用及线路敷设）",
     "Hazard 指电气设备金属外壳未做良好接地；《消防法》第二十七条第二款要求电器产品的安装、使用及其线路设计、敷设、维护保养、检测必须符合消防技术标准和管理规定，"
     "属上位法兜底依据，直接接地条款需后续补充 GB 50054/GB/T 13869 等专项标准。",
     ["FALLBACK_UPPER_LAW", "DIRECT_CLAUSE_PENDING"]),

    ("H_265A5682E86D43F0B813544099", "C005", "fallback",
     "配电箱（柜）可开启门与金属框架间保护接地跨接",
     "Hazard 指装有电器的可开启门与金属框架接地端子间未用不小于 4mm² 黄绿绝缘铜芯软导线跨接；《消防法》第二十七条第二款对电器产品安装、线路敷设维护提出强制要求，"
     "属上位法兜底，跨接导线截面与连接方式的直接技术条款需后续补充 GB 50303 等专项验收规范。",
     ["FALLBACK_UPPER_LAW", "DIRECT_CLAUSE_PENDING"]),

    ("H_B0A88B69CC0047CE8BF9D87EB6", "C005", "fallback",
     "插头、插座保护接地极单独与保护接地线可靠连接",
     "Hazard 指插座保护接地极未单独与保护接地线可靠连接、不得在插头（座）内与工作中性线相连；《消防法》第二十七条第二款为电器产品安装使用的上位法兜底，"
     "直接接线规则需后续补充 GB/T 13869、GB 50303 等专项标准。",
     ["FALLBACK_UPPER_LAW", "DIRECT_CLAUSE_PENDING"]),

    ("H_6D5EBB4E642F489C9717AED728", "C_229C416CB5F55CB0A4FE6865", "supporting",
     "危险化学品库房防爆电气设施（防爆接线盒）",
     "Hazard 指危险化学品库房使用非防爆接线盒；《危险化学品安全管理条例》第二十条要求生产、储存危化品单位根据危险特性在作业场所设置防爆等安全设施、设备并维护保养，"
     "该条为安全设施配置与维护的原则性依据，具体防爆电气选型（Ex 标志、温度组别）需后续补充 GB 3836 系列标准。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),

    ("H_560D75081D1F4B42BEB642811A", "C_229C416CB5F55CB0A4FE6865", "supporting",
     "危险化学品试剂间电气线路钢管敷设（防爆隔离）",
     "Hazard 指危化品试剂间电气线路未敷设在钢管内；《危险化学品安全管理条例》第二十条要求按危险特性设置防爆、防腐等安全设施并维护，"
     "线路穿管敷设属防爆隔离措施，该条为原则性支撑依据，具体配线方式需后续补充 GB 3836、GB 50058 等专项标准。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),

    ("H_46A4349273C34D2992F88B202F", "C_00EDA4F0099D3AD8ED968F56", "supporting",
     "危险化学品作业场所可燃气体报警装置完好适用",
     "Hazard 指危化品试剂间可燃气体报警器接线处护套线腐蚀脱落、未采用防爆挠性管连接，报警装置失效；《危险化学品安全管理条例》第二十一条要求作业场所设置通信、报警装置并保证处于适用状态，"
     "接线防爆防护的具体要求需后续补充 GB 3836 及报警系统专项标准。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),

    ("H_54D18AD4CE504AD2A8F3967B1F", "C_00EDA4F0099D3AD8ED968F56", "supporting",
     "喷漆房可燃气体报警仪供电线路防爆",
     "Hazard 指喷漆房可燃气体报警仪电源线路不符合防爆规范；《危险化学品安全管理条例》第二十一条要求报警装置处于适用状态，"
     "电源线路防爆配线的具体要求需后续补充 GB 3836、GB 6514 等涂装/防爆专项标准。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),

    ("H_62AD7AADA05F468BAE0F91F5CC", "C005", "fallback",
     "现场电源线路绝缘破损（线路维护保养）",
     "Hazard 指现场部分电源线路绝缘破损；《消防法》第二十七条第二款要求电器产品线路的维护保养、检测必须符合消防技术标准，绝缘破损属线路维护不到位，"
     "属上位法兜底，直接绝缘电阻/更换条款需后续补充 GB/T 13869 等专项标准。",
     ["FALLBACK_UPPER_LAW", "DIRECT_CLAUSE_PENDING"]),

    ("H_8ECAE760F5A5413D8013602429", "C005", "fallback",
     "移动用电产品电源线选型及防机械损伤",
     "Hazard 指移动使用的电子产品未采用完整铜芯橡皮套软电缆/护套软线、移动时未防止电源线拉断损坏；《消防法》第二十七条第二款为电器产品安装使用及线路敷设的上位法兜底，"
     "软电缆选型与防护的直接条款需后续补充 GB/T 13869 等专项标准。",
     ["FALLBACK_UPPER_LAW", "DIRECT_CLAUSE_PENDING"]),

    ("H072", "C039", "direct",
     "电气特种作业人员持证上岗",
     "Hazard 指属于特种作业的电气作业人员未取得相应特种作业操作资格即上岗；《安全生产法》第三十条明确特种作业人员必须经专门安全作业培训、取得相应资格方可上岗，"
     "无证上岗事实与条文直接对应，故 role=direct（个体防护部分另由第四十六条覆盖，本条仅就持证要求建立关联）。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_8525D185BB224B8C84DA85BCE1", "C005", "fallback",
     "粉尘场所配电箱底部封堵（防尘与线路维护）",
     "Hazard 指木工车间配电箱底部未封堵、存在积尘；《消防法》第二十七条第二款要求电器产品及其线路的安装、敷设、维护保养必须符合消防技术标准，"
     "配电箱封堵防尘属安装维护要求，属上位法兜底，防尘等级与封堵做法需后续补充粉尘防爆专项标准。",
     ["FALLBACK_UPPER_LAW", "DIRECT_CLAUSE_PENDING"]),

    # ===== 安全标志 =====
    ("H_2E28B7A14EFE498F905E3B624E", "C030", "direct",
     "易燃易爆危险场所禁止吸烟、禁止明火警示标志",
     "Hazard 指危险场所未张贴严禁吸烟和禁止使用明火等标志；《安全生产法》第三十五条要求在有较大危险因素的生产经营场所和设施设备上设置明显的安全警示标志，"
     "标志缺失事实与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_438F526ECA2148CFA7098ABDCB", "C030", "direct",
     "气瓶临时储存场所安全警示标志",
     "Hazard 指气瓶临时储存场所无安全警示标志；气瓶间存在窒息、燃爆等较大危险因素，《安全生产法》第三十五条要求设置明显安全警示标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_6E52D631F442451F8CAB5B5527", "C030", "direct",
     "气瓶间“禁油脂”“禁止烟火”“当心窒息”警示标志",
     "Hazard 指气瓶间缺少禁油脂、禁止烟火、当心窒息安全警示标志；气瓶间存在较大危险因素，《安全生产法》第三十五条要求设置明显安全警示标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_B4C3B26745D144BD9DCD70E8F3", "C030", "direct",
     "氧气瓶使用场所“严禁油脂”警示标志",
     "Hazard 指氧气瓶使用场所未张贴严禁油脂安全警示标志；氧气接触油脂有燃爆危险，属较大危险因素场所，《安全生产法》第三十五条要求设置明显安全警示标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_67FEC43961B247529D64123BB2", "C030", "direct",
     "货梯等特种设备/危险部位安全警示标志",
     "Hazard 指货梯缺少警示标识；货梯运行存在剪切、坠落等危险因素，《安全生产法》第三十五条要求在有关设施、设备上设置明显安全警示标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_D3152C2FAE274C6A83208875C3", "C030", "direct",
     "受限空间（循环水池）警示标志",
     "Hazard 指循环水池为受限空间、缺少受限空间标识；受限空间存在中毒窒息等较大危险因素，《安全生产法》第三十五条要求在有关场所和设施上设置明显安全警示标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_37C8566545BA444CBD1EB41BCB", "C030", "direct",
     "高温设备/管道防烫伤警示标志",
     "Hazard 指表面温度超过 50°C 的生产设备和管道未设安全警示标志；高温表面存在烫伤危险因素，《安全生产法》第三十五条要求在有关设施设备上设置明显安全警示标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_6706FA04BB344FA59ED6251058", "C_CF69BD977AABD92CE9BBE5", "supporting",
     "生产设备危险部位安全标志的设置与可视性",
     "Hazard 指生产设备易发生危险部位无安全标志，标志图形、符号、文字、颜色须符合 GB 2893、GB 2894 等；GB 2894-2025《安全色和安全标志》7.3 对标志的设置位置、可视性与排列提出规范性要求，"
     "属设置规范支撑依据，标志类型与选用的直接条款待标准全文核验后补充。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),

    ("H_4E1F7C3FFB724997B5C4EC82C9", "C004", "direct",
     "紧急通道和出入口醒目标志",
     "Hazard 指生产场所、作业点的紧急通道和出入口未设置醒目标志；《安全生产法》第四十二条第二款要求生产经营场所出口、疏散通道应标志明显，"
     "紧急通道出入口标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_85C9BDCE54474AEEBD4627119A", "C004", "direct",
     "车间安全疏散出口疏散标识",
     "Hazard 指车间内安全疏散出口缺少疏散标识；《安全生产法》第四十二条第二款要求生产经营场所出口、疏散通道标志明显，"
     "疏散出口标识缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_1764B7439DFE44C1A680A7393E", "C_07FC5D01BC32159FABA700ABBF", "direct",
     "危险废物贮存设施识别标志",
     "Hazard 指危险废物贮存设施未按贮存废物种类和特性按 GB 18597 附录 A 设置标志；L023（危险废物贮存污染控制标准）4.6 明确要求贮存设施、容器和包装物按 HJ 1276 设置危险废物识别标志，"
     "标志缺失与条文直接对应，故 role=direct。",
     ["DIRECT_CLAUSE_MATCH"]),

    ("H_409EF7D84AB8469C91AEC3385C", "C_589E2B3309AADC292AAA4514", "supporting",
     "危险化学品贮存场所明显标志",
     "Hazard 指贮存的化学危险品无明显标志、标志不符合 GB 190 且未按最高等级标志；《危险化学品安全管理条例》第二十六条要求危险化学品专用仓库设置明显的标志，"
     "属标志设置依据，具体危险品标志图形与分级需后续补充 GB 190 等专项标准。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),

    ("H_B62D5B7BB22E4F398116A27DBD", "C001", "supporting",
     "视线障碍处灭火器设置点指示标志",
     "Hazard 指对有视线障碍的灭火器设置点未设置指示其位置的发光标志；《消防法》第十六条第一款第（二）项要求按国家标准配置消防设施器材并设置消防安全标志，"
     "灭火器位置指示标志属消防安全标志范畴，具体发光标志要求需后续补充 GB 50140 专项条文。",
     ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"]),
]

PRIORITY = {"direct": 10, "fallback": 20, "supporting": 30}


def main():
    created_links = []
    skipped_exists = []
    for hid, cid, role, applic, reason, codes in LINKS:
        lid = "K_" + h22(hid + "|" + cid)
        lpath = os.path.join(KNOW, "links", lid + ".json")
        rpath = os.path.join(KNOW, "reviews", "links", lid + ".json")

        # load entities
        hazard = json.load(io.open(os.path.join(KNOW, "hazards", hid + ".json"), encoding="utf-8"))
        clause = json.load(io.open(os.path.join(KNOW, "clauses", cid + ".json"), encoding="utf-8"))

        link = {
            "id": lid,
            "hazardId": hid,
            "clauseId": cid,
            "role": role,
            "legacyRole": "",
            "applicability": applic,
            "jurisdictionCode": "CN",
            "lifecycle": "active",
            "priority": PRIORITY[role],
            "requirementId": "",
        }

        if not os.path.exists(lpath):
            with io.open(lpath, "w", encoding="utf-8") as fh:
                json.dump(link, fh, ensure_ascii=False, indent=1)
        else:
            skipped_exists.append(lid)
            # still ensure review exists
        if not os.path.exists(rpath):
            review = {
                "entityType": "link",
                "entityId": lid,
                "reviewType": "applicability",
                "decision": "verified",
                "reviewedContentHash": content_hash(link),
                "contextHashes": {"hazard": content_hash(hazard), "clause": content_hash(clause)},
                "checkedAt": CHECKED_AT,
                "reviewer": "Doubao-Agent",
                "reason": reason,
                "reasonCodes": codes,
                "evidenceRefs": [],
                "migratedFromV3Verification": None,
            }
            with io.open(rpath, "w", encoding="utf-8") as fh:
                json.dump(review, fh, ensure_ascii=False, indent=1)

        created_links.append((lid, hid, hazard.get("title", ""), cid, clause.get("articlePath", ""), role))

    print("checkedAt:", CHECKED_AT)
    print("created/ensured links:", len(created_links))
    if skipped_exists:
        print("already existed (link file):", skipped_exists)
    for lid, hid, ht, cid, ap, role in created_links:
        print("%s | %s | %s | %s | %s | %s" % (lid, hid, cid, ap, role, ht[:40]))


if __name__ == "__main__":
    main()
