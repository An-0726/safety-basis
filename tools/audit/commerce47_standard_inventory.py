#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];K=ROOT/"knowledge"
def rd(p): return json.loads(p.read_text(encoding="utf-8"))
lvs=[rd(p) for p in (K/"law-versions").glob("*.json")]
clauses=[rd(p) for p in (K/"clauses").glob("*.json")]
def norm(s): return re.sub(r"\s+","",str(s or "").upper().replace("—","-").replace("–","-"))
wanted={
"GB 55024-2022":["8.5.1"],
"GB 50055-2011":["8.0.6"],
"GB/T 30134-2025":["5.1.21"],
"GB 50303-2015":["20.2.1","20.2.2","3.2.12","14.2.1","5.1.1"],
"GB 50058-2014":["5.2.1","5.2.2"],
"GB 55036-2022":["2.0.2","2.0.9","10.0.1","10.0.3"],
"GB 55009-2021":["6.2.1","6.2.5"],
"CJJ/T 146-2011":["3.3.1","3.3.2"],
"JGJ/T 46-2024":[],
"GB 55034-2022":["3.2.1","3.4.1"],
"GB 55023-2022":["4.4.4"],
"JGJ 80-2016":["8.2.1"],
"DL/T 1476-2023":["5.3.1.2","5.3.2.2"],
"CJJ/T 149-2021":["10.2.1"],
"GB 50037-2013":["3.2.7"],
"GB/T 40248-2021":["7.9.2"],
"XF 1131-2014":["5.1.1","6.15"],
"GB 15603-2022":["5.2"],
"GB 9448-2025":["11.5.5"],
"GB 2894-2025":["7.4.1"],
"GB 51251-2017":["4.3.6"],
"GB 55037-2022":["6.4.1","6.4.2","6.4.3"],
"TSG 08-2026":["4.12"],
}
out={}
for doc,arts in wanted.items():
    matches=[lv for lv in lvs if norm(lv.get("documentNumber"))==norm(doc)]
    rows=[]
    for lv in matches:
        cs=[c for c in clauses if c.get("lawVersionId")==lv["id"]]
        found=[]
        for art in arts:
            candidates=[c for c in cs if art in str(c.get("articlePath",""))]
            found.append({"article":art,"matches":[{"id":c["id"],"articlePath":c.get("articlePath"),"quote":c.get("quote")} for c in candidates]})
        rows.append({"lawVersion":lv,"clauseCount":len(cs),"articles":found})
    out[doc]=rows
print(json.dumps(out,ensure_ascii=False,indent=2))
