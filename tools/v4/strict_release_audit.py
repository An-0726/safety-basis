# -*- coding: utf-8 -*-
"""Strict V4 release audit aligned with docs/GATE_V4.md.

Read-only: it never mutates knowledge or release files.
It reports entity-review coverage, current-version semantics, eligible links,
eligible hazards, and final blockers/warnings for candidate production review.
"""
import glob
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
AS_OF = date(2026, 9, 10)
ALLOWED_VALIDITY = {"active", "upcoming", "repealed", "unknown"}
QUALIFYING_ROLES = {"direct", "fallback"}


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("id") or d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def parse_date(v):
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except Exception:
        return None


def review_ok(entity, review, need_evidence=False):
    reasons = []
    if not review:
        return False, ["review_missing"]
    if review.get("decision") != "verified":
        reasons.append("review_not_verified:" + str(review.get("decision")))
    if review.get("reviewedContentHash") != content_hash(entity):
        reasons.append("review_hash_stale")
    if need_evidence and not review.get("evidenceRefs"):
        reasons.append("authoritative_evidence_missing")
    return not reasons, reasons


def main():
    laws = load_dir("laws")
    lvs = load_dir("law-versions")
    clauses = load_dir("clauses")
    hazards = load_dir("hazards")
    links = load_dir("links")
    reviews = {
        "laws": load_dir(os.path.join("reviews", "laws")),
        "law-versions": load_dir(os.path.join("reviews", "law-versions")),
        "clauses": load_dir(os.path.join("reviews", "clauses")),
        "hazards": load_dir(os.path.join("reviews", "hazards")),
        "links": load_dir(os.path.join("reviews", "links")),
    }

    summary = {
        "asOf": AS_OF.isoformat(),
        "entityCounts": {
            "laws": len(laws), "lawVersions": len(lvs), "clauses": len(clauses),
            "hazards": len(hazards), "links": len(links),
        },
        "reviewCounts": {k: len(v) for k, v in reviews.items()},
        "reviewDecisionCounts": {
            k: dict(Counter((x.get("decision") or "") for x in v.values()))
            for k, v in reviews.items()
        },
    }
    blockers = []
    warnings = []

    law_ok = {}
    for lid, law in laws.items():
        ok, why = review_ok(law, reviews["laws"].get(lid), True)
        law_ok[lid] = ok
        if not ok:
            blockers.append({"type": "law", "id": lid, "reasons": why})

    lv_ok = {}
    for vid, lv in lvs.items():
        why = []
        _, rwhy = review_ok(lv, reviews["law-versions"].get(vid), True)
        why += rwhy
        status = lv.get("validityStatus") or "unknown"
        eff = parse_date(lv.get("effectiveDate"))
        end = parse_date(lv.get("endDate"))
        if status not in ALLOWED_VALIDITY:
            why.append("invalid_validityStatus:" + str(status))
        if not eff:
            why.append("effectiveDate_invalid_or_missing")
        if status == "active" and eff and eff > AS_OF:
            why.append("active_before_effectiveDate")
        if status == "active" and end and not (AS_OF < end):
            why.append("active_past_endDate")
        if status == "upcoming" and eff and not (eff > AS_OF):
            why.append("upcoming_not_future")
        if lv.get("lawId") not in laws:
            why.append("law_missing")
        elif not law_ok.get(lv.get("lawId"), False):
            why.append("law_gate_failed")
        lv_ok[vid] = not why
        if why:
            blockers.append({"type": "lawVersion", "id": vid, "reasons": why})

    clause_ok = {}
    for cid, cl in clauses.items():
        why = []
        _, rwhy = review_ok(cl, reviews["clauses"].get(cid), True)
        why += rwhy
        vid = cl.get("lawVersionId")
        if vid not in lvs:
            why.append("lawVersion_missing")
        elif not lv_ok.get(vid, False):
            why.append("lawVersion_gate_failed")
        if not cl.get("articlePath"):
            why.append("articlePath_missing")
        if not cl.get("quote"):
            why.append("quote_missing")
        clause_ok[cid] = not why
        if why:
            blockers.append({"type": "clause", "id": cid, "reasons": why})

    hazard_content_ok = {}
    for hid, hz in hazards.items():
        why = []
        _, rwhy = review_ok(hz, reviews["hazards"].get(hid), False)
        why += rwhy
        for field in ("title", "description", "measures", "category"):
            if not hz.get(field):
                why.append(field + "_missing")
        if (hz.get("lifecycle") or "active") != "active":
            why.append("hazard_not_active")
        if hz.get("mergedInto"):
            why.append("hazard_merged")
        public_text = " ".join(str(hz.get(x) or "") for x in ("title", "description", "measures"))
        if re.search(r"[A-Za-z]:\\|/(?:home|Users|mnt)/", public_text):
            why.append("possible_private_path")
        hazard_content_ok[hid] = not why
        if why:
            blockers.append({"type": "hazard_content", "id": hid, "reasons": why})

    eligible_links = {}
    hazard_links = defaultdict(list)
    link_failures = {}
    for kid, lk in links.items():
        hid, cid = lk.get("hazardId"), lk.get("clauseId")
        hazard_links[hid].append(kid)
        why = []
        _, rwhy = review_ok(lk, reviews["links"].get(kid), False)
        why += rwhy
        rv = reviews["links"].get(kid) or {}
        if rv.get("decision") == "verified":
            if not rv.get("reason"):
                why.append("reason_missing")
            ctx = rv.get("contextHashes") or {}
            if hid in hazards and ctx.get("hazard") != content_hash(hazards[hid]):
                why.append("hazard_context_stale")
            if cid in clauses and ctx.get("clause") != content_hash(clauses[cid]):
                why.append("clause_context_stale")
        if lk.get("role") not in {"direct", "supporting", "fallback"}:
            why.append("invalid_role")
        if (lk.get("lifecycle") or "active") != "active":
            why.append("link_not_active")
        if cid not in clauses:
            why.append("clause_missing")
        elif not clause_ok.get(cid, False):
            why.append("clause_gate_failed")
        if hid not in hazards:
            why.append("hazard_missing")
        eligible_links[kid] = not why
        if why:
            link_failures[kid] = why

    eligible_hazards = {}
    hazard_reasons = {}
    for hid in hazards:
        why = []
        if not hazard_content_ok.get(hid, False):
            why.append("hazard_content_gate_failed")
        qualifying = [
            kid for kid in hazard_links.get(hid, [])
            if eligible_links.get(kid) and links[kid].get("role") in QUALIFYING_ROLES
        ]
        if not qualifying:
            why.append("no_qualifying_verified_link")
        eligible_hazards[hid] = not why
        if why:
            hazard_reasons[hid] = why

    backfill_ids = [
        "H001","H003","H004","H006","H007","H008","H009","H010","H011","H012",
        "H014","H020","H023","H026","H027","H028","H029","H030","H031","H032",
    ]
    pending_link_ids = sorted(
        kid for kid, rv in reviews["links"].items() if rv.get("decision") == "pending"
    )
    pending_hazards = sorted({links[k].get("hazardId") for k in pending_link_ids if k in links})

    summary.update({
        "eligibleLinks": sum(eligible_links.values()),
        "ineligibleLinks": len(links) - sum(eligible_links.values()),
        "eligibleHazards": sum(eligible_hazards.values()),
        "blockedHazards": len(hazards) - sum(eligible_hazards.values()),
        "pendingLinks": len(pending_link_ids),
        "pendingLinkIds": pending_link_ids,
        "pendingHazards": len(pending_hazards),
        "backfill": {
            "ids": backfill_ids,
            "withAnyLink": [h for h in backfill_ids if hazard_links.get(h)],
            "eligible": [h for h in backfill_ids if eligible_hazards.get(h)],
            "blocked": [h for h in backfill_ids if not eligible_hazards.get(h)],
        },
        "blockedHazardIds": sorted(h for h, ok in eligible_hazards.items() if not ok),
        "linkFailureSample": dict(list(sorted(link_failures.items()))[:50]),
    })

    for kid in pending_link_ids:
        hid = links.get(kid, {}).get("hazardId")
        if eligible_hazards.get(hid):
            warnings.append({"type": "pending_link_excluded", "id": kid, "hazardId": hid})
        else:
            blockers.append({"type": "pending_link_on_blocked_hazard", "id": kid, "hazardId": hid})

    summary["strictVerdict"] = "PASS" if not blockers else "BLOCK"
    summary["blockerCount"] = len(blockers)
    summary["warningCount"] = len(warnings)
    summary["blockers"] = blockers[:300]
    summary["warnings"] = warnings[:300]

    print("=== STRICT_V4_RELEASE_AUDIT ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
