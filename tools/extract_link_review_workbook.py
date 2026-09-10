#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all link candidates + full context into a review workbook.

Reads knowledge/{links,hazards,clauses,law-versions,laws,evidence,reviews/links}
and produces tools/workbooks/link_review_workbook.json containing, per link:
link entity, current review sidecar, hazard, clause, lawVersion, law, evidence list.
Only links without a professional reviewer are included (decision=pending, no reviewer).
"""
import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")


def load_dir(sub):
    d = os.path.join(KNOW, sub)
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            obj = json.load(f)
        key = obj.get("id") or os.path.splitext(fn)[0]
        out[key] = obj
    return out


def main():
    links = load_dir("links")
    reviews = load_dir(os.path.join("reviews", "links"))
    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    law_versions = load_dir("law-versions")
    laws = load_dir("laws")
    evidence = load_dir("evidence")

    wb = []
    missing = {"hazard": [], "clause": [], "lawVersion": [], "law": [], "evidence": []}

    for kid in sorted(links.keys()):
        link = links[kid]
        rev = reviews.get(kid)
        # skip already professionally reviewed
        if rev and rev.get("reviewer"):
            continue
        if rev is None:
            # link without any review sidecar -> needs one
            pass
        hid = link.get("hazardId")
        cid = link.get("clauseId")
        h = hazards.get(hid)
        c = clauses.get(cid)
        lv = law_versions.get(c.get("lawVersionId")) if c else None
        lw = laws.get(lv.get("lawId")) if lv else None
        evs = []
        if rev and rev.get("evidenceRefs"):
            for eid in rev["evidenceRefs"]:
                e = evidence.get(eid)
                if e is None:
                    missing["evidence"].append((kid, eid))
                else:
                    evs.append(e)
        if h is None:
            missing["hazard"].append((kid, hid))
        if c is None:
            missing["clause"].append((kid, cid))
        if lv is None:
            missing["lawVersion"].append((kid, c.get("lawVersionId") if c else None))
        if lw is None:
            missing["law"].append((kid, lv.get("lawId") if lv else None))
        wb.append(OrderedDict([
            ("link", link),
            ("review", rev),
            ("hazard", h),
            ("clause", c),
            ("lawVersion", lv),
            ("law", lw),
            ("evidence", evs),
        ]))

    out = {
        "pendingCount": len(wb),
        "missing": missing,
        "items": wb,
    }
    outdir = os.path.join(ROOT, "tools", "workbooks")
    os.makedirs(outdir, exist_ok=True)
    outp = os.path.join(outdir, "link_review_workbook.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"pending links: {len(wb)}")
    print(f"missing refs: {json.dumps(missing, ensure_ascii=False)}")
    print(f"written: {outp}")


if __name__ == "__main__":
    sys.exit(main())
