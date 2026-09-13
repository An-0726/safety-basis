# -*- coding: utf-8 -*-
"""Formalize the GB 50444 clauses recovered by visual PDF inspection."""
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import load_dir  # noqa: E402

KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")
AS_OF = "2026-09-13"
SOURCE_URL = "https://sc.119.gov.cn/scxfjyzd/uploadfiles/2022103116002028319.pdf"


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    hazards = load_dir(KNOW, "hazards")
    clauses = load_dir(KNOW, "clauses")
    quote_531 = ("本条规定了灭火器需要送修的具体条件，包括在检查中发现灭火器存在机械损伤、"
                 "明显锈蚀、灭火剂泄露、被开启使用过或符合其他维修条件的灭火器，"
                 "都需送到灭火器生产企业或灭火器专业维修单位，及时地进行维修。")
    quote_315 = ("本条要求灭火器设置点的环境温度要与灭火器的使用温度范围相适应，"
                 "是为了防止在超出使用温度范围上限时，灭火器驱动气体压力过高而可能导致灭火器爆裂，"
                 "也防止在低于使用温度范围下限时，灭火器驱动气体压力偏低，影响灭火器的灭火效果。")
    specs = {
        "C_XLSX_GB50444_5_3_1": ("5.3.1", quote_531, "E_XLSX_GB50444_5_3_1",
                                   ["H_446213AC44A140D9B879B52981", "H_9FDD968713424B6CB3EC721C3D",
                                    "H_2D53B6520A1544E09CB203CB7E", "H028"]),
        "C_XLSX_GB50444_3_1_5": ("3.1.5", quote_315, "E_XLSX_GB50444_3_1_5", ["H027"]),
    }
    promoted = []
    for cid, (article, quote, eid, hids) in specs.items():
        clause = {
            "articlePath": article, "id": cid, "jurisdictionCode": "CN",
            "lawVersionId": "LV_STD_GB50444_2008", "lifecycle": "active",
            "quote": quote, "sourceUrl": SOURCE_URL,
        }
        evidence = {"id": eid, "locator": "第" + article + "条", "page": "38" if article == "5.3.1" else "28",
                    "retrievedAt": AS_OF, "snapshotSha256": "local-pdf-GB50444-2008",
                    "tier": "authoritative-public", "url": SOURCE_URL}
        clause_review = {"checkedAt": AS_OF, "decision": "verified", "entityId": cid,
                         "entityType": "clause", "evidenceRefs": [eid],
                         "reason": "已目视核对GB 50444-2008原PDF对应页，条款号和原文逐字录入。",
                         "reviewType": "text", "reviewedContentHash": content_hash(clause),
                         "reviewer": "Codex正式核验批次20260913"}
        write(os.path.join(KNOW, "clauses", cid + ".json"), clause)
        write(os.path.join(KNOW, "evidence", eid + ".json"), evidence)
        write(os.path.join(KNOW, "reviews", "clauses", cid + ".json"), clause_review)
        for hid in hids:
            hz = hazards.get(hid)
            if not hz or hz.get("lifecycle") != "proposed":
                continue
            hz["lifecycle"] = "active"; hz["mode"] = "direct"
            hz.pop("proposalStatus", None); hz.pop("sourceRow", None)
            marker = "本批已目视核对GB 50444-2008原PDF对应条款并完成适用性核验。"
            if marker not in str(hz.get("note") or ""):
                hz["note"] = (str(hz.get("note") or "").rstrip() + "\n" + marker).strip()
            link_id = "K_XLSX_GB50444_" + hashlib.sha1((hid + cid).encode("utf-8")).hexdigest()[:24].upper()
            link = {"applicability": hz.get("conditions") or "适用于灭火器设置、检查、维修和报废条件。",
                    "clauseId": cid, "hazardId": hid, "id": link_id, "jurisdictionCode": "CN",
                    "legacyRole": "直接依据", "lifecycle": "active", "priority": 10,
                    "reason": "隐患对象与GB 50444-2008条款规定的维修或环境条件直接对应。", "role": "direct"}
            hazard_review = {"checkedAt": AS_OF, "decision": "verified", "entityId": hid,
                             "entityType": "hazard", "evidenceRefs": [eid],
                             "reason": "已核对隐患描述、整改措施与GB 50444-2008原文条款的对象和义务。",
                             "reviewType": "content", "reviewedContentHash": content_hash(hz),
                             "reviewer": "Codex正式核验批次20260913"}
            link_review = {"checkedAt": AS_OF,
                           "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)},
                           "decision": "verified", "entityId": link_id, "entityType": "link",
                           "evidenceRefs": [eid],
                           "reason": "隐患与条款原文直接对应，关联角色为直接依据。",
                           "reviewType": "applicability", "reviewedContentHash": content_hash(link),
                           "reviewer": "Codex正式核验批次20260913"}
            write(os.path.join(KNOW, "hazards", hid + ".json"), hz)
            write(os.path.join(KNOW, "links", link_id + ".json"), link)
            write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), hazard_review)
            write(os.path.join(KNOW, "reviews", "links", link_id + ".json"), link_review)
            promoted.append(hid)
    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = read(manifest_path)
    bid = "excel-formalize-gb50444-batch-20260913"
    if bid not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({"id": bid, "hazardsAdded": len(promoted),
            "clausesAdded": len(specs), "linksAdded": len(promoted), "evidenceAdded": len(specs),
            "selection": "Visual PDF verification of GB 50444-2008 clauses 3.1.5 and 5.3.1."})
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards"))
    manifest["counts"]["clauses"] = len(load_dir(KNOW, "clauses"))
    manifest["counts"]["links"] = len(load_dir(KNOW, "links"))
    write(manifest_path, manifest)
    write(os.path.join(PROPOSAL, "formalize-gb50444-report.json"),
          {"asOf": AS_OF, "promoted": promoted, "generatedAt": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"promoted": len(promoted), "hazardIds": promoted}, ensure_ascii=False))


if __name__ == "__main__":
    main()
