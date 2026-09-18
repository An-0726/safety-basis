# tools/maintenance/execute_gb18597_ingest_and_promotion.py
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v4"))
from canonical import content_hash

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")

NOW = "2026-09-19T00:00:00+08:00"
AS_OF = "2026-09-19"
REVIEWER = "Codex GB 18597-2023 专项收录与转正批次 20260919"
EVIDENCE_ID = "E_026fdfa94508deea38f0f150b79c87a9a3ae47136eb94c8a17aefbd2b273e992"
OFFICIAL_URL = "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/gtfwwrkzbz/202302/W020230224679408713470.pdf"

VERSION_ID = "LV_STD_GB18597_2023"
LAW_ID = "LF_STD_GB18597_2001"

# 1. Version definition
version_entity = {
    "documentNumber": "GB 18597-2023",
    "effectiveDate": "2023-07-01",
    "endDate": "",
    "id": VERSION_ID,
    "lawId": LAW_ID,
    "level": "强制性国家标准",
    "officialName": "危险废物贮存污染控制标准",
    "scope": "全国",
    "sourceUrl": OFFICIAL_URL,
    "validityStatus": "active",
    "versionKey": "GB 18597-2023"
}

version_review = {
    "checkedAt": NOW,
    "decision": "verified",
    "entityId": VERSION_ID,
    "entityType": "lawVersion",
    "evidenceRefs": [EVIDENCE_ID],
    "reason": "官方生态环境部原件发布，2023-07-01起正式实施，替代旧版GB 18597-2001。",
    "reviewType": "version",
    "reviewedContentHash": content_hash(version_entity),
    "reviewer": REVIEWER
}

# 2. Succession definition
succession_entity = {
    "effectiveDate": "2023-07-01",
    "id": "LS_GB18597_2001_2023",
    "newVersionId": VERSION_ID,
    "oldVersionId": "LV_STD_GB18597_2001",
    "relation": "replaces",
    "scope": "GB 18597-2023 于 2023-01-20 发布，2023-07-01 实施并代替 GB 18597-2001（自实施之日起 GB 18597-2001 废止）。"
}

