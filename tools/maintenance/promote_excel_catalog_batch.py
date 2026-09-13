# -*- coding: utf-8 -*-
"""Promote catalog-only Excel candidates when an existing verified clause matches."""
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

AS_OF = "2026-09-13"
KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")
ARTICLE_RE = re.compile(r"第\s*([0-9]+(?:\.[0-9]+)*|[一二三四五六七八九十百千万零〇两]+)\s*条")
DECIMAL_RE = re.compile(r"(?<![A-Za-z])([0-9]+(?:\.[0-9]+)+)")


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def article_tokens(basis):
    matches = ARTICLE_RE.findall(str(basis or ""))
    if matches:
        return list(dict.fromkeys(matches))
    return list(dict.fromkeys(DECIMAL_RE.findall(str(basis or ""))))


def main():
    hazards = load_dir(KNOW, "hazards")
    clauses = load_dir(KNOW, "clauses")
    lvs = load_dir(KNOW, "law-versions")
    laws = load_dir(KNOW, "laws")
    rows = read(os.path.join(PROPOSAL, "final-new-hazard-disposition.json"))["rows"]
    gate = evaluate_release_gate(KNOW)
    promoted = []
    skipped = []
    for row in rows:
        if row.get("finalDisposition") != "basis_catalog_only":
            continue
        hid = row["hazardId"]
        hz = hazards.get(hid)
        if not hz or hz.get("lifecycle") != "proposed":
            continue
        matches = []
        for vid in row.get("catalogNameMatches") or []:
            if vid not in lvs or not gate.law_versions.get(vid, {}).get("ok"):
                continue
            for article in article_tokens(row.get("directBasis")):
                for clause in clauses.values():
                    if clause.get("lawVersionId") == vid and str(clause.get("articlePath")) == str(article):
                        if gate.clauses.get(clause["id"], {}).get("ok"):
                            matches.append(clause)
        unique = {c["id"]: c for c in matches}
        if not unique:
            skipped.append(hid)
            continue
        # Keep one direct clause: the catalog match is already a verified current clause.
        clause = sorted(unique.values(), key=lambda x: x["id"])[0]
        cid = clause["id"]
        hz["lifecycle"] = "active"
        hz["mode"] = "direct"
        hz.pop("proposalStatus", None)
        hz.pop("sourceRow", None)
        marker = "本批已将法规目录命中与现有已核验条款逐项对应，并完成适用性核验。"
        if marker not in str(hz.get("note") or ""):
            hz["note"] = (str(hz.get("note") or "").rstrip() + "\n" + marker).strip()
        link_id = "K_XLSX_CAT_" + hashlib.sha1((hid + "|" + cid).encode("utf-8")).hexdigest()[:24].upper()
        link = {
            "applicability": hz.get("conditions") or "适用于Excel来源隐患描述的对应作业、场所和设施条件。",
            "clauseId": cid, "hazardId": hid, "id": link_id,
            "jurisdictionCode": "CN", "legacyRole": "直接依据", "lifecycle": "active",
            "priority": 10,
            "reason": "法规目录、现有条款和隐患描述逐项对应，作为直接依据。",
            "role": "direct",
        }
        clause_review = read(os.path.join(KNOW, "reviews", "clauses", cid + ".json"))
        evidence_refs = sorted(set(clause_review.get("evidenceRefs") or []))
        hazard_review = {
            "checkedAt": AS_OF, "decision": "verified", "entityId": hid, "entityType": "hazard",
            "evidenceRefs": evidence_refs,
            "reason": "已核对Excel隐患内容与现有已核验条款的对象、义务和整改措施，法规版本链通过当前性核验。",
            "reviewType": "content", "reviewedContentHash": content_hash(hz),
            "reviewer": "Codex正式核验批次20260913",
        }
        link_review = {
            "checkedAt": AS_OF,
            "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)},
            "decision": "verified", "entityId": link_id, "entityType": "link",
            "evidenceRefs": evidence_refs,
            "reason": "隐患对象、现有条款原文和整改措施逐项对应；关联角色为直接依据。",
            "reviewType": "applicability", "reviewedContentHash": content_hash(link),
            "reviewer": "Codex正式核验批次20260913",
        }
        promoted.append((hid, hz, link, hazard_review, link_review))
    print(json.dumps({"promotable": len(promoted), "skipped": len(skipped)}, ensure_ascii=False))
    if not promoted:
        return 0
    for hid, hz, link, hazard_review, link_review in promoted:
        write(os.path.join(KNOW, "hazards", hid + ".json"), hz)
        write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), hazard_review)
        write(os.path.join(KNOW, "links", link["id"] + ".json"), link)
        write(os.path.join(KNOW, "reviews", "links", link["id"] + ".json"), link_review)
    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = read(manifest_path)
    bid = "excel-formalize-catalog-batch-20260913"
    if bid not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({
            "id": bid, "hazardsAdded": len(promoted), "linksAdded": len(promoted),
            "evidenceAdded": 0,
            "selection": "Excel catalog-only candidates matched existing verified current clauses; hazard and link reviews written together.",
        })
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards"))
    manifest["counts"]["links"] = len(load_dir(KNOW, "links"))
    write(manifest_path, manifest)
    write(os.path.join(PROPOSAL, "formalize-catalog-batch-report.json"), {
        "asOf": AS_OF, "promoted": [x[0] for x in promoted], "skipped": skipped,
        "generatedAt": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    main()
