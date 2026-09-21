#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
K=ROOT/"knowledge"

def rd(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\s，。；：、,.!！?？（）()“”‘’'\"《》【】\[\]—–_-]+","",s)
    for w in ("现场","一处","部分","相关","存在","未见","及时","立即"):
        s=s.replace(w,"")
    return s
def grams(s,n=2):
    s=norm(s)
    if len(s)<n: return {s} if s else set()
    return {s[i:i+n] for i in range(len(s)-n+1)}
def jac(a,b):
    if not a or not b: return 0.0
    return len(a&b)/len(a|b)
def sim(c,h):
    ct, ht=norm(c["hazard"]), norm(h.get("title"))
    cd, hd=norm(c["hazard"]), norm(h.get("description"))
    title=SequenceMatcher(None,ct,ht).ratio() if ct and ht else 0
    desc=SequenceMatcher(None,cd,hd).ratio() if cd and hd else 0
    gj=jac(grams(c["hazard"]), grams((h.get("title") or "")+" "+(h.get("description") or "")))
    kw=jac(grams(c["hazard"],1), grams(" ".join(h.get("keywords") or []),1))
    return 0.50*title+0.22*desc+0.23*gj+0.05*kw

def load_dir(name):
    out={}
    for p in (K/name).glob("*.json"):
        o=rd(p); oid=o.get("id") or o.get("entityId")
        if oid: out[oid]=o
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidates",default=str(ROOT/"tools/audit/commerce_full_candidates_20260921.json"))
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    cand=rd(args.candidates)["items"]
    hazards=load_dir("hazards")
    links=load_dir("links")
    clauses=load_dir("clauses")
    lvs=load_dir("law-versions")
    reviews=load_dir("reviews/links")
    links_by_h=defaultdict(list)
    for l in links.values(): links_by_h[l.get("hazardId")].append(l)

    rows=[]
    for c in cand:
        scored=[]
        for h in hazards.values():
            if h.get("lifecycle")=="superseded":
                continue
            s=sim(c,h)
            if s<0.10: continue
            scored.append((s,h))
        scored.sort(key=lambda x:x[0],reverse=True)
        tops=[]
        for s,h in scored[:8]:
            basis=[]
            for l in sorted(links_by_h.get(h["id"],[]), key=lambda x:(x.get("priority",99),x.get("id",""))):
                if l.get("lifecycle")!="active": continue
                cid=l.get("clauseId"); cl=clauses.get(cid,{})
                lv=lvs.get(cl.get("lawVersionId"),{})
                rv=reviews.get(l.get("id"),{})
                basis.append({
                    "linkId":l.get("id"),"role":l.get("role"),"review":rv.get("decision"),
                    "clauseId":cid,"articlePath":cl.get("articlePath"),"lawVersionId":lv.get("id"),
                    "documentNumber":lv.get("documentNumber"),"validityStatus":lv.get("validityStatus"),
                })
            tops.append({
                "score":round(s,4),"id":h["id"],"title":h.get("title"),"description":h.get("description"),
                "lifecycle":h.get("lifecycle"),"mode":h.get("mode"),"category":h.get("category"),
                "basis":basis[:5]
            })
        exact=[x for x in tops if norm(x["title"])==norm(c["hazard"])]
        best=tops[0] if tops else None
        confidence="low"
        if exact: confidence="exact"
        elif best and best["score"]>=0.62: confidence="high"
        elif best and best["score"]>=0.42: confidence="medium"
        rows.append({**c,"matchConfidence":confidence,"topMatches":tops})

    # Candidate-to-candidate near duplicate groups (union-find at conservative threshold).
    parent={c["candidateId"]:c["candidateId"] for c in cand}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    for i,a in enumerate(cand):
        for b in cand[i+1:]:
            sa=norm(a["hazard"]); sb=norm(b["hazard"])
            score=0.65*SequenceMatcher(None,sa,sb).ratio()+0.35*jac(grams(sa),grams(sb))
            if score>=0.78: union(a["candidateId"],b["candidateId"])
    groups=defaultdict(list)
    byid={c["candidateId"]:c for c in cand}
    for cid in parent: groups[find(cid)].append(cid)
    dup_groups=[{"ids":v,"hazards":[byid[x]["hazard"] for x in v]} for v in groups.values() if len(v)>1]

    summary={
      "candidateCount":len(rows),
      "confidenceCounts":{k:sum(1 for r in rows if r["matchConfidence"]==k) for k in ("exact","high","medium","low")},
      "nearDuplicateGroups":len(dup_groups),
    }
    out={"schemaVersion":"commerce-full-match-v1","summary":summary,"candidateNearDuplicateGroups":dup_groups,"rows":rows}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    # concise terminal list for low-confidence candidates
    for r in rows:
        if r["matchConfidence"]=="low":
            b=r["topMatches"][0] if r["topMatches"] else None
            print(json.dumps({"id":r["candidateId"],"hazard":r["hazard"],"best":b},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
