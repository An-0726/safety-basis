# -*- coding: utf-8 -*-
"""Phase 16 final-acceptance inventory report.

Read-only against knowledge. Produces a concise machine/human-readable snapshot of
Requirement status and the shared release-gate inventory that still needs semantic
closure before READY_FOR_ACCEPTANCE.
"""
import glob
import io
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
DOC = os.path.join(ROOT, "docs", "V4_FINAL_ACCEPTANCE_INVENTORY.md")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402


def load_requirements():
    out = {}
    for f in glob.glob(os.path.join(KNOW, "requirements", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        out[d.get("id") or os.path.splitext(os.path.basename(f))[0]] = d
    return out


def main():
    gate = evaluate_release_gate(KNOW)
    requirements = load_requirements()
    hazards = load_dir(KNOW, "hazards")
    reviews = load_dir(KNOW, os.path.join("reviews", "links"))

    requirement_status = Counter(r.get("reviewStatus", "missing") for r in requirements.values())
    link_decisions = Counter(r.get("decision", "missing") for r in reviews.values())

    supporting_only = []
    for kid, v in sorted(gate.links.items()):
        if v.get("decision") == "verified" and v.get("ok") and v.get("role") == "supporting":
            supporting_only.append({
                "id": kid,
                "hazardId": v.get("hazardId"),
                "title": (hazards.get(v.get("hazardId")) or {}).get("title", ""),
            })

    active_without = []
    for hid, v in sorted(gate.hazards.items()):
        if v.get("active") and not v.get("merged") and v.get("content_ok") and hid not in gate.eligible_hazards:
            h = hazards.get(hid) or {}
            active_without.append({
                "id": hid,
                "category": h.get("category", ""),
                "title": h.get("title", ""),
            })

    excluded_superseded = []
    for hid, v in sorted(gate.hazards.items()):
        if not v.get("active") or v.get("merged"):
            h = hazards.get(hid) or {}
            excluded_superseded.append({
                "id": hid,
                "category": h.get("category", ""),
                "title": h.get("title", ""),
                "reason": "merged" if v.get("merged") else "superseded",
            })

    summary = {
        "counts": gate.counts,
        "eligibleHazards": len(gate.eligible_hazards),
        "eligibleLinks": len(gate.eligible_links),
        "requirementReviewStatus": dict(requirement_status),
        "linkReviewDecision": dict(link_decisions),
        "supportingVerifiedLinks": len(supporting_only),
        "activeHazardsWithoutQualifyingLink": len(active_without),
        "supersededOrMergedHazards": len(excluded_superseded),
    }

    lines = [
        "# V4 Phase 16 Final Acceptance Inventory",
        "",
        "> Generated from the current `knowledge/` tree by `tools/v4/final_acceptance_inventory.py`.",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Active hazards without qualifying direct/fallback link",
        "",
        "These remain outside the public release until individually adjudicated. They are not automatically errors, but Phase 16 must classify them before final acceptance.",
        "",
    ]
    for i, x in enumerate(active_without, 1):
        lines.append("%d. `%s` | %s | %s" % (i, x["id"], x["category"], x["title"]))

    lines.extend(["", "## Verified supporting links", ""])
    for i, x in enumerate(supporting_only, 1):
        lines.append("%d. `%s` -> `%s` | %s" % (i, x["id"], x["hazardId"], x["title"]))

    lines.extend(["", "## Superseded / merged hazards", ""])
    lines.append("Count: %d. These are retained for traceability and should remain excluded from the current public projection unless lifecycle review finds a data error." % len(excluded_superseded))

    with io.open(DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("report:", DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
