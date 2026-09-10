# -*- coding: utf-8 -*-
"""Phase 8/18: 为临时线类 hazard 补充口语 aliases，并重绑受影响 review。"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HAZ = os.path.join(ROOT, "knowledge", "hazards")
REV = os.path.join(ROOT, "knowledge", "reviews", "links")

ADD = {
    "H005": ["临时线"],
    "H_9C4FE3EBE8": ["临时线", "临时电源线"],
    "H_EA0194690E": ["临时线", "临时电线"],
    "H_F55588551E": ["临时线", "临时电源线"],
}

changed = set()
for f in glob.glob(os.path.join(HAZ, "*.json")):
    with io.open(f, encoding="utf-8") as fh:
        h = json.load(fh)
    hid = h["id"]
    match = hid if hid in ADD else next((k for k in ADD if hid.startswith(k)), None)
    if match:
        cur = set(h.get("aliases") or [])
        before = set(cur)
        cur.update(ADD[match])
        if cur != before:
            h["aliases"] = sorted(cur)
            with io.open(f, "w", encoding="utf-8") as fh:
                json.dump(h, fh, ensure_ascii=False, indent=1)
            changed.add(hid)
            print("aliases+", hid)

# rebind reviews whose hazard ctx hash changed
rebound = 0
for f in glob.glob(os.path.join(REV, "*.json")):
    with io.open(f, encoding="utf-8") as fh:
        r = json.load(fh)
    hid = (r.get("contextHashes") or {}).get("hazard")
    if not hid:
        continue
    # find hazard file by id
    hpath = os.path.join(HAZ, r.get("entityId") and r.get("contextHashes", {}).get("hazard") + ".json")
    # contextHashes.hazard stores the hash, not id; use review entity target:
    # reviews for links store hazardId in link entity; here we recompute hash of hazard by entityId of review
    continue

# simpler: recompute every review whose linked hazard id is in changed set
links = {}
for f in glob.glob(os.path.join(ROOT, "knowledge", "links", "*.json")):
    with io.open(f, encoding="utf-8") as fh:
        l = json.load(fh)
    links[l.get("entityId") or l.get("id")] = l

new_hashes = {}
for hid in changed:
    with io.open(os.path.join(HAZ, hid + ".json"), encoding="utf-8") as fh:
        new_hashes[hid] = content_hash(json.load(fh))

for f in glob.glob(os.path.join(REV, "*.json")):
    with io.open(f, encoding="utf-8") as fh:
        r = json.load(fh)
    rid = r.get("entityId") or r.get("id")
    l = links.get(rid) or {}
    hid = l.get("hazardId")
    if hid in new_hashes:
        ctx = dict(r.get("contextHashes") or {})
        ctx["hazard"] = new_hashes[hid]
        r["contextHashes"] = ctx
        r["checkedAt"] = "2026-09-10T17:00:00+08:00"
        reason = str(r.get("reason") or "")
        r["reason"] = (reason + "\n" if reason else "") + "【Phase8】hazard aliases 补充口语词，hazard ctx 重绑。"
        with io.open(f, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
        rebound += 1
        print("rebound", rid)
print("rebound reviews:", rebound)
