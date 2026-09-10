# -*- coding: utf-8 -*-
"""定位 evidence 错配的 review 与 link。"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")


def main():
    evidence = {}
    for f in glob.glob(os.path.join(KNOW, "evidence", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        evidence[d["id"]] = d

    fire_url = "ff8081817ab22e0c017abd"          # 消防法详情页
    mee_url = "mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw"  # 危废标准 PDF
    bad_evidence = set()
    for eid, ev in evidence.items():
        u = str(ev.get("url", ""))
        if fire_url in u or mee_url in u:
            bad_evidence.add(eid)

    print("suspicious evidence ids:", len(bad_evidence))
    for f in glob.glob(os.path.join(KNOW, "reviews", "links", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        refs = r.get("evidenceRefs") or []
        hit = [e for e in refs if e in bad_evidence]
        if hit:
            kid = r.get("entityId") or os.path.splitext(os.path.basename(f))[0]
            link_f = os.path.join(KNOW, "links", kid + ".json")
            cid = ""
            if os.path.exists(link_f):
                with io.open(link_f, encoding="utf-8") as fh:
                    cid = json.load(fh).get("clauseId", "")
            print(" review:", kid, "| clause:", cid, "| ev:", hit)
            for e in hit:
                ev = evidence.get(e, {})
                print("    ev url:", str(ev.get("url"))[:100], "| locator:", ev.get("locator"))


if __name__ == "__main__":
    main()
