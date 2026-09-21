#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json,re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
K=ROOT/"knowledge"

def rd(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\s，。；：、,.!！?？（）()“”‘’'\"《》【】\[\]—–_-]+","",s)
    return s
def grams(s,n=2):
    s=norm(s)
    return {s[i:i+n] for i in range(max(0,len(s)-n+1))} or ({s} if s else set())
def jac(a,b): return len(a&b)/len(a|b) if a and b else 0.0
def load(sub):
    out={}
    for p in (K/sub).glob("*.json"):
        o=rd(p); oid=o.get("id") or o.get("entityId")
        if oid: out[oid]=o
    return out

haz=load("hazards"); clauses=load("clauses"); links=load("links"); lvs=load("law-versions"); laws=load("laws"); rlinks=load("reviews/links")
links_by_clause=defaultdict(list)
for l in links.values():
    links_by_clause[l.get("clauseId")].append(l)

targets=[h for h in haz.values() if h.get("id","").startswith("H_COM_") and h.get("lifecycle")=="proposed"]
rows=[]
for h in sorted(targets,key=lambda x:x["id"]):
    htext=" ".join([h.get("title",""),h.get("description","")," ".join(h.get("keywords") or [])," ".join(h.get("aliases") or [])])
    scored=[]
    for c in clauses.values():
        if c.get("lifecycle")!="active": continue
        q=c.get("quote") or ""
        if not q: continue
        lv=lvs.get(c.get("lawVersionId"),{})
        status=lv.get("validityStatus")
        if status not in (None,"active","current","现行有效","现行使用中"):
            continue
        ctext=" ".join([c.get("articlePath",""),q])
        base=0.62*jac(grams(htext),grams(ctext))+0.38*SequenceMatcher(None,norm(h.get("title")),norm(q[:100])).ratio()
        related=[]
        for l in links_by_clause.get(c["id"],[]):
            if l.get("lifecycle")!="active": continue
            rv=rlinks.get(l["id"],{})
            if rv.get("decision")!="verified": continue
            hh=haz.get(l.get("hazardId"),{})
            if not hh or hh.get("lifecycle")!="active": continue
            hs=0.55*jac(grams(htext),grams((hh.get("title") or "")+" "+(hh.get("description") or "")))+0.45*SequenceMatcher(None,norm(h.get("title")),norm(hh.get("title"))).ratio()
            if hs>0.12:
                related.append({"hazardId":hh.get("id"),"title":hh.get("title"),"role":l.get("role"),"score":round(hs,4)})
                base=max(base,0.55*base+0.45*hs)
        if base<0.12 and not related: continue
        law=laws.get(lv.get("lawId"),{})
        scored.append((base,{
          "clauseId":c["id"],"articlePath":c.get("articlePath"),"quote":q,
          "lawVersionId":lv.get("id"),"documentNumber":lv.get("documentNumber"),
          "lawName":law.get("canonicalName"),"validityStatus":status,
          "score":round(base,4),"relatedHazards":sorted(related,key=lambda x:x["score"],reverse=True)[:5]
        }))
    scored.sort(key=lambda x:x[0],reverse=True)
    rows.append({"hazardId":h["id"],"title":h.get("title"),"description":h.get("description"),"conditions":h.get("conditions"),"category":h.get("category"),"topClauses":[x[1] for x in scored[:12]]})
out={"count":len(rows),"rows":rows}
Path("/tmp/commerce47-clause-match.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"count":len(rows)},ensure_ascii=False))
for r in rows:
    t=r["topClauses"][:3]
    print(json.dumps({"hazardId":r["hazardId"],"title":r["title"],"top":[{"clauseId":x["clauseId"],"law":x["lawName"],"article":x["articlePath"],"score":x["score"],"related":x["relatedHazards"][:2]} for x in t]},ensure_ascii=False))
