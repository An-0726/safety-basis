# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
KNOW = Path("knowledge")

for hid in ["H_5E36D9ABBA9321D566592E49_2", "H_66B2A0967E8B4E4BAD7749DF_1"]:
    links = [json.loads(p.read_text(encoding="utf-8")) for p in (KNOW / "links").glob("*.json")]
    h_links = [l for l in links if l.get("hazardId") == hid]
    print(hid, "links:", len(h_links))
    for l in h_links:
        cid = l.get("clauseId")
        c = json.loads((KNOW / "clauses" / f"{cid}.json").read_text(encoding="utf-8"))
        lvid = c["lawVersionId"]
        lv = json.loads((KNOW / "law-versions" / f"{lvid}.json").read_text(encoding="utf-8"))
        print(f"  {l['id']} (lifecycle={l.get('lifecycle')}) -> {cid} ({lv.get('documentNumber')} {c.get('articlePath')}) quote={c.get('quote')[:40]}")