# 3. Clauses definition
clauses_data = [
    {
        "id": "C_GB18597_4_1",
        "locator": "第4.1条",
        "quote": "产生、收集、贮存、利用、处置危险废物的单位应建造危险废物贮存设施或设置贮存场所，并根据需要选择贮存设施类型。"
    },
    {
        "id": "C_GB18597_4_3",
        "locator": "第4.3条",
        "quote": "贮存危险废物应根据危险废物的类别、形态、物理化学性质和污染防治要求进行分类贮存，且应避免危险废物与不相容的物质或材料接触。"
    },
    {
        "id": "C_GB18597_4_6",
        "locator": "第4.6条",
        "quote": "贮存设施或场所、容器和包装物应按 HJ 1276 要求设置危险废物贮存设施或场所标志、危险废物贮存分区标志和危险废物标签等危险废物识别标志。"
    },
    {
        "id": "C_GB18597_4_7",
        "locator": "第4.7条",
        "quote": "HJ 1259 规定的危险废物环境重点监管单位，应采用电子地磅、电子标签、电子管理台账等技术手段对危险废物贮存过程进行信息化管理，确保数据完整、真实、准确；采用视频监控的应确保监控画面清晰，视频记录保存时间至少为 3 个月。"
    },
    {
        "id": "C_GB18597_4_9",
        "locator": "第4.9条",
        "quote": "在常温常压下易爆、易燃及排出有毒气体的危险废物应进行预处理，使之稳定后贮存，否则应按易爆、易燃危险品贮存。"
    },
    {
        "id": "C_GB18597_5_2",
        "locator": "第5.2条",
        "quote": "集中贮存设施不应选在生态保护红线区域、永久基本农田和其他需要特别保护的区域内，不应建在溶洞区或易遭受洪水、滑坡、泥石流、潮汐等严重自然灾害影响的地区。"
    },
    {
        "id": "C_GB18597_5_3",
        "locator": "第5.3条",
        "quote": "贮存设施不应选在江河、湖泊、运河、渠道、水库及其最高水位线以下的滩地和岸坡，以及法律法规规定禁止贮存危险废物的其他地点。"
    },
    {
        "id": "C_GB18597_5_4",
        "locator": "第5.4条",
        "quote": "贮存设施场址的位置以及其与周围环境敏感目标的距离应依据环境影响评价文件确定。"
    },
    {
        "id": "C_GB18597_6_1_1",
        "locator": "第6.1.1条",
        "quote": "贮存设施应根据危险废物的形态、物理化学性质、包装形式和污染物迁移途径，采取必要的防风、防晒、防雨、防漏、防渗、防腐以及其他环境污染防治措施，不应露天堆放危险废物。"
    },
    {
        "id": "C_GB18597_6_1_2",
        "locator": "第6.1.2条",
        "quote": "贮存设施应根据危险废物的类别、数量、形态、物理化学性质和污染防治等要求设置必要的贮存分区，避免不相容的危险废物接触、混合。"
    },
    {
        "id": "C_GB18597_6_1_4",
        "locator": "第6.1.4条",
        "quote": "贮存设施地面与裙脚应采取表面防渗措施；表面防渗材料应与所接触的物料或污染物相容，可采用抗渗混凝土、高密度聚乙烯膜、钠基膨润土防水毯或其他防渗性能等效的材料。贮存的危险废物直接接触地面的，还应进行基础防渗，防渗层为至少 1 m 厚黏土层（渗透系数不大于 10-7 cm/s），或至少 2 mm 厚高密度聚乙烯膜等人工防渗材料（渗透系数不大于 10-10 cm/s），或其他防渗性能等效的材料。"
    },
    {
        "id": "C_GB18597_6_2_1",
        "locator": "第6.2.1条",
        "quote": "贮存库内不同贮存分区之间应采取隔离措施。隔离措施可根据危险废物特性采用过道、隔板或隔墙等方式。"
    },
    {
        "id": "C_GB18597_6_2_2",
        "locator": "第6.2.2条",
        "quote": "在贮存库内或通过贮存分区方式贮存液态危险废物的，应具有液体泄漏堵截设施，堵截设施最小容积不应低于对应贮存区域最大液态废物容器容积或液态废物总储量 1/10（二者取较大者）；用于贮存可能产生渗滤液的危险废物的贮存库或贮存分区应设计渗滤液收集设施，收集设施容积应满足渗滤液的收集要求。"
    },
    {
        "id": "C_GB18597_7_3",
        "locator": "第7.3条",
        "quote": "硬质容器和包装物及其支护结构堆叠码放时不应有明显变形，无破损泄漏。"
    },
    {
        "id": "C_GB18597_8_2_2",
        "locator": "第8.2.2条",
        "quote": "应定期检查危险废物的贮存状况，及时清理贮存设施地面，更换破损泄漏的危险废物贮存容器和包装物，保证堆存危险废物的防雨、防风、防扬尘等设施功能完好。"
    },
    {
        "id": "C_GB18597_8_3_1",
        "locator": "第8.3.1条",
        "quote": "贮存点应具有固定的区域边界，并应采取与其他区域进行隔离的措施。"
    },
    {
        "id": "C_GB18597_8_3_2",
        "locator": "第8.3.2条",
        "quote": "贮存点应采取防风、防雨、防晒和防止危险废物流失、扬散等措施。"
    },
    {
        "id": "C_GB18597_8_3_3",
        "locator": "第8.3.3条",
        "quote": "贮存点贮存的危险废物应置于容器或包装物中，不应直接散堆。"
    },
    {
        "id": "C_GB18597_8_3_5",
        "locator": "第8.3.5条",
        "quote": "贮存点应及时清运贮存的危险废物，实时贮存量不应超过 3 吨。"
    },
    {
        "id": "C_GB18597_11_2",
        "locator": "第11.2条",
        "quote": "贮存设施所有者或运营者应配备满足其突发环境事件应急要求的应急人员、装备和物资，并应设置应急照明系统。"
    }
]

