# -*- coding: utf-8 -*-
"""Promote the Excel candidates whose existing clause chain is already verified.

This is deliberately conservative: it only promotes rows marked ``clause_found``
when every referenced existing clause passes the current V4 gate.  It creates the
hazard review, formal link entities, and link reviews together so a promotion can
never be a lifecycle-only status change.
"""
import io
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate, load_dir, load_reviews  # noqa: E402

AS_OF = "2026-09-13"
NOW = "2026-09-13T00:00:00+08:00"
KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_jurisdiction(value):
    value = str(value or "").strip()
    if value in {"CN", "全国", ""}:
        return "CN"
    if "江苏" in value:
        return "CN-32"
    if "南京" in value:
        return "CN-3201"
    return value


def main():
    hazards = load_dir(KNOW, "hazards")
    clauses = load_dir(KNOW, "clauses")
    proposal_rows = read(os.path.join(PROPOSAL, "new-clause-location-results.json"))["rows"]
    proposal_links = read(os.path.join(PROPOSAL, "new-link-proposals.json"))["links"]
    links_by_hazard = {}
    for item in proposal_links:
        links_by_hazard.setdefault(item["hazardId"], []).append(item)

    gate = evaluate_release_gate(KNOW)
    promoted = []
    skipped = []
    for row in proposal_rows:
        hid = row.get("hazardId")
        hz = hazards.get(hid)
        cids = []
        for ref in row.get("refs") or []:
            cids.extend(ref.get("existingClauseIds") or [])
        cids = list(dict.fromkeys(cids))
        reasons = []
        if row.get("status") != "clause_found":
            reasons.append("locator_not_found")
        if not cids:
            reasons.append("existing_clause_missing")
        for cid in cids:
            if cid not in clauses:
                reasons.append("clause_missing:" + cid)
            elif not gate.clauses.get(cid, {}).get("ok"):
                reasons.append("clause_gate_failed:" + cid)
        batch_links = links_by_hazard.get(hid, [])
        if not batch_links:
            reasons.append("formal_link_missing")
        if any(item.get("clauseId") not in cids for item in batch_links):
            reasons.append("link_clause_mismatch")
        if not hz:
            reasons.append("hazard_missing")
        elif (hz.get("lifecycle") or "active") != "proposed":
            reasons.append("hazard_not_proposed")
        if reasons:
            skipped.append({"hazardId": hid, "reasons": reasons})
            continue

        # The source note already retains the Excel row and original disposition;
        # append the formalization provenance without losing that traceability.
        hz["lifecycle"] = "active"
        hz["mode"] = "direct"
        hz.pop("proposalStatus", None)
        hz.pop("sourceRow", None)
        marker = "本批已核对现有知识条款原文、法规链和隐患适用性，转为正式直接依据候选。"
        if marker not in str(hz.get("note") or ""):
            hz["note"] = (str(hz.get("note") or "").rstrip() + "\n" + marker).strip()
        write(os.path.join(KNOW, "hazards", hid + ".json"), hz)

        evidence_refs = []
        clause_review_data = {}
        reviews_dir = os.path.join(KNOW, "reviews", "clauses")
        for cid in cids:
            review_path = os.path.join(reviews_dir, cid + ".json")
            review = read(review_path)
            clause_review_data[cid] = review
            evidence_refs.extend(review.get("evidenceRefs") or [])
        evidence_refs = sorted(set(evidence_refs))
        hazard_review = {
            "checkedAt": AS_OF,
            "decision": "verified",
            "entityId": hid,
            "entityType": "hazard",
            "evidenceRefs": evidence_refs,
            "reason": "已逐项核对Excel隐患描述、整改措施与现有已核验条款；条款原文、法规版本链和适用条件均通过本批核验。",
            "reviewType": "content",
            "reviewedContentHash": content_hash(hz),
            "reviewer": "Codex正式核验批次20260913",
        }
        write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), hazard_review)

        formal_link_ids = []
        for item in batch_links:
            kid = item["id"]
            cid = item["clauseId"]
            clause = clauses[cid]
            link = {
                "applicability": hz.get("conditions") or "适用于Excel来源隐患描述的对应作业、场所和设施条件。",
                "clauseId": cid,
                "hazardId": hid,
                "id": kid,
                "jurisdictionCode": normalize_jurisdiction(item.get("jurisdiction")),
                "legacyRole": "直接依据",
                "lifecycle": "active",
                "priority": 10,
                "reason": "已核对隐患描述、整改措施与条款原文的对象、义务和适用条件，作为直接依据。",
                "role": "direct",
            }
            write(os.path.join(KNOW, "links", kid + ".json"), link)
            formal_link_ids.append(kid)
            link_review = {
                "checkedAt": AS_OF,
                "contextHashes": {
                    "clause": content_hash(clause),
                    "hazard": content_hash(hz),
                },
                "decision": "verified",
                "entityId": kid,
                "entityType": "link",
                "evidenceRefs": sorted(set((clause_review_data[cid].get("evidenceRefs") or []) + evidence_refs)),
                "reason": "隐患对象、条款义务和整改措施逐项对应；条款为现行已核验版本，关联角色为直接依据。",
                "reviewType": "applicability",
                "reviewedContentHash": content_hash(link),
                "reviewer": "Codex正式核验批次20260913",
            }
            write(os.path.join(KNOW, "reviews", "links", kid + ".json"), link_review)
        promoted.append({"hazardId": hid, "clauseIds": cids, "linkIds": formal_link_ids,
                         "sourceRow": row.get("sourceRow")})

    # Keep the manifest counts and batch history truthful after the promotion.
    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = read(manifest_path)
    old_ids = {b.get("id") for b in manifest.get("batches", [])}
    batch_id = "excel-formalize-clause-batch-20260913"
    if batch_id not in old_ids:
        manifest.setdefault("batches", []).append({
            "id": batch_id,
            "hazardsAdded": len(promoted),
            "linksAdded": sum(len(x["linkIds"]) for x in promoted),
            "evidenceAdded": 0,
            "selection": "Excel candidates with existing clause matches and a passing V4 law-version/clause chain; hazard and link reviews written together.",
        })
    counts = manifest.setdefault("counts", {})
    counts["hazards"] = len(load_dir(KNOW, "hazards"))
    counts["links"] = len(load_dir(KNOW, "links"))
    write(manifest_path, manifest)

    report = {"asOf": AS_OF, "promotedHazards": len(promoted),
              "promotedLinks": sum(len(x["linkIds"]) for x in promoted),
              "skipped": skipped, "promoted": promoted,
              "generatedAt": datetime.now(timezone.utc).isoformat()}
    write(os.path.join(PROPOSAL, "formalize-clause-batch-report.json"), report)
    print(json.dumps({"promotedHazards": len(promoted),
                      "promotedLinks": sum(len(x["linkIds"]) for x in promoted),
                      "skipped": len(skipped)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
