# -*- coding: utf-8 -*-
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")


def load(sub, fid):
    p = os.path.join(KNOW, sub, fid + ".json")
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    targets = ["K_A43B448D1E611C41A5212F686D", "K_04cdf5ee09cb1c9b9690bc5a", "K_cb3e687"]
    for t in targets:
        f = glob.glob(os.path.join(KNOW, "reviews", "links", "*" + t + "*.json"))
        if not f:
            print(t, "NOT FOUND")
            continue
        rid = os.path.splitext(os.path.basename(f[0]))[0]
        r = load(os.path.join("reviews", "links"), rid)
        print("=== review", rid, "===")
        for k in ("entityType", "entityId", "reviewType", "decision", "reasonCodes", "evidenceRefs", "clauseId", "hazardId"):
            if k in r:
                print(" ", k, ":", json.dumps(r[k], ensure_ascii=False)[:220])
        print("  keys:", sorted(r.keys()))
        # contextHashes
        if "contextHashes" in r:
            print("  contextHashes:", json.dumps(r["contextHashes"], ensure_ascii=False)[:160])
        # find the clause via link entity
        link = load("links", rid)
        cid = link.get("clauseId")
        if cid:
            c = load("clauses", cid)
            print("  link clause:", cid, "|", c.get("articlePath"), "|", c.get("quote", "")[:90])
        for e in (r.get("evidenceRefs") or [])[:3]:
            ef = os.path.join(KNOW, "evidence", e + ".json")
            if os.path.exists(ef):
                ev = json.load(io.open(ef, encoding="utf-8"))
                print("  EVIDENCE", e[:16], "| title:", str(ev.get("title"))[:70], "| source:", str(ev.get("source"))[:70])
            else:
                print("  EVIDENCE", e[:16], "MISSING FILE")
        print()


if __name__ == "__main__":
    main()
