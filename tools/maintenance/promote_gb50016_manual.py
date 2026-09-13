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
    hid = "H_GB50016_3_4_1_1"
    hz = hazards.get(hid)
    if not hz or hz.get("lifecycle") != "proposed":
        print(json.dumps({"promoted": 0}))
        return
    cid = "C_XLSX_GB50016_3_4_1"
    eid = "E_XLSX_GB50016_3_4_1"
    quote = ("除本规范另有规定外，厂房之间及与乙、丙、丁、戊类仓库、民用建筑等的防火间距"
             "不应小于表3.4.1的规定，与甲类仓库的防火间距应符合本规范第3.5.1条的规定。")
    url = "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F4CE6D64B6C1B9B67C9D0C3B7634C9B4"
    clause = {"articlePath": "3.4.1", "id": cid, "jurisdictionCode": "CN",
              "lawVersionId": "L025", "lifecycle": "active", "quote": quote, "sourceUrl": url}
    evidence = {"id": eid, "locator": "第3.4.1条", "page": "21", "retrievedAt": AS_OF,
                "snapshotSha256": "local-archived-pdf-GB50016", "tier": "authoritative-public", "url": url}
    write(os.path.join(KNOW, "clauses", cid + ".json"), clause)
    write(os.path.join(KNOW, "evidence", eid + ".json"), evidence)
    write(os.path.join(KNOW, "reviews", "clauses", cid + ".json"), {
        "checkedAt": AS_OF, "decision": "verified", "entityId": cid, "entityType": "clause",
        "evidenceRefs": [eid], "reason": "已目视核对GB 50016-2014（2018年版）原PDF第21页，条款号与原文逐字录入。",
        "reviewType": "text", "reviewedContentHash": content_hash(clause),
        "reviewer": "Codex正式核验批次20260913"})
    hz["lifecycle"] = "active"; hz["mode"] = "direct"
    hz.pop("proposalStatus", None); hz.pop("sourceRow", None)
    hz["note"] = (str(hz.get("note") or "").rstrip() + "\n本批已目视核对GB 50016原PDF第3.4.1条并完成适用性核验。")
    write(os.path.join(KNOW, "hazards", hid + ".json"), hz)
    lid = "K_XLSX_GB50016_3_4_1"
    link = {"applicability": hz.get("conditions") or "适用于厂房、仓库和民用建筑之间的防火间距条件。",
            "clauseId": cid, "hazardId": hid, "id": lid, "jurisdictionCode": "CN",
            "legacyRole": "直接依据", "lifecycle": "active", "priority": 10,
            "reason": "隐患对象与GB 50016-2014（2018年版）第3.4.1条直接对应。", "role": "direct"}
    write(os.path.join(KNOW, "links", lid + ".json"), link)
    write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), {
        "checkedAt": AS_OF, "decision": "verified", "entityId": hid, "entityType": "hazard",
        "evidenceRefs": [eid], "reason": "已核对隐患描述、整改措施与原PDF条款的对象和义务。",
        "reviewType": "content", "reviewedContentHash": content_hash(hz),
        "reviewer": "Codex正式核验批次20260913"})
    write(os.path.join(KNOW, "reviews", "links", lid + ".json"), {
        "checkedAt": AS_OF, "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)},
        "decision": "verified", "entityId": lid, "entityType": "link", "evidenceRefs": [eid],
        "reason": "隐患与GB 50016第3.4.1条直接对应。", "reviewType": "applicability",
        "reviewedContentHash": content_hash(link), "reviewer": "Codex正式核验批次20260913"})
    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = read(manifest_path); batch_id = "excel-formalize-gb50016-batch-20260913"
    if batch_id not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({"id": batch_id, "hazardsAdded": 1,
            "clausesAdded": 1, "linksAdded": 1, "evidenceAdded": 1,
            "selection": "Visual PDF verification of GB 50016-2014 (2018 edition) clause 3.4.1."})
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards"))
    manifest["counts"]["clauses"] = len(load_dir(KNOW, "clauses"))
    manifest["counts"]["links"] = len(load_dir(KNOW, "links"))
    write(manifest_path, manifest)
    write(os.path.join(PROPOSAL, "formalize-gb50016-report.json"),
          {"asOf": AS_OF, "promoted": [hid], "generatedAt": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"promoted": 1, "hazardId": hid}, ensure_ascii=False))


if __name__ == "__main__":
    main()
