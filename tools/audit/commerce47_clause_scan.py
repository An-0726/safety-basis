#!/usr/bin/env python3
import json,re
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; K=ROOT/"knowledge"
def rd(p): return json.loads(Path(p).read_text(encoding="utf-8"))
haz=[rd(p) for p in (K/"hazards").glob("H_COM_*.json") if p.name!="H_COM_DUST_AIR_BLOW.json"]
laws={rd(p)["id"]:rd(p) for p in (K/"laws").glob("*.json")}
lvs={rd(p)["id"]:rd(p) for p in (K/"law-versions").glob("*.json")}
clauses=[rd(p) for p in (K/"clauses").glob("*.json")]
links=[rd(p) for p in (K/"links").glob("*.json")]
reviews={}
for p in (K/"reviews"/"clauses").glob("*.json"):
    o=rd(p); reviews[o.get("entityId") or p.stem]=o
link_reviews={}
for p in (K/"reviews"/"links").glob("*.json"):
    o=rd(p); link_reviews[o.get("entityId") or p.stem]=o
# standards/laws inferred from aliases/keywords/title are too weak; output all likely relevant verified clauses by token overlap and domain.
domain_terms={
"消防安全":["消防","灭火器","消火栓","疏散","防火门","排烟"],
"电气安全":["电气","配电","插座","导线","电缆","用电","行灯"],
"燃气安全":["燃气","气瓶","液化石油气","报警","切断阀","灶具"],
"机械与设备安全":["机械","设备","吊装","脚手架","气瓶","切割","冷库"],
"安全管理":["安全","警示","高处","巡查","制度","脚手架"],
"危险化学品与危险物质":["危险化学品","油漆","储存","仓库"],
"特种设备":["特种设备","叉车","检验"],
}
# precompute clause text and version metadata
crows=[]
for c in clauses:
    lv=lvs.get(c.get("lawVersionId"),{})
    law=laws.get(lv.get("lawId"),{})
    text=" ".join(map(str,[law.get("canonicalName",""),lv.get("documentNumber",""),c.get("articlePath",""),c.get("quote","")]))
    crows.append((c,lv,law,text))
out=[]
for h in sorted(haz,key=lambda x:x["id"]):
    tokens=[t for t in re.split(r"[，。、；：（）\s]+",h.get("title","")+" "+h.get("description","")+" "+" ".join(h.get("keywords") or [])) if len(t)>=2]
    scored=[]
    for c,lv,law,text in crows:
        rv=reviews.get(c["id"],{})
        if c.get("lifecycle")!="active" or rv.get("decision")!="verified": continue
        score=sum(1 for t in tokens if t in text)
        if h.get("category") in domain_terms and any(t in text for t in domain_terms[h["category"]]): score+=2
        if score:
            scored.append((score,c,lv,law))
    scored.sort(key=lambda x:(-x[0],x[1]["id"]))
    out.append({"hazardId":h["id"],"title":h["title"],"category":h.get("category"),
                "top":[{"score":s,"clauseId":c["id"],"articlePath":c.get("articlePath"),
                        "quote":c.get("quote"),"lawVersionId":lv.get("id"),"documentNumber":lv.get("documentNumber"),
                        "lawName":law.get("canonicalName"),"validityStatus":lv.get("validityStatus")} for s,c,lv,law in scored[:12]]})
Path("/tmp/commerce47-clause-hits.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"hazards":len(out),"with_hits":sum(bool(x["top"]) for x in out),"without_hits":sum(not x["top"] for x in out)},ensure_ascii=False))
for x in out:
    print(json.dumps({"id":x["hazardId"],"title":x["title"],"top":x["top"][:5]},ensure_ascii=False))
