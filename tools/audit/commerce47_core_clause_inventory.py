#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];K=ROOT/"knowledge"
def rd(p): return json.loads(p.read_text(encoding="utf-8"))
laws={rd(p)["id"]:rd(p) for p in (K/"laws").glob("*.json")}
lvs={rd(p)["id"]:rd(p) for p in (K/"law-versions").glob("*.json")}
clauses=[rd(p) for p in (K/"clauses").glob("*.json")]
wanted=[
"中华人民共和国消防法","中华人民共和国安全生产法","中华人民共和国特种设备安全法",
"中华人民共和国危险化学品安全法","危险化学品安全管理条例",
"南京市电动自行车消防安全管理办法","爆炸危险环境电力装置设计规范",
"危险化学品仓库储存通则","用电安全导则","消防设施通用规范",
"建筑防火通用规范","燃气工程项目规范","焊接与切割安全",
"建筑电气工程施工质量验收规范","安全色和安全标志","仓储场所消防安全管理通则"
]
for lv in sorted(lvs.values(),key=lambda x:x["id"]):
    law=laws.get(lv.get("lawId"),{})
    name=law.get("canonicalName","")
    if not any(w in name or w in lv.get("officialName","") for w in wanted): continue
    rows=[c for c in clauses if c.get("lawVersionId")==lv["id"] and c.get("lifecycle")=="active"]
    print(json.dumps({"lawVersionId":lv["id"],"lawName":name,"documentNumber":lv.get("documentNumber"),
                      "validityStatus":lv.get("validityStatus"),"clauses":[{"id":c["id"],"articlePath":c.get("articlePath"),"quote":c.get("quote")} for c in sorted(rows,key=lambda x:str(x.get("articlePath","")))]},ensure_ascii=False))
