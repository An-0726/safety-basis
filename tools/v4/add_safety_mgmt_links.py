# -*- coding: utf-8 -*-
"""安全管理 + 应急与事故管理 + 安全教育 无link hazard 批量建 link+review。

仅复用已有 clause（安全生产法 / 江苏省安全生产条例 / 危险废物贮存污染控制标准）。
- direct：条文直接覆盖 hazard 描述的违法事实
- fallback：上位法兜底，reason 注明 direct 依据需补充的专项标准
不新建 clause / evidence；不更新 manifest；不做 git 操作。
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

# 当前北京时间
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def h22(s):
    return "K_" + hashlib.sha1(s.encode("utf-8")).hexdigest()[:22].upper()


# (hazardId, clauseId, role, priority, applicability, reason, reasonCodes)
PLAN = [
    # ===== 安全管理 =====
    ("H_0E92EFCE7E9E667C7BE84085", "C018", "direct", 10,
     "生产经营单位主要负责人建立健全并落实全员安全生产责任制的情形",
     "hazard 为未建立健全并落实本单位全员安全生产责任制；安全生产法第二十一条第（一）项明确主要负责人应建立健全并落实本单位全员安全生产责任制，违法事实直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_56B7B9F8379B4E6E93F2342596", "C020", "direct", 10,
     "生产经营单位未构建安全风险分级管控和隐患排查治理双重预防机制的情形",
     "hazard 系安全生产法第四条总则性义务（含全员责任制、规章制度、投入、双重预防机制等）；C020（第二十一条第（五）项）对其核心要素——组织建立并落实双重预防工作机制、督促检查安全生产工作——作出直接规定，覆盖该隐患的核心违法事实；其余要素待总则条文补齐。",
     ["DIRECT_CLAUSE_APPLICABLE", "PARTIAL_COVERAGE"]),
    ("H_29E2A1B2BE9B4996ABDFC52C3F", "C015", "direct", 10,
     "生产经营单位安全生产所必需资金投入未予保证的情形",
     "hazard 与安全生产法第二十三条原文高度一致：安全生产条件所必需的资金投入应由决策机构、主要负责人或投资人予以保证并对投入不足后果负责，属直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H015", "C_217217C54423E4EC506728BB7D", "direct", 10,
     "生产经营单位从业人员安全生产教育和培训不到位、未合格即上岗的情形",
     "hazard 为从业人员未按要求接受安全生产教育和培训或未合格即上岗；安全生产法第二十八条要求对从业人员进行安全生产教育和培训、保证其具备必要安全知识并熟悉规章制度操作规程，直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H040", "C039", "direct", 10,
     "法定特种作业范围人员未取得相应资格即上岗作业的情形",
     "hazard 为特种作业人员未按规定持证上岗；安全生产法第三十条明确特种作业人员必须经专门安全作业培训取得相应资格方可上岗，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_9DCBB0D8DB5441A2A3E4811603", "C003", "direct", 10,
     "生产经营单位未建立健全并落实事故隐患排查治理制度、未如实记录并通报的情形",
     "hazard 为未建立健全并落实事故隐患排查治理制度、未通过信息系统如实记录并通报、重大隐患记录保存不足五年；安全生产法第四十一条第二款要求建立健全并落实隐患排查治理制度，直接覆盖制度缺失这一核心违法事实；记录保存期限与信息系统要求同源同条，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_4BCFEF17729F891A6144A8E0", "C003", "direct", 10,
     "隐患排查治理情况未通过信息系统如实记录、未向从业人员通报、重大隐患记录保存不足五年的情形",
     "hazard 聚焦隐患排查治理记录与通报缺陷；安全生产法第四十一条第二款要求建立健全并落实隐患排查治理制度、如实记录并向从业人员通报，直接对应记录缺失与未通报的违法事实。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_BDB99227C14D4C7FBE2C5EED54", "C016", "direct", 10,
     "未按标准为从业人员配备劳动防护用品的情形",
     "hazard 为未按 GB11651 及国家劳动防护用品配备标准配备用品；安全生产法第四十五条要求必须为从业人员提供符合国家标准或行业标准的劳动防护用品，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_EDE4F3F91EC94F4A8B8970393D", "C016", "direct", 10,
     "提供的劳动防护用品不符合国家标准或行业标准、超使用期限的情形",
     "hazard 为劳动防护用品未符合国标/行标、不得超期使用；安全生产法第四十五条要求提供符合国家标准或行业标准的劳动防护用品，直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_6A3ECBD2217B41DCA80350F3F0", "C016", "direct", 10,
     "从业人员未按使用规则正确佩戴、使用劳动防护用品上岗的情形",
     "hazard 为未正确穿戴劳动保护用品上岗；安全生产法第四十五条要求监督、教育从业人员按照使用规则佩戴、使用，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_E8BA94B23294445698371ADAA4", "C016", "fallback", 20,
     "未建立劳动防护用品采购、验收、保管、发放、使用、报废等全过程管理制度的情形",
     "安全生产法第四十五条确立提供合格劳保用品并监督佩戴的上位法义务，构成兜底依据；采购验收发放报废等全过程管理细节的直接依据需后续补充《用人单位劳动防护用品管理规范》（安监总厅安健〔2018〕3号）。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_8DB944621AC043EF8758F7D4C3", "C024", "fallback", 20,
     "未建立安全风险管控清单的情形",
     "安全生产法第四十一条第一款要求建立安全风险分级管控制度并按分级采取管控措施，构成上位法兜底；风险管控清单的编制要素与格式直接依据需后续补充风险分级管控专项标准/指引。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_DC6AE2637C1549ECA1FEB8F087", "C024", "direct", 10,
     "未建立安全风险辨识管控制度的情形",
     "hazard 为未建立安全风险辨识管控制度（对应罚则情形）；安全生产法第四十一条第一款要求建立安全风险分级管控制度，制度缺失直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_00DB7A50FF994B5DB5470A3B03", "C024", "fallback", 20,
     "企业未对较大以上安全风险进行公示的情形",
     "安全生产法第四十一条第一款建立安全风险分级管控制度，构成上位法兜底；较大风险通过公示栏等方式公告的具体要求直接依据需后续补充风险分级管控与隐患排查治理双重预防机制建设相关规定。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H061", "C060", "direct", 10,
     "发包/出租后对承包、承租单位安全生产工作未统一协调管理、未定期检查的情形",
     "hazard 为承包承租单位安全生产统一协调管理或定期检查不到位；安全生产法第四十九条要求生产经营项目场发包出租时对承包承租单位统一协调管理并定期安全检查、发现问题督促整改，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H050", "C049", "direct", 10,
     "江苏省生产经营单位主要负责人未每年向从业人员报告或通报安全生产履职情况的情形",
     "hazard 为江苏省生产经营单位主要负责人未按要求每年向从业人员报告/通报安全生产工作及个人履职情况；江苏省安全生产条例第十五条第（五）项要求每年通过职代会、信息公示栏等向从业人员报告或通报并接受监督，直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_97C1C1E87B844BAD9EB2A3D580", "C_EB1C00891F0F010C3E8DE36882", "direct", 10,
     "危险废物贮存单位未建立贮存台账制度、出入库交接记录不规范的情形",
     "hazard 为危废贮存单位未建立台账制度、出入库交接记录未按标准执行；《危险废物贮存污染控制标准》8.2.4要求贮存设施运行期间按国家有关标准和规定建立危险废物管理台账并保存，直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),

    # ===== 应急与事故管理 =====
    ("H_5B19995BCDF379CBC019C6BE", "C080", "direct", 10,
     "生产经营单位未制定生产安全事故应急救援预案的情形",
     "hazard 为未制定生产安全事故应急救援预案；安全生产法第八十一条要求生产经营单位制定本单位生产安全事故应急救援预案，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_653DF6B73BC04403AD75AE9E27", "C080", "direct", 10,
     "未制定应急救援预案、未与政府预案衔接、未定期组织演练的情形",
     "hazard 与安全生产法第八十一条原文高度一致：制定本单位应急救援预案、与所在地县级以上地方政府预案相衔接并定期组织演练，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H047", "C080", "fallback", 20,
     "江苏省主要负责人未每年至少组织并参与一次应急救援演练的情形",
     "安全生产法第八十一条要求定期组织应急救援演练，构成上位法兜底；主要负责人每年至少组织并参与一次演练的具体频次与责任主体直接依据需后续补充《生产安全事故应急条例》及江苏省安全生产条例。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_1B4FBE6B18404FD795AA211BA6", "C080", "fallback", 20,
     "未制定应急预案演练计划、未按每年/每半年频次组织综合、专项及现场处置方案演练的情形",
     "安全生产法第八十一条要求定期组织应急救援演练，构成上位法兜底；每年至少一次综合/专项演练、每半年至少一次现场处置方案演练的频次直接依据需后续补充《生产安全事故应急条例》（国务院令第708号）。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_02FEFD347E114E1E979C9589AF", "C080", "fallback", 20,
     "应急预案未按综合应急预案、专项应急预案和现场处置方案三层体系构成的情形",
     "安全生产法第八十一条要求制定生产安全事故应急救援预案，构成上位法兜底；应急预案分为综合、专项、现场处置方案三层体系的直接依据需后续补充《生产安全事故应急条例》第五条。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_D87EA645288648BA82AF01F8E6", "C080", "fallback", 20,
     "新组建生产经营单位投产前未编制应急预案并完成评审、备案、培训和演练的情形",
     "安全生产法第八十一条要求制定应急救援预案并定期演练，构成上位法兜底；新组建单位投产前应急预案评审、备案、培训、演练的具体程序直接依据需后续补充《生产安全事故应急条例》及配套预案管理办法。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_4AF088F48DFD4BFA88FD254F28", "C080", "fallback", 20,
     "未针对液氮储罐泄漏等具体风险编制现场应急处置方案的情形",
     "安全生产法第八十一条要求生产经营单位制定本单位生产安全事故应急救援预案，构成上位法兜底；液氮储罐泄漏专项/现场处置方案的具体编制要求直接依据需后续补充涉氨（液氮）气体相关专项安全规定。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
    ("H_9D076BD9D82444DCAA72489164", "C080", "direct", 10,
     "生产经营单位未制定事故应急救援预案的情形（与责任制、规章制度打包）",
     "hazard 包含未制定事故应急救援预案；安全生产法第八十一条要求制定本单位生产安全事故应急救援预案并定期演练，直接覆盖预案缺失这一违法事实；责任制与规章制度要素可另引第二十一条。",
     ["DIRECT_CLAUSE_APPLICABLE", "PARTIAL_COVERAGE"]),
    ("H_E67B17F6EF6D40B7A040452046", "C_BEA30FD8815D16FCA9C51BAF90", "direct", 10,
     "危险废物贮存设施未配备通讯、照明、应急防护设施及物资的情形",
     "hazard 为危废贮存设施未配备通讯、照明及应急防护设施；《危险废物贮存污染控制标准》11.2要求贮存设施所有者或运营者配备满足突发环境事件应急要求的应急人员、装备和物资并设置应急照明系统，直接对应。",
     ["DIRECT_CLAUSE_APPLICABLE"]),

    # ===== 安全教育 =====
    ("H_8A733CAD776643E3B34B4D4689", "C_217217C54423E4EC506728BB7D", "direct", 10,
     "未对员工进行安全生产技术专业培训和劳动纪律教育、考试合格持证上岗的情形",
     "hazard 为未对员工进行安全生产技术专业培训和劳动纪律教育、经考试合格持证上岗；安全生产法第二十八条要求对从业人员进行安全生产教育和培训、熟悉规章制度和安全操作规程、掌握本岗位安全操作技能，直接适用。",
     ["DIRECT_CLAUSE_APPLICABLE"]),
    ("H_E8DB5A9E2700483BA4639D3AD6", "C_217217C54423E4EC506728BB7D", "fallback", 20,
     "未将安全风险管控纳入年度安全生产教育培训计划或未组织实施的情形",
     "安全生产法第二十八条要求对从业人员进行安全生产教育和培训，构成上位法兜底；将安全风险管控纳入年度培训计划并组织实施的具体要求直接依据需后续补充风险分级管控专项规定与《生产经营单位安全培训规定》。",
     ["DIRECT_STANDARD_PENDING", "FALLBACK_ROLE"]),
]


def load_json(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    created = []
    skipped_existing = []
    for hid, cid, role, prio, applicability, reason, codes in PLAN:
        lid = h22(hid + "|" + cid)
        lpath = os.path.join(KNOW, "links", lid + ".json")
        rpath = os.path.join(KNOW, "reviews", "links", lid + ".json")
        if os.path.exists(lpath) or os.path.exists(rpath):
            skipped_existing.append((hid, cid, lid))
            continue

        hazard = load_json(os.path.join("knowledge", "hazards", hid + ".json"))
        clause = load_json(os.path.join("knowledge", "clauses", cid + ".json"))

        link = {
            "id": lid,
            "hazardId": hid,
            "clauseId": cid,
            "role": role,
            "legacyRole": "",
            "applicability": applicability,
            "jurisdictionCode": "CN",
            "lifecycle": "active",
            "priority": prio,
            "requirementId": "",
        }
        with io.open(lpath, "w", encoding="utf-8") as fh:
            json.dump(link, fh, ensure_ascii=False, indent=1)

        review = {
            "entityType": "link",
            "entityId": lid,
            "reviewType": "applicability",
            "decision": "verified",
            "reviewedContentHash": content_hash(link),
            "contextHashes": {
                "hazard": content_hash(hazard),
                "clause": content_hash(clause),
            },
            "checkedAt": NOW,
            "reviewer": "Doubao-Agent",
            "reason": reason,
            "reasonCodes": codes,
            "evidenceRefs": [],
            "migratedFromV3Verification": None,
        }
        with io.open(rpath, "w", encoding="utf-8") as fh:
            json.dump(review, fh, ensure_ascii=False, indent=1)

        created.append((lid, hid, hazard.get("title"), cid, role))
        print("created:", lid, "<-", hid, "/", cid, "(" + role + ")")

    print("\n=== SUMMARY ===")
    print("created links:", len(created))
    print("skipped existing:", len(skipped_existing))
    for s in skipped_existing:
        print("  skip:", s)
    json.dump(created, open(os.path.join(ROOT, "scratch", "my_created_links.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
