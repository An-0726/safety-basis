#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print a readable digest of pending link reviews, batch by batch.

Usage: python tools/workbooks/digest_pending.py <start_idx> <end_idx>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WB = os.path.join(HERE, "link_review_workbook.json")

with open(WB, encoding="utf-8") as f:
    data = json.load(f)

items = data["items"]
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end = int(sys.argv[2]) if len(sys.argv) > 2 else len(items)

for i in range(start, min(end, len(items))):
    it = items[i]
    link = it["link"]
    h = it["hazard"] or {}
    c = it["clause"] or {}
    lv = it["lawVersion"] or {}
    lw = it["law"] or {}
    rev = it["review"] or {}
    print("=" * 100)
    print(f"[{i}] LINK {link.get('id')}  role={link.get('role')} legacy={link.get('legacyRole')} juris={link.get('jurisdictionCode')}")
    print(f"  applicability: {link.get('applicability')}")
    print(f"  hazardId={link.get('hazardId')}  clauseId={link.get('clauseId')}")
    print(f"  HAZARD {h.get('id')}: {h.get('title')}")
    print(f"    category={h.get('category')} places={h.get('places')} conditions={h.get('conditions')}")
    print(f"    note={h.get('note')!r} measures={h.get('measures')!r}")
    print(f"    keywords={h.get('keywords')} aliases={h.get('aliases')}")
    print(f"  CLAUSE {c.get('id')} [{lv.get('officialName')} {lv.get('documentNumber')} {lv.get('validityStatus')} eff={lv.get('effectiveDate')}]")
    print(f"    {c.get('articlePath')}: {c.get('quote')}")
    print(f"    lawVersionId={c.get('lawVersionId')} sourceUrl={c.get('sourceUrl')}")
    print(f"  LAW {lw.get('id')}: {lw.get('canonicalName')} kind={lw.get('documentKind')} juris={lw.get('jurisdictionCode')}")
    if rev:
        print(f"  REVIEW: decision={rev.get('decision')} codes={rev.get('reasonCodes')}")
        v3 = rev.get("migratedFromV3Verification") or {}
        print(f"    v3Result={v3.get('v3Result')} v3Reason={v3.get('v3Reason')}")
        for e in it["evidence"]:
            print(f"    EVID {e.get('id')} tier={e.get('tier')} url={e.get('url')} locator={e.get('locator')}")
