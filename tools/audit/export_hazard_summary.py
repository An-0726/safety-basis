#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]; K=ROOT/"knowledge"
def rd(p): return json.loads(p.read_text(encoding="utf-8"))
haz=[]; clauses={}; lvs={}; links=[]; reviews={}
for p in (K/"clauses").glob("*.json"): 
    o=rd(p); clauses[o["id"]]=o
for p in (K/"law-versions").glob("*.json"):
    o=rd(p); lvs[o["id"]]=o
for p in (K/"links").glob("*.json"): links.append(rd(p))
for p in (K/"reviews"/"links").glob("*.json"):
    o=rd(p); reviews[o.get("entityId") or p.stem]=o
byh=defaultdict(list)
for l in links: byh[l.get("hazardId")].append(l)
for p in sorted((K/"hazards").glob("*.json")):
    h=rd(p)
    basis=[]
    for l in byh.get(h["id"],[]):
        if l.get("lifecycle")!="active": continue
        c=clauses.get(l.get("clauseId"),{}); lv=lvs.get(c.get("lawVersionId"),{})
        basis.append({
          "linkId":l.get("id"),"role":l.get("role"),"review":reviews.get(l.get("id"),{}).get("decision"),
          "clauseId":c.get("id"),"articlePath":c.get("articlePath"),"quote":c.get("quote"),
          "lawVersionId":lv.get("id"),"documentNumber":lv.get("documentNumber"),"validityStatus":lv.get("validityStatus")
        })
    haz.append({k:h.get(k) for k in ("id","title","description","measures","conditions","category","places","aliases","keywords","lifecycle","mode","mergedInto")} | {"basis":basis})
Path("/tmp/hazard-summary.json").write_text(json.dumps({"hazards":haz},ensure_ascii=False)+"\n",encoding="utf-8")
print({"hazards":len(haz)})