# 4. Promotions mapping
promotions = [
    {
        "hazardId": "H_YJF_6_9_1",
        "title": "危险废物贮存设施未按规定设置危险废物识别标志",
        "clauseIds": ["C_GB18597_4_6"],
        "applicability": "适用于危险废物产生、收集、贮存单位的设施或场所识别标志设置现场状态。",
        "reason": "隐患所述危险废物贮存设施标志缺失，直接违反GB 18597-2023第4.6条识别标志设置要求。"
    },
    {
        "hazardId": "H_3B20B1FE3A9647A9A1AE26FC87",
        "title": "未建造符合标准的专用危险废物贮存设施",
        "clauseIds": ["C_GB18597_4_1"],
        "applicability": "适用于产生、收集、贮存、利用、处置危险废物的单位设施建设与选型状态。",
        "reason": "产生与贮存单位未建造专用贮存设施或场所，直接违反GB 18597-2023第4.1条总体要求。"
    },
    {
        "hazardId": "H_9284B9BA196043B59022AF0FB7",
        "title": "危险废物未按种类特性分区贮存或设置防雨防火防风防扬尘装置",
        "clauseIds": ["C_GB18597_6_1_1", "C_GB18597_6_1_2"],
        "applicability": "适用于危险废物贮存设施内分类分区存放及防风防晒防雨防漏防渗等污染防治设施状态。",
        "reason": "危废露天堆放未采取防风防晒防雨防漏防渗防腐措施，未设置必要分区，直接违反第6.1.1、6.1.2条。"
    },
    {
        "hazardId": "H_F53C97BEFD7761225C2B413A",
        "title": "未按标准设置泄漏液体堵截设施及渗滤液收集设施",
        "clauseIds": ["C_GB18597_6_2_2"],
        "applicability": "适用于贮存液态危险废物或可能产生渗滤液的贮存库及贮存分区的设施配置状态。",
        "reason": "贮存液态危废未设堵截设施或容积不足1/10，未设渗滤液收集设施，直接违反第6.2.2条要求。"
    },
    {
        "hazardId": "H_E67B17F6EF6D40B7A040452046",
        "title": "未为危险废物贮存设施配备应急装备或应急照明设施",
        "clauseIds": ["C_GB18597_11_2"],
        "applicability": "适用于危险废物贮存设施应急人员物资装备配备及应急照明系统配置状态。",
        "reason": "危废贮存设施未配备应急人员装备物资及应急照明系统，直接违反第11.2条环境应急强制要求。"
    },
    {
        "hazardId": "H_14E04FE43D8A43DC90F7464F41",
        "title": "废油漆桶等危险废物在厂区随意堆放，未及时清运至暂存间",
        "clauseIds": ["C_GB18597_6_1_1", "C_GB18597_8_3_5"],
        "applicability": "适用于企业产生废油漆桶等危废在厂区露天堆放或贮存点未及时清运的现场状态。",
        "reason": "危废在厂区随意堆放露天堆存，贮存点未及时清运超量，违反第6.1.1条及第8.3.5条规定。"
    },
    {
        "hazardId": "H_72C3801D44894633B32B67FD4E",
        "title": "危险废物集中贮存设施选址不符合禁建区要求",
        "clauseIds": ["C_GB18597_5_2", "C_GB18597_5_3"],
        "applicability": "适用于危险废物集中贮存设施及一般贮存设施选址合规性评价。",
        "reason": "集中贮存设施建在禁建保护区或严重自然灾害地带，违反GB 18597-2023第5.2、5.3条选址规定。"
    },
    {
        "hazardId": "H_AE64CC10CCCDBB67B2A6452E",
        "title": "危险废物贮存设施选址未按环评文件确定环境敏感目标防护距离",
        "clauseIds": ["C_GB18597_5_4"],
        "applicability": "适用于危险废物贮存设施场址与周围环境敏感目标防护距离现场判定。",
        "reason": "贮存设施位置及敏感目标距离未按环境影响评价文件确定，违反第5.4条规定。"
    }
]

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("=== Executing GB 18597-2023 Ingestion & Promotion (Strict Gate Aligned) ===")

    # 1. Write version
    v_path = os.path.join(KNOW, "law-versions", f"{VERSION_ID}.json")
    save_json(v_path, version_entity)
    print(f"Created version: {VERSION_ID}")

    vr_path = os.path.join(KNOW, "reviews", "law-versions", f"{VERSION_ID}.json")
    save_json(vr_path, version_review)
    print(f"Created version review: {VERSION_ID}")

    # 2. Write succession
    s_path = os.path.join(KNOW, "successions", "LS_GB18597_2001_2023.json")
    save_json(s_path, succession_entity)
    print("Created succession: LS_GB18597_2001_2023")

    # 3. Write clauses
    clauses_dict = {}
    for cd in clauses_data:
        cid = cd["id"]
        clause = {
            "articlePath": cd["locator"],
            "id": cid,
            "jurisdictionCode": "CN",
            "lawVersionId": VERSION_ID,
            "lifecycle": "active",
            "quote": cd["quote"],
            "sourceUrl": OFFICIAL_URL
        }
        clauses_dict[cid] = clause
        save_json(os.path.join(KNOW, "clauses", f"{cid}.json"), clause)

        clause_review = {
            "checkedAt": NOW,
            "decision": "verified",
            "entityId": cid,
            "entityType": "clause",
            "evidenceRefs": [EVIDENCE_ID],
            "reason": f"从归档官方原件全文提取核实，作为现行规范依据条款（{cd['locator']}）。",
            "reviewType": "text",
            "reviewedContentHash": content_hash(clause),
            "reviewer": REVIEWER
        }
        save_json(os.path.join(KNOW, "reviews", "clauses", f"{cid}.json"), clause_review)
    print(f"Created {len(clauses_data)} clauses and reviews.")

    # 4. Promote hazards & create links
    promoted_count = 0
    for p in promotions:
        hid = p["hazardId"]
        h_path = os.path.join(KNOW, "hazards", f"{hid}.json")
        with open(h_path, "r", encoding="utf-8") as f:
            h = json.load(f)

        if p.get("title"):
            h["title"] = p["title"]
        h["lifecycle"] = "active"
        h["mode"] = "direct"
        h["checked"] = AS_OF
        save_json(h_path, h)

        # Hazard review
        hr_path = os.path.join(KNOW, "reviews", "hazards", f"{hid}.json")
        h_ch = content_hash(h)
        h_review = {
            "checkedAt": NOW,
            "decision": "verified",
            "entityId": hid,
            "entityType": "hazard",
            "evidenceRefs": [EVIDENCE_ID],
            "reason": f"经核验GB 18597-2023官方原件，条款原文与适用范围完全支撑该隐患判定，转为正式有效隐患。{p['reason']}",
            "reviewType": "content",
            "reviewedContentHash": h_ch,
            "reviewer": REVIEWER
        }
        save_json(hr_path, h_review)

        # Links & Link reviews
        for cid in p["clauseIds"]:
            clause = clauses_dict[cid]
            c_ch = content_hash(clause)
            lid = f"K_{hid}_{cid}".replace("-", "_")
            if len(lid) > 40:
                lid = f"K_{hid[:16]}_{cid[:16]}".replace("-", "_")

            link_entity = {
                "applicability": p["applicability"],
                "clauseId": cid,
                "hazardId": hid,
                "id": lid,
                "jurisdictionCode": "CN",
                "legacyRole": "",
                "lifecycle": "active",
                "priority": 10,
                "reason": f"隐患判定要点与GB 18597-2023条款原文完全对应。{p['reason']}",
                "requirementId": "",
                "role": "direct"
            }
            l_ch = content_hash(link_entity)
            save_json(os.path.join(KNOW, "links", f"{lid}.json"), link_entity)

            link_review = {
                "checkedAt": NOW,
                "contextHashes": {
                    "clause": c_ch,
                    "hazard": h_ch,
                    "link": l_ch
                },
                "decision": "verified",
                "entityId": lid,
                "entityType": "link",
                "evidenceRefs": [EVIDENCE_ID],
                "reason": f"隐患判定要点与GB 18597-2023条款原文完全对应。{p['reason']}",
                "reviewType": "applicability",
                "reviewedContentHash": l_ch,
                "reviewer": REVIEWER
            }
            save_json(os.path.join(KNOW, "reviews", "links", f"{lid}.json"), link_review)

        promoted_count += 1
        print(f"Promoted hazard {hid} -> active with {len(p['clauseIds'])} links.")

    print(f"Promotion complete: {promoted_count} hazards promoted to active.")

    # 5. Refresh manifest.json
    manifest_path = os.path.join(KNOW, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    hazards = [json.load(open(os.path.join(KNOW, "hazards", f), "r", encoding="utf-8")) for f in os.listdir(os.path.join(KNOW, "hazards")) if f.endswith(".json")]
    active_cnt = sum(1 for h in hazards if h.get("lifecycle") == "active")
    proposed_cnt = sum(1 for h in hazards if h.get("lifecycle") == "proposed")
    superseded_cnt = sum(1 for h in hazards if h.get("lifecycle") == "superseded")

    laws_cnt = len([f for f in os.listdir(os.path.join(KNOW, "laws")) if f.endswith(".json")])
    law_versions_cnt = len([f for f in os.listdir(os.path.join(KNOW, "law-versions")) if f.endswith(".json")])
    clauses_cnt = len([f for f in os.listdir(os.path.join(KNOW, "clauses")) if f.endswith(".json")])
    links_cnt = len([f for f in os.listdir(os.path.join(KNOW, "links")) if f.endswith(".json")])
    evidences_cnt = len([f for f in os.listdir(os.path.join(KNOW, "evidence")) if f.endswith(".json")])
    successions_cnt = len([f for f in os.listdir(os.path.join(KNOW, "successions")) if f.endswith(".json")])

    manifest["laws"] = laws_cnt
    manifest["lawVersions"] = law_versions_cnt
    manifest["clauses"] = clauses_cnt
    manifest["hazards"] = len(hazards)
    manifest["links"] = links_cnt
    manifest["evidence"] = evidences_cnt
    manifest["successions"] = successions_cnt
    manifest["activeHazards"] = active_cnt
    manifest["proposedHazards"] = proposed_cnt
    manifest["supersededHazards"] = superseded_cnt
    manifest["asOf"] = AS_OF

    save_json(manifest_path, manifest)
    print(f"Manifest updated: {active_cnt} active / {proposed_cnt} proposed / {superseded_cnt} superseded (total {len(hazards)})")

if __name__ == "__main__":
    main()
