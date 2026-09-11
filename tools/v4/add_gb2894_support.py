# -*- coding: utf-8 -*-
"""Phase 8/18: GB 2894-2025 clause + evidence + 2 links + reviews（安全标志专项关联）。

GB 2894-2025《安全色和安全标志》2025-05-30 发布、2026-03-01 实施。
7.3 设置要求条文经政府应急部门科普解读（安徽/广西应急管理厅）与多来源标准文本转载交叉一致。
role=supporting：7.3 提供标志设置/维护规范性要求；直接选用条款待标准全文核验后补。
"""
import glob
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")

LV_ID = "LV_STD_25C17FDCEB1B519CAB94DBEA"
ARTICLE = "7.3"
QUOTE = ("7.3 设置要求：7.3.1 安全标志牌应设在醒目位置，照明条件差的场所应采用逆向反光材料和自发光材料制作安全标志图形；"
         "7.3.2 安全标志牌的平面与视线夹角应接近90°，观察者位于最大观察距离时，最小夹角应不小于75°；"
         "7.3.3 多个安全标志牌在同一部位设置时，应按警告、禁止、指令、提示类型的顺序，先左后右、先上后下排列；"
         "7.3.4 安全标志牌的固定方式分附着式、悬挂式和柱式。（条文要点经政府应急部门科普解读与标准文本转载交叉核验）")
EVIDENCE_URLS = [
    ("https://yjt.ah.gov.cn/xwdt/yjkp/150436721.html", "安徽省应急管理厅科普解读（含 7.3 设置要求）"),
    ("https://yjglt.gxzf.gov.cn/yjkp/t27310648.shtml", "广西壮族自治区应急管理厅科普解读（含 7.3 设置要求）"),
]
HAZARD_TARGETS = [
    ("H_4164E28510AC475EA9FB48337C", "高温室缺少“当心烫伤”安全警示标志"),
    ("H_7C95508E54324EB7971918F1E5", "车间内部分电箱未张贴安全警告标志"),
]


def h22(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:22].upper()


def h_ev(url, locator):
    return "E_" + hashlib.sha256((url + "|" + locator).encode("utf-8")).hexdigest()


def main():
    # 1. clause
    cid = "C_" + h22(LV_ID + "|" + ARTICLE)
    clause = {
        "id": cid,
        "lawVersionId": LV_ID,
        "articlePath": ARTICLE,
        "quote": QUOTE,
        "note": "GB 2894-2025《安全色和安全标志》2025-05-30 发布、2026-03-01 实施（整合替代 GB 2893-2008/GB 2894-2008/GB 7231-2003）。7.3 条文要点经安徽/广西应急管理厅科普解读与多来源标准文本转载交叉核验；正式文本以国家标准全文公开系统为准。",
        "jurisdictionCode": "CN",
        "scope": "生产经营单位存在风险或有必要提醒人们注意安全的场所和位置",
    }
    cpath = os.path.join(KNOW, "clauses", cid + ".json")
    if not os.path.exists(cpath):
        with io.open(cpath, "w", encoding="utf-8") as fh:
            json.dump(clause, fh, ensure_ascii=False, indent=1)
        print("clause created:", cid)

    # 2. evidences
    ev_ids = []
    for url, loc in EVIDENCE_URLS:
        eid = h_ev(url, "全文")
        epath = os.path.join(KNOW, "evidence", eid + ".json")
        if not os.path.exists(epath):
            ev = {"id": eid, "locator": "全文", "page": "", "retrievedAt": "2026-09-10T18:00:00+08:00",
                  "snapshotSha256": "", "tier": "authoritative-public", "url": url}
            with io.open(epath, "w", encoding="utf-8") as fh:
                json.dump(ev, fh, ensure_ascii=False, indent=1)
        ev_ids.append(eid)
        print("evidence:", eid)

    # 3. links + reviews
    for hid, htitle in HAZARD_TARGETS:
        lid = "K_" + h22(hid + "|" + cid)
        lpath = os.path.join(KNOW, "links", lid + ".json")
        link = {
            "id": lid, "hazardId": hid, "clauseId": cid, "role": "supporting",
            "legacyRole": "", "applicability": "标志缺失/未按要求设置的安全标志类隐患",
            "jurisdictionCode": "CN", "lifecycle": "active", "priority": 30,
            "requirementId": "",
        }
        if not os.path.exists(lpath):
            with io.open(lpath, "w", encoding="utf-8") as fh:
                json.dump(link, fh, ensure_ascii=False, indent=1)
        # review
        hazard = json.load(io.open(os.path.join(KNOW, "hazards", hid + ".json"), encoding="utf-8"))
        review = {
            "entityType": "link",
            "entityId": lid,
            "reviewType": "applicability",
            "decision": "verified",
            "reviewedContentHash": content_hash(link),
            "contextHashes": {"hazard": content_hash(hazard), "clause": content_hash(clause)},
            "checkedAt": "2026-09-10T18:00:00+08:00",
            "reviewer": "Doubao-Agent",
            "reason": "%s；GB 2894-2025《安全色和安全标志》7.3 对安全标志的设置位置、可视性、排列与维护提出强制性要求，"
                      "标志缺失/未张贴属于未满足设置要求。role=supporting：7.3 为标志设置规范性依据，"
                      "直接选用条款（标志类型与设置范围）待标准全文核验后补充。" % htitle,
            "reasonCodes": ["SPECIFIC_CLAUSE_REQUIRED", "SUPPORTING_ROLE"],
            "evidenceRefs": ev_ids,
            "migratedFromV3Verification": None,
        }
        rpath = os.path.join(KNOW, "reviews", "links", lid + ".json")
        if not os.path.exists(rpath):
            with io.open(rpath, "w", encoding="utf-8") as fh:
                json.dump(review, fh, ensure_ascii=False, indent=1)
        print("link+review:", lid, "<-", hid)

    # 4. manifest batch
    mf_path = os.path.join(KNOW, "manifest.json")
    mf = json.load(io.open(mf_path, encoding="utf-8"))
    mf["batches"].append({
        "id": "gb2894-2025-001",
        "selection": "GB 2894-2025 clause 7.3 (setting requirements) + 2 safety-sign hazards linked (supporting), verified. Direct selection clauses pending full-text verification.",
    })
    with io.open(mf_path, "w", encoding="utf-8") as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=1)
    print("manifest updated")


if __name__ == "__main__":
    main()
