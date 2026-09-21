#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; K=ROOT/"knowledge"
def rd(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def norm(s):
    return re.sub(r"[\s·•，。；：、,.!！?？（）()“”‘’'\"《》【】\[\]—–_-]+","",str(s or "").lower())
def nnum(s):
    s=str(s or "").upper().replace("—","-").replace("–","-").replace(" ","")
    return s
def grams(s,n=2):
    s=norm(s); return {s[i:i+n] for i in range(max(0,len(s)-n+1))} or ({s} if s else set())
def jac(a,b): return len(a&b)/len(a|b) if a and b else 0.0
def load(name):
    out={}
    for p in (K/name).glob("*.json"):
        o=rd(p); oid=o.get("id") or o.get("entityId")
        if oid: out[oid]=o
    return out
DOC_RE=re.compile(r"(?i)(GB/T|GB|JGJ/T|JGJ|CJJ/T|CJJ|DL/T|JB/T|XF|TSG|DB\d+/T|DB\d+)[\s]*([0-9A-Z.]+)[—–-]?([0-9]{4})")
ARTICLE_RE=re.compile(r"第?([0-9]+(?:\.[0-9]+){0,4})条?(?:第([0-9]+)款)?(?:第?[（(]?([0-9一二三四五六七八九十]+)[）)]?项)?")
LAW_NAMES=["中华人民共和国消防法","中华人民共和国安全生产法","中华人民共和国特种设备安全法","危险化学品安全管理条例","建设工程安全生产管理条例","南京市燃气管理条例","江苏省燃气管理条例","南京市电动自行车消防安全管理办法"]
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args()
    cand=rd(ROOT/"tools/audit/commerce_full_candidates_20260921.json")["items"]
    laws=load("laws"); lvs=load("law-versions"); clauses=load("clauses"); links=load("links"); reviews=load("reviews/links"); hazards=load("hazards")
    lv_by_num=defaultdict(list)
    for lv in lvs.values(): lv_by_num[nnum(lv.get("documentNumber"))].append(lv)
    law_by_name=[]
    for law in laws.values(): law_by_name.append((norm(law.get("canonicalName")),law))
    clauses_by_lv=defaultdict(list)
    for c in clauses.values(): clauses_by_lv[c.get("lawVersionId")].append(c)
    links_by_c=defaultdict(list)
    for l in links.values(): links_by_c[l.get("clauseId")].append(l)
    rows=[]
    for cnd in cand:
        hits=[]
        for seed in cnd.get("legacyBases") or []:
            lv_candidates=[]
            for m in DOC_RE.finditer(seed):
                num=nnum(m.group(1)+m.group(2)+"-"+m.group(3))
                lv_candidates.extend(lv_by_num.get(num,[]))
            if not lv_candidates:
                ns=norm(seed)
                for lname,law in law_by_name:
                    if lname and lname in ns:
                        lv_candidates.extend([lv for lv in lvs.values() if lv.get("lawId")==law["id"]])
            # dedup current-looking versions first
            seen=set(); lv_candidates=[x for x in lv_candidates if not (x["id"] in seen or seen.add(x["id"]))]
            arts=[m.group(1) for m in ARTICLE_RE.finditer(seed)]
            for lv in lv_candidates:
                candidates=clauses_by_lv.get(lv["id"],[])
                ranked=[]
                for cl in candidates:
                    apath=norm(cl.get("articlePath"))
                    article_match=max([1.0 if a.replace(".","") in apath else 0.0 for a in arts], default=0.0)
                    text_sim=jac(grams(cnd["hazard"]),grams((cl.get("articlePath") or "")+" "+(cl.get("quote") or "")))
                    score=0.75*article_match+0.25*text_sim if arts else text_sim
                    if score>0.02: ranked.append((score,cl))
                ranked.sort(key=lambda x:x[0],reverse=True)
                for score,cl in ranked[:5]:
                    linked=[]
                    for l in links_by_c.get(cl["id"],[]):
                        rv=reviews.get(l["id"],{})
                        h=hazards.get(l.get("hazardId"),{})
                        linked.append({"linkId":l["id"],"role":l.get("role"),"lifecycle":l.get("lifecycle"),"review":rv.get("decision"),
                                       "hazardId":h.get("id"),"hazardTitle":h.get("title"),"hazardLifecycle":h.get("lifecycle")})
                    hits.append({"seed":seed,"lawVersionId":lv["id"],"documentNumber":lv.get("documentNumber"),"validityStatus":lv.get("validityStatus"),
                                 "effectiveDate":lv.get("effectiveDate"),"clauseId":cl["id"],"articlePath":cl.get("articlePath"),"quote":cl.get("quote"),
                                 "score":round(score,4),"linkedHazards":linked[:8]})
        # unique by lv/clause
        uniq=[]; seen=set()
        for h in sorted(hits,key=lambda x:x["score"],reverse=True):
            k=(h["lawVersionId"],h["clauseId"])
            if k in seen: continue
            seen.add(k);uniq.append(h)
        rows.append({"candidateId":cnd["candidateId"],"hazard":cnd["hazard"],"sources":cnd["sources"],"legacyBases":cnd["legacyBases"],"basisHits":uniq[:12]})
    out={"schemaVersion":"commerce-basis-match-v1","rows":rows,
         "summary":{"candidateCount":len(rows),"withBasisHits":sum(bool(r["basisHits"]) for r in rows),"withoutBasisHits":sum(not r["basisHits"] for r in rows)}}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True);Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out["summary"],ensure_ascii=False))
    for r in rows:
        if not r["basisHits"]: print(json.dumps({"id":r["candidateId"],"hazard":r["hazard"],"bases":r["legacyBases"]},ensure_ascii=False))
if __name__=="__main__": main()
