#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate hash binding across knowledge entities and their review sidecars.

Checks for every link review:
- link entity hash == review.reviewedContentHash
- hazard entity hash == review.contextHashes.hazard
- clause entity hash == review.contextHashes.clause
Reports mismatches grouped by kind. Used to detect stale/mis-bound reviews
before writing new ones.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v4"))
from canonical import content_hash  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")


def load_dir(sub, by_entity_id=False):
    d = os.path.join(KNOW, sub)
    out = {}
    for fn in os.listdir(d):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            obj = json.load(f)
        # review 文件名可能是 review 自身 id（RV_*）而非被审实体 id，
        # 必须按 entityId 索引，否则这些 review 会被静默跳过。
        key = (obj.get("entityId") or os.path.splitext(fn)[0]) if by_entity_id else os.path.splitext(fn)[0]
        out[key] = obj
    return out


def main():
    links = load_dir("links")
    hazards = load_dir("hazards")
    clauses = load_dir("clauses")
    reviews = load_dir(os.path.join("reviews", "links"), by_entity_id=True)

    stale_link, stale_hazard, stale_clause, unbound = [], [], [], []
    for kid, rev in sorted(reviews.items()):
        link = links.get(kid)
        if link is None:
            print(f"MISSING LINK ENTITY for review {kid}")
            continue
        h = rev.get("contextHashes") or {}
        if not rev.get("reviewedContentHash"):
            unbound.append((kid, "reviewedContentHash"))
        if link.get("id") != kid:
            print(f"LINK ID MISMATCH review={kid} entity={link.get('id')}")
        try:
            lh = content_hash(link)
        except Exception as e:
            print(f"HASH ERROR {kid}: {e}")
            continue
        if rev.get("reviewedContentHash") != lh:
            stale_link.append((kid, rev.get("reviewedContentHash"), lh))
        hid = link.get("hazardId")
        cid = link.get("clauseId")
        if hid and hid in hazards:
            hh = content_hash(hazards[hid])
            if h.get("hazard") != hh:
                stale_hazard.append((kid, h.get("hazard"), hh))
        else:
            print(f"MISSING HAZARD {hid} for link {kid}")
        if cid and cid in clauses:
            ch = content_hash(clauses[cid])
            if h.get("clause") != ch:
                stale_clause.append((kid, h.get("clause"), ch))
        else:
            print(f"MISSING CLAUSE {cid} for link {kid}")

    print(f"reviews total: {len(reviews)}")
    print(f"unbound (no reviewedContentHash): {len(unbound)} {unbound[:10]}")
    print(f"stale link hash: {len(stale_link)}")
    for x in stale_link[:20]:
        print("   ", x[0], "rev=", x[1][:16], "now=", x[2][:16])
    print(f"stale hazard ctx: {len(stale_hazard)}")
    for x in stale_hazard[:20]:
        print("   ", x[0], "rev=", x[1][:16], "now=", x[2][:16])
    print(f"stale clause ctx: {len(stale_clause)}")
    for x in stale_clause[:20]:
        print("   ", x[0], "rev=", x[1][:16], "now=", x[2][:16])
    bad = len(stale_link) + len(stale_hazard) + len(stale_clause) + len(unbound)
    if bad:
        print(f"BINDING FAILURES: {bad}（可使用 tools/v4/rebind.py --fix 批量刷新）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
