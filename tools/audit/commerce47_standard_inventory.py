#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];K=ROOT/"knowledge"
TARGETS=["JGJ 392-2016","GB 55024-2022","GB 55023-2022","GB 55036-2022","GB 55009-2021","JGJ 18-2012","GB 9448-2025","CJJ/T 146-2011","JGJ/T 46-2024","JGJ 46-2005","DL/T 1476-2023","GB 55037-2022","CJJ/T 149-2021","GB 51210-2016","GB 51251-2017","CJ/T 28-2013","GB 50055-2011","GB/T 30134-2025","GB 50037-2013","GB 50054-2011","GB 50303-2015","GB/T 40248-2021","GB 14444-2025","GB 2894-2025","GB/T 33000-2016","XF 1131-2014"]
def rd(p): return json.loads(p.read_text(encoding="utf-8"))
def norm(s):
    return re.sub(r"[^A-Z0-9./-]","",str(s or "").upper().replace("—","-").replace("–","-"))
lvs={rd(p)["id"]:rd(p) for p in (K/"law-versions").glob("*.json")}
laws={rd(p)["id"]:rd(p) for p in (K/"laws").glob("*.json")}
clauses=[rd(p) for p in (K/"clauses").glob("*.json")]
bylv={}
for c in clauses: bylv.setdefault(c.get("lawVersionId"),[]).append(c)
for t in TARGETS:
    nt=norm(t); matches=[]
    for lv in lvs.values():
        n=norm(lv.get("documentNumber"))
        if nt==n or nt in n or n in nt:
            law=laws.get(lv.get("lawId"),{})
            rows=sorted(bylv.get(lv["id"],[]),key=lambda x:str(x.get("articlePath","")))
            matches.append({"lawVersionId":lv["id"],"documentNumber":lv.get("documentNumber"),"validityStatus":lv.get("validityStatus"),
                            "effectiveDate":lv.get("effectiveDate"),"lawName":law.get("canonicalName"),
                            "clauses":[{"id":c["id"],"articlePath":c.get("articlePath"),"quote":c.get("quote")} for c in rows]})
    print(json.dumps({"target":t,"matches":matches},ensure_ascii=False))
