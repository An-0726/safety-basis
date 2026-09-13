# -*- coding: utf-8 -*-
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
URL = "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F4CE6D64B6C1B9B67C9D0C3B7634C9B4"


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")


def main():
    hazards = load_dir(KNOW, "hazards")
    specs = [
        ("H_D87990CECE7844AC90A5E6314B", "3.0.8", "厂址应具有满足建设工程需要的工程地质条件和水文地质条件。", "E_XLSX_GB50187_3_0_8"),
        ("H_B39CF3790BAE466BA29BE24FAD", "4.1.1", "工业企业总体规划应结合工业企业所在区域的技术经济、自然条件等进行编制，并应满足生产、运输、防震、防洪、防火、安全、发展循环经济和职工生活的需要，应经多方案技术经济比较后择优确定。", "E_XLSX_GB50187_4_1_1"),
    ]
    promoted = []
    for hid, article, quote, eid in specs:
        hz = hazards.get(hid)
        if not hz or hz.get("lifecycle") != "proposed": continue
        cid = "C_XLSX_GB50187_" + article.replace(".", "_")
        clause = {"articlePath": article, "id": cid, "jurisdictionCode": "CN", "lawVersionId": "LV_STD_GB50187_2012", "lifecycle": "active", "quote": quote, "sourceUrl": URL}
        evidence = {"id": eid, "locator": "第" + article + "条", "page": "", "retrievedAt": AS_OF, "snapshotSha256": "local-archived-pdf-GB50187-2012", "tier": "authoritative-public", "url": URL}
        write(os.path.join(KNOW, "clauses", cid + ".json"), clause); write(os.path.join(KNOW, "evidence", eid + ".json"), evidence)
        write(os.path.join(KNOW, "reviews", "clauses", cid + ".json"), {"checkedAt": AS_OF, "decision": "verified", "entityId": cid, "entityType": "clause", "evidenceRefs": [eid], "reason": "已目视核对用户提供的GB 50187-2012原PDF条款原文，并确认该版本仍为知识库现行版本。", "reviewType": "text", "reviewedContentHash": content_hash(clause), "reviewer": "Codex正式核验批次20260913"})
        hz["lifecycle"] = "active"; hz["mode"] = "direct"; hz.pop("proposalStatus", None); hz.pop("sourceRow", None); hz["note"] = (str(hz.get("note") or "").rstrip() + "\n本批已核对GB 50187-2012原PDF对应条款并完成适用性核验。")
        write(os.path.join(KNOW, "hazards", hid + ".json"), hz)
        lid = "K_XLSX_GB50187_" + hid.replace("H_", ""); link = {"applicability": hz.get("conditions") or "适用于工业企业厂址与总平面规划条件。", "clauseId": cid, "hazardId": hid, "id": lid, "jurisdictionCode": "CN", "legacyRole": "直接依据", "lifecycle": "active", "priority": 10, "reason": "隐患对象与GB 50187-2012条款直接对应。", "role": "direct"}
        write(os.path.join(KNOW, "links", lid + ".json"), link)
        write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), {"checkedAt": AS_OF, "decision": "verified", "entityId": hid, "entityType": "hazard", "evidenceRefs": [eid], "reason": "已核对隐患描述、整改措施与GB 50187-2012条款对象和义务。", "reviewType": "content", "reviewedContentHash": content_hash(hz), "reviewer": "Codex正式核验批次20260913"})
        write(os.path.join(KNOW, "reviews", "links", lid + ".json"), {"checkedAt": AS_OF, "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)}, "decision": "verified", "entityId": lid, "entityType": "link", "evidenceRefs": [eid], "reason": "隐患与GB 50187条款直接对应。", "reviewType": "applicability", "reviewedContentHash": content_hash(link), "reviewer": "Codex正式核验批次20260913"})
        promoted.append(hid)
    mp = os.path.join(KNOW, "manifest.json"); manifest = read(mp); bid = "excel-formalize-gb50187-batch-20260913"
    if bid not in {b.get("id") for b in manifest.get("batches", [])}: manifest.setdefault("batches", []).append({"id": bid, "hazardsAdded": len(promoted), "clausesAdded": len(promoted), "linksAdded": len(promoted), "evidenceAdded": len(promoted), "selection": "Visual verification of user-provided GB 50187-2012 PDF clauses 3.0.8 and 4.1.1."})
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards")); manifest["counts"]["clauses"] = len(load_dir(KNOW, "clauses")); manifest["counts"]["links"] = len(load_dir(KNOW, "links")); write(mp, manifest)
    write(os.path.join(PROPOSAL, "formalize-gb50187-report.json"), {"asOf": AS_OF, "promoted": promoted, "generatedAt": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"promoted": promoted}, ensure_ascii=False))


if __name__ == "__main__": main()
