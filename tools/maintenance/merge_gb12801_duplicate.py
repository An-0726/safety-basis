# -*- coding: utf-8 -*-
"""Merge the GB 12801-2025 duplicate into the existing canonical hazard.

The new edition is not effective until 2026-10-01, so the source candidate
stays out of the current-basis projection.  Its subject is nevertheless an
obvious duplicate of the already reviewed hazard whose succession mapping
already points to GB 12801-2025 article 5.7.5.  This script records that
deduplication without inventing a second hazard or treating the upcoming
edition as effective early.
"""
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
PAIRS = (
    ("H_B085FE55797E498897B61DCA10", "H_GB12801_5_4_6_1", "安全通道"),
    ("H_608147EE09234EBC92B53F842A", "H_3B764981E731EA8D2F1B2B0C59_1", "识别色"),
)


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_one(hazards, canonical_id, duplicate_id, subject):
    canonical = hazards[canonical_id]
    duplicate = hazards[duplicate_id]
    if duplicate.get("lifecycle") == "active" and duplicate.get("mergedInto") == canonical_id:
        return {"canonical": canonical_id, "merged": duplicate_id, "alreadyMerged": True}
    if duplicate.get("lifecycle") != "proposed":
        raise RuntimeError(f"GB 12801 candidate {duplicate_id} is no longer proposed; inspect before rerunning")
    if subject not in str(canonical.get("title")) or subject not in str(duplicate.get("title")):
        raise RuntimeError(f"canonical and candidate do not describe the same {subject} subject")

    marker = (
        f"本批已与 {canonical_id} 合并：两条记录均描述同一{subject}隐患；"
        "正式依据沿用该实体已建立的 GB 12801-2025 条款衔接记录，"
        "但新版在 2026-10-01 前不提前作为现行依据。"
    )
    duplicate["lifecycle"] = "active"
    duplicate["mergedInto"] = canonical_id
    duplicate.pop("proposalStatus", None)
    duplicate.pop("sourceRow", None)
    duplicate["note"] = (str(duplicate.get("note") or "").rstrip() + "\n" + marker).strip()
    write(os.path.join(KNOW, "hazards", duplicate_id + ".json"), duplicate)

    canonical_review = read(os.path.join(KNOW, "reviews", "hazards", canonical_id + ".json"))
    write(os.path.join(KNOW, "reviews", "hazards", duplicate_id + ".json"), {
        "checkedAt": AS_OF,
        "decision": "verified",
        "entityId": duplicate_id,
        "entityType": "hazard",
        "evidenceRefs": canonical_review.get("evidenceRefs", []),
        "reason": f"与已核验的同一{subject}隐患为同一语义对象，已合并到 canonical 实体；正式条款关系保留在 canonical 实体上。",
        "reviewType": "deduplication",
        "reviewedContentHash": content_hash(duplicate),
        "reviewer": "Codex正式核验批次20260913",
    })
    return {"canonical": canonical_id, "merged": duplicate_id, "alreadyMerged": False}


def main():
    hazards = load_dir(KNOW, "hazards")
    results = [merge_one(hazards, *pair) for pair in PAIRS]

    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = read(manifest_path)
    batch_id = "excel-merge-gb12801-duplicate-20260913"
    if batch_id not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({
            "id": batch_id,
            "hazardsAdded": 0,
            "hazardsMerged": len(PAIRS),
            "clausesAdded": 0,
            "linksAdded": 0,
            "evidenceAdded": 0,
            "selection": "Merge the two same-subject GB 12801-2025 Excel candidates into existing reviewed hazards; preserve upcoming-version boundary.",
        })
    manifest.setdefault("counts", {})["hazards"] = len(load_dir(KNOW, "hazards"))
    manifest["counts"]["clauses"] = len(load_dir(KNOW, "clauses"))
    manifest["counts"]["links"] = len(load_dir(KNOW, "links"))
    write(manifest_path, manifest)
    write(os.path.join(PROPOSAL, "merge-gb12801-duplicate-report.json"), {
        "asOf": AS_OF,
        "pairs": results,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    })
    print(json.dumps({"pairs": results, "newEdition": "GB 12801-2025", "effectiveDate": "2026-10-01"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
