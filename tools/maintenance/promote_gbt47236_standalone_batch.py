# -*- coding: utf-8 -*-
"""Promote GB/T 47236 candidates supported by self-contained clause duties.

Cross-standard compliance claims, table-only requirements, recommended wording,
and partial duplicates are intentionally outside this batch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate  # noqa: E402


AS_OF = "2026-09-18"
REVIEWER = "Codex PHASE11 GB/T 47236 standalone review 20260918"
EVIDENCE_ID = "E_GBT47236_2026"
SCOPE = (
    "仅适用于GB/T 47236-2026范围内的低压铸造机、差压铸造机及其他金属型铸造设备；"
    "其他机械应按相应通用或专用标准判断。"
)

# These clauses contain the operative duty needed to establish the candidate.
# Candidates that require a referenced standard/table to establish the actual
# defect are deliberately omitted.
PROMOTE = {
    "H_GBT47236_4_2_1_5_1": "C_GBT47236_4_2_1_5",
    "H_GBT47236_4_2_10_1_1": "C_GBT47236_4_2_10_1",
    "H_GBT47236_4_2_11_1_1": "C_GBT47236_4_2_11_1",
    "H_GBT47236_4_2_2_1": "C_GBT47236_4_2_2_1",
    "H_GBT47236_4_2_3_1_4": "C_GBT47236_4_2_3_1_4",
    "H_GBT47236_4_2_3_1_5_1": "C_GBT47236_4_2_3_1_5",
    "H_GBT47236_4_2_3_2_2_1": "C_GBT47236_4_2_3_2_2",
    "H_GBT47236_4_2_4_3": "C_GBT47236_4_2_4_3",
    "H_GBT47236_4_2_4_4_1": "C_GBT47236_4_2_4_4",
    "H_GBT47236_4_2_4_5": "C_GBT47236_4_2_4_5",
    "H_GBT47236_4_2_5_1_1": "C_GBT47236_4_2_5_1",
    "H_GBT47236_4_2_5_2_1": "C_GBT47236_4_2_5_2",
    "H_GBT47236_4_2_5_3_1": "C_GBT47236_4_2_5_3",
    "H_GBT47236_4_2_5_5_1": "C_GBT47236_4_2_5_5",
    "H_GBT47236_4_2_5_6_1": "C_GBT47236_4_2_5_6",
    "H_GBT47236_4_2_6_3_1": "C_GBT47236_4_2_6_3",
    "H_GBT47236_4_2_6_6_1": "C_GBT47236_4_2_6_6",
    "H_GBT47236_4_2_6_7_1": "C_GBT47236_4_2_6_7",
    "H_GBT47236_4_2_8_3_1": "C_GBT47236_4_2_8_3",
    "H_GBT47236_4_2_9_1_1": "C_GBT47236_4_2_9_1",
    "H_GBT47236_4_2_9_3_1": "C_GBT47236_4_2_9_3",
    "H_GBT47236_5_1_1_2": "C_GBT47236_5_1_1",
    "H_GBT47236_6_1_2_1": "C_GBT47236_6_1_2",
    "H_GBT47236_6_2_2_1": "C_GBT47236_6_2_2",
    "H_GBT47236_6_2_3_1": "C_GBT47236_6_2_3",
    "H_GBT47236_6_3_3_1": "C_GBT47236_6_3_3",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_dir(relative: str) -> dict[str, dict]:
    result = {}
    for path in (KNOW / relative).glob("*.json"):
        value = read_json(path)
        result[value.get("id") or value.get("entityId") or path.stem] = value
    return result


def clause_reason(clause: dict) -> str:
    return f"{clause['articlePath']}在本条内直接规定候选所述义务，候选为该义务的反向缺陷表述。"


def validate_baseline(hazards: dict, clauses: dict, links: dict, clause_reviews: dict) -> None:
    counts = Counter(h.get("lifecycle") for h in hazards.values())
    expected = Counter({"active": 1458, "proposed": 471, "superseded": 86})
    if counts != expected:
        raise RuntimeError(f"lifecycle baseline drift: {dict(counts)}")
    for hazard_id, clause_id in PROMOTE.items():
        hazard = hazards.get(hazard_id, {})
        clause = clauses.get(clause_id, {})
        review = clause_reviews.get(clause_id, {})
        if hazard.get("lifecycle") != "proposed" or hazard.get("mergedInto"):
            raise RuntimeError(f"candidate is not independently proposed: {hazard_id}")
        if clause.get("lifecycle") != "active" or clause.get("lawVersionId") != "LV_STD_GBT47236_2026":
            raise RuntimeError(f"target is not an active GB/T 47236 clause: {clause_id}")
        if review.get("decision") != "verified" or review.get("reviewedContentHash") != content_hash(clause):
            raise RuntimeError(f"clause review is stale: {clause_id}")
        if EVIDENCE_ID not in (review.get("evidenceRefs") or []):
            raise RuntimeError(f"clause lacks official evidence: {clause_id}")
        existing = [
            link["id"]
            for link in links.values()
            if link.get("clauseId") == clause_id
            and link.get("lifecycle") == "active"
            and hazards.get(link.get("hazardId"), {}).get("lifecycle") == "active"
            and not hazards.get(link.get("hazardId"), {}).get("mergedInto")
        ]
        if existing:
            raise RuntimeError(f"target clause already supports active hazard: {clause_id} {existing}")


def promote_one(hazard: dict, clause: dict) -> dict:
    hazard = dict(hazard)
    hazard["conditions"] = SCOPE
    hazard["lifecycle"] = "active"
    hazard["mode"] = "direct"
    hazard.pop("proposalStatus", None)
    hazard.pop("sourceRow", None)
    hazard.pop("revisionState", None)
    marker = (
        "【PHASE 11 2026-09-18 standalone批次】已复核GB/T 47236-2026官方逐字条款；"
        "本条自身直接规定所述义务，适用范围已限定至该标准覆盖设备。"
    )
    note = str(hazard.get("note") or "").rstrip()
    if marker not in note:
        hazard["note"] = (note + "\n" + marker).strip()
    reason = clause_reason(clause)
    hazard_review = {
        "checkedAt": AS_OF,
        "decision": "verified",
        "entityId": hazard["id"],
        "entityType": "hazard",
        "evidenceRefs": [EVIDENCE_ID],
        "reason": reason + "已限定设备对象，未用外部标准或表格的未核内容补足本条义务。",
        "reviewType": "content",
        "reviewedContentHash": content_hash(hazard),
        "reviewer": REVIEWER,
    }
    link_id = "K_PHASE11_GBT47236_S_" + hashlib.sha1(
        (hazard["id"] + "|" + clause["id"]).encode("utf-8")
    ).hexdigest()[:18].upper()
    link = {
        "id": link_id,
        "hazardId": hazard["id"],
        "clauseId": clause["id"],
        "role": "direct",
        "legacyRole": "直接依据",
        "applicability": SCOPE,
        "jurisdictionCode": "CN",
        "lifecycle": "active",
        "priority": 10,
        "requirementId": "",
        "reason": reason,
    }
    link_review = {
        "checkedAt": AS_OF,
        "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hazard)},
        "decision": "verified",
        "entityId": link_id,
        "entityType": "link",
        "evidenceRefs": [EVIDENCE_ID],
        "reason": reason + "适用范围已限定为GB/T 47236-2026覆盖设备。",
        "reviewType": "applicability",
        "reviewedContentHash": content_hash(link),
        "reviewer": REVIEWER,
    }
    write_json(KNOW / "hazards" / f"{hazard['id']}.json", hazard)
    write_json(KNOW / "reviews" / "hazards" / f"{hazard['id']}.json", hazard_review)
    write_json(KNOW / "links" / f"{link_id}.json", link)
    write_json(KNOW / "reviews" / "links" / f"{link_id}.json", link_review)
    return {
        "hazardId": hazard["id"],
        "title": hazard.get("title"),
        "clauseId": clause["id"],
        "linkId": link_id,
        "reason": reason,
    }


def update_manifest() -> None:
    path = KNOW / "manifest.json"
    manifest = read_json(path)
    batch_id = "phase11-promote-gbt47236-standalone-batch-20260918"
    batches = [item for item in manifest.get("batches", []) if item.get("id") != batch_id]
    batches.append(
        {
            "id": batch_id,
            "hazardsPromoted": len(PROMOTE),
            "linksAdded": len(PROMOTE),
            "candidatesReviewed": len(PROMOTE),
            "selection": (
                "Promote GB/T 47236-2026 candidates supported by self-contained operative duties; "
                "exclude cross-standard, table-only, recommended-wording, and partial-duplicate cases."
            ),
        }
    )
    manifest["batches"] = batches
    manifest["counts"]["links"] = len(list((KNOW / "links").glob("*.json")))
    manifest["asOf"] = AS_OF
    write_json(path, manifest)


def write_reports(promoted: list[dict]) -> None:
    rows = [
        {
            "recordType": "metadata",
            "schemaVersion": 1,
            "asOf": AS_OF,
            "baselineProposed": 471,
            "reviewed": len(PROMOTE),
            "promoted": len(PROMOTE),
            "proposedAfter": 445,
            "selection": "self_contained_clause_duty",
            "privateSqliteModified": False,
        }
    ]
    rows.extend(
        {
            **item,
            "outcome": "promoted_active",
            "lifecycleAfter": "active",
            "reasonCode": "verified_self_contained_direct",
        }
        for item in promoted
    )
    path = DOCS / "phase11-gbt47236-standalone-disposition.jsonl"
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# PHASE 11 GB/T 47236 独立义务候选批次",
        "",
        f"> 基准日：{AS_OF}。本批只采用本条自身足以成立的直接义务。",
        "",
        "## 结论",
        "",
        f"- 复核并转正：{len(promoted)} 条。",
        "- 明确排除：需读取被引用标准才能确认的合规项、表1至表5项目、推荐性措辞和部分重叠项。",
        "- 本批后 knowledge lifecycle：1,484 active / 445 proposed / 86 superseded。",
        "- 未修改私有 SQLite、archive、稳定 ID 或官方原文快照。",
        "",
        "## 转正清单",
        "",
        "| hazardId | clauseId | 核验结论 |",
        "| --- | --- | --- |",
    ]
    for item in promoted:
        lines.append(f"| `{item['hazardId']}` | `{item['clauseId']}` | {item['reason']} |")
    lines += ["", "机器明细见 `docs/phase11-gbt47236-standalone-disposition.jsonl`。", ""]
    (DOCS / "PHASE11_GBT47236_STANDALONE_BATCH.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    links = load_dir("links")
    clause_reviews = load_dir("reviews/clauses")
    validate_baseline(hazards, clauses, links, clause_reviews)
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "baselineProposed": 471,
        "reviewed": len(PROMOTE),
        "promotable": len(PROMOTE),
        "proposedAfter": 445,
    }
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    promoted = [promote_one(hazards[hid], clauses[cid]) for hid, cid in sorted(PROMOTE.items())]
    update_manifest()
    write_reports(promoted)
    gate = evaluate_release_gate(KNOW)
    missing = sorted(set(PROMOTE) - set(gate.eligible_hazards))
    if missing:
        raise RuntimeError(f"promoted hazards failed release Gate: {missing}")
    final = Counter(h.get("lifecycle") for h in load_dir("hazards").values())
    expected = Counter({"active": 1484, "proposed": 445, "superseded": 86})
    if final != expected:
        raise RuntimeError(f"unexpected final lifecycle counts: {dict(final)}")
    summary["allPromotedGateEligible"] = True
    summary["finalLifecycle"] = dict(final)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
