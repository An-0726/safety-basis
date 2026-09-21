#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json,re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
K=ROOT/"knowledge"
def rd(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def norm_num(s):
    s=str(s or "").upper().replace("—","-").replace("–","-").replace("－","-")
    s=re.sub(r"\s+","",s)
    s=s.replace("（","(").replace("）",")")
    return s
def norm_name(s):
    return re.sub(r"[《》〈〉\s（）()—–-]+","",str(s or "").lower())
def art_tokens(s):
    out=[]
    # Numeric standard clauses: 10.2.3 / 5.2.1 etc.
    for m in re.finditer(r"(?<!\d)(\d+(?:\.\d+){1,4})(?!\d)", s):
        out.append(m.group(1))
    # Chinese law articles.
    for m in re.finditer(r"第([一二三四五六七八九十百零〇两]+)条", s):
        out.append("第"+m.group(1)+"条")
    # Arabic article in Chinese form.
    for m in re.finditer(r"第(\d+)条", s):
        out.append("第"+m.group(1)+"条")
    return list(dict.fromkeys(out))

STD_RE=re.compile(r"(?i)(GB/T|GB|JGJ/T|JGJ|CJJ/T|CJJ|DL/T|JB/T|XF|TSG|DB\d+(?:/T)?)[\s]*([0-9A-Z.]+)[—–-]?(20\d{2})")
LAW_ALIASES={
"中华人民共和国安全生产法":["中华人民共和国安全生产法","安全生产法"],
"中华人民共和国消防法":["中华人民共和国消防法","消防法"],
"危险化学品安全管理条例":["危险化学品安全管理条例"],
"建设工程安全生产管理条例":["建设工程安全生产管理条例"],
"江苏省燃气管理条例":["江苏省燃气管理条例"],
"南京市电动自行车消防安全管理办法":["南京市电动自行车消防安全管理办法"],
"食品生产经营监督检查管理办法":["食品生产经营监督检查管理办法"],
}
basis=rd(ROOT/"tools"/"audit"/"commerce47_legacy_basis.json")["hazards"]
laws={rd(p)["id"]:rd(p) for p in (K/"laws").glob("*.json")}
lvs={rd(p)["id"]:rd(p) for p in (K/"law-versions").glob("*.json")}
clauses={rd(p)["id"]:rd(p) for p in (K/"clauses").glob("*.json")}
creviews={}
for p in (K/"reviews"/"clauses").glob("*.json"):
    o=rd(p); creviews[o.get("entityId") or p.stem]=o

lv_by_num=defaultdict(list)
for lv in lvs.values():
    lv_by_num[norm_num(lv.get("documentNumber"))].append(lv)
law_versions_by_law=defaultdict(list)
for lv in lvs.values(): law_versions_by_law[lv.get("lawId")].append(lv)
law_ids_by_alias={}
for lid,law in laws.items():
    nm=norm_name(law.get("canonicalName"))
    law_ids_by_alias[nm]=lid
    for alias in law.get("aliases") or []: law_ids_by_alias[norm_name(alias)]=lid
for canonical,aliases in LAW_ALIASES.items():
    # map explicit aliases to existing canonical law if present
    lid=None
    for x,y in laws.items():
        if norm_name(y.get("canonicalName"))==norm_name(canonical): lid=x; break
    if lid:
        for a in aliases: law_ids_by_alias[norm_name(a)]=lid

clauses_by_lv=defaultdict(list)
for c in clauses.values(): clauses_by_lv[c.get("lawVersionId")].append(c)

def exact_article_match(token,article_path):
    a=str(article_path or "").replace(" ","")
    if token.startswith("第"):
        return token in a
    # numeric clause token; require boundary-ish match
    return bool(re.search(r"(?<![\d.])"+re.escape(token)+r"(?![\d.])",a)) or a==token or a.endswith(token)

out=[]
for hid,row in sorted(basis.items()):
    seeds=[]
    for item in row["items"]:
        seeds.extend(item.get("legacyBases") or [])
    hits=[]; missing=[]
    for seed in seeds:
        candidates=[]
        stds=list(STD_RE.finditer(seed))
        for m in stds:
            num=norm_num(m.group(1)+m.group(2)+"-"+m.group(3))
            # tolerate spacing difference and older storage of document number extra text
            for k,vals in lv_by_num.items():
                if num==k or num in k or k in num:
                    candidates.extend(vals)
        if not stds:
            ns=norm_name(seed)
            for alias,lid in law_ids_by_alias.items():
                if alias and alias in ns:
                    candidates.extend(law_versions_by_law.get(lid,[]))
        # dedupe
        uniq=[]; seen=set()
        for lv in candidates:
            if lv["id"] not in seen:
                seen.add(lv["id"]);uniq.append(lv)
        arts=art_tokens(seed)
        matched_seed=[]
        for lv in uniq:
            for c in clauses_by_lv.get(lv["id"],[]):
                rv=creviews.get(c["id"],{})
                if c.get("lifecycle")!="active" or rv.get("decision")!="verified": continue
                if arts and not any(exact_article_match(a,c.get("articlePath")) for a in arts):
                    continue
                matched_seed.append({
                    "seed":seed,"lawVersionId":lv["id"],"documentNumber":lv.get("documentNumber"),
                    "validityStatus":lv.get("validityStatus"),"effectiveDate":lv.get("effectiveDate"),
                    "clauseId":c["id"],"articlePath":c.get("articlePath"),"quote":c.get("quote"),
                    "sourceUrl":c.get("sourceUrl")
                })
        if matched_seed: hits.extend(matched_seed)
        else: missing.append(seed)
    # prioritize active current versions over upcoming
    hits.sort(key=lambda x:(x.get("validityStatus")!="active",x["documentNumber"] or "",x["articlePath"] or "",x["clauseId"]))
    # dedupe clause
    final=[]; seen=set()
    for h in hits:
        if h["clauseId"] in seen: continue
        seen.add(h["clauseId"]);final.append(h)
    out.append({"hazardId":hid,"title":row.get("title"),"exactHits":final,"unmatchedSeeds":list(dict.fromkeys(missing))})
summary={"hazards":len(out),"withExact":sum(bool(x["exactHits"]) for x in out),"withoutExact":sum(not x["exactHits"] for x in out),
         "activeExact":sum(any(h.get("validityStatus")=="active" for h in x["exactHits"]) for x in out)}
Path("/tmp/commerce47-exact.json").write_text(json.dumps({"summary":summary,"rows":out},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
for x in out:
    print(json.dumps({"id":x["hazardId"],"title":x["title"],"hits":[{"doc":h["documentNumber"],"article":h["articlePath"],"cid":h["clauseId"],"status":h["validityStatus"]} for h in x["exactHits"]],"unmatched":x["unmatchedSeeds"]},ensure_ascii=False))
