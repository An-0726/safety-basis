# -*- coding: utf-8 -*-
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
    cid = "C_XLSX_SAN_TONG_4"
    eid = "E_XLSX_SAN_TONG_4"
    url = "https://www.mem.gov.cn/gk/gwgg/agwzlfl/zjl_01/201504/t20150402_233762.shtml"
    quote = ("生产经营单位是建设项目安全设施建设的责任主体。建设项目安全设施必须与主体工程"
             "同时设计、同时施工、同时投入生产和使用（以下简称‘三同时’）。安全设施投资应当纳入建设项目概算。")
    clause = {"articlePath": "4", "id": cid, "jurisdictionCode": "CN",
              "lawVersionId": "LV_REG_SAN_TONG_SHI_2011", "lifecycle": "active",
              "quote": quote, "sourceUrl": url}
    evidence = {"id": eid, "locator": "第四条", "page": "", "retrievedAt": AS_OF,
                "snapshotSha256": "official-mem-html", "tier": "authoritative-public", "url": url}
    write(os.path.join(KNOW, "clauses", cid + ".json"), clause)
    write(os.path.join(KNOW, "evidence", eid + ".json"), evidence)
    write(os.path.join(KNOW, "reviews", "clauses", cid + ".json"), {
        "checkedAt": AS_OF, "decision": "verified", "entityId": cid, "entityType": "clause",
        "evidenceRefs": [eid], "reason": "已核对应急管理部官方全文第4条原文。",
        "reviewType": "text", "reviewedContentHash": content_hash(clause),
        "reviewer": "Codex正式核验批次20260913"})
    promoted = []
    for hid in ["H_SANTONGSHI_4_1", "H_SANTONGSHI_4_2"]:
        hz = hazards.get(hid)
        if not hz or hz.get("lifecycle") != "proposed":
            continue
        hz["lifecycle"] = "active"; hz["mode"] = "direct"
        hz.pop("proposalStatus", None); hz.pop("sourceRow", None)
        hz["note"] = (str(hz.get("note") or "").rstrip() +
                      "\n本批已核对国家应急管理部官方全文《建设项目安全设施‘三同时’监督管理办法》第4条。")
        write(os.path.join(KNOW, "hazards", hid + ".json"), hz)
        lid = "K_XLSX_SAN_TONG_" + hashlib.sha1(hid.encode()).hexdigest()[:24].upper()
        link = {"applicability": hz.get("conditions") or "适用于建设项目安全设施同时设计、同时施工、同时投入生产和使用的条件。",
                "clauseId": cid, "hazardId": hid, "id": lid, "jurisdictionCode": "CN",
                "legacyRole": "直接依据", "lifecycle": "active", "priority": 10,
                "reason": "隐患与‘三同时’条款直接对应。", "role": "direct"}
        write(os.path.join(KNOW, "links", lid + ".json"), link)
        write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), {
            "checkedAt": AS_OF, "decision": "verified", "entityId": hid, "entityType": "hazard",
            "evidenceRefs": [eid], "reason": "隐患内容与‘三同时’义务直接对应。",
            "reviewType": "content", "reviewedContentHash": content_hash(hz),
            "reviewer": "Codex正式核验批次20260913"})
        write(os.path.join(KNOW, "reviews", "links", lid + ".json"), {
            "checkedAt": AS_OF, "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)},
            "decision": "verified", "entityId": lid, "entityType": "link", "evidenceRefs": [eid],
            "reason": "隐患与第4条直接对应。", "reviewType": "applicability",
            "reviewedContentHash": content_hash(link), "reviewer": "Codex正式核验批次20260913"})
        promoted.append(hid)
    mp = os.path.join(KNOW, "manifest.json")
    manifest = read(mp); bid = "excel-formalize-santongshi-batch-20260913"
    if bid not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({"id": bid, "hazardsAdded": len(promoted),
            "clausesAdded": 1, "linksAdded": len(promoted), "evidenceAdded": 1,
            "selection": "Official Ministry of Emergency Management fulltext verification of the Three Simultaneous Construction Measures Article 4."})
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards"))
    manifest["counts"]["clauses"] = len(load_dir(KNOW, "clauses"))
    manifest["counts"]["links"] = len(load_dir(KNOW, "links"))
    write(mp, manifest)
    write(os.path.join(PROPOSAL, "formalize-santongshi-report.json"),
          {"asOf": AS_OF, "promoted": promoted, "generatedAt": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"promoted": promoted}, ensure_ascii=False))


if __name__ == "__main__":
    main()
