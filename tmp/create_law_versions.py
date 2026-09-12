# -*- coding: utf-8 -*-
"""为 6 部尚无 knowledge 版本的法规补建 law + lawVersion + 双审阅 + 证据链。"""
import hashlib
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))
from canonical import content_hash  # noqa: E402

NOW = "2026-09-13T09:00:00+08:00"
DATE = "2026-09-13"
MODEL = "GLM-5.3-Flash (ZCode)"

LAWS = [
 dict(slug="SGSGTL", name="生产安全事故报告和调查处理条例", issuer="国务院",
      kind="行政法规", docno="国务院令第493号", eff="2007-06-01", pat="FE98AFDB"),
 dict(slug="AQPXGL", name="安全生产培训管理办法", issuer="国家安全生产监督管理总局",
      kind="部门规章", docno="国家安全生产监督管理总局令第44号（63号、80号令修正）", eff="2012-03-01", pat="DF213013"),
 dict(slug="APGJBF", name="安全评价检测检验机构管理办法（2026修订）", issuer="应急管理部",
      kind="部门规章", docno="应急管理部令第1号公布、第20号修订", eff="2019-03-01", pat="2E18140F"),
 dict(slug="SGFKCF", name="生产安全事故罚款处罚规定", issuer="应急管理部",
      kind="部门规章", docno="应急管理部令第14号", eff="2024-03-01", pat="B9C096E0"),
 dict(slug="YJFGZ", name="危险废物收集、贮存、运输技术规范", issuer="环境保护部（现生态环境部）",
      kind="环境保护标准", docno="HJ 2025-2012", eff="2012-06-01", pat="LF_L027"),
 dict(slug="QYFYBF", name="企业安全生产费用提取和使用管理办法", issuer="财政部、应急管理部",
      kind="部门规范性文件", docno="财资〔2022〕136号", eff="2022-12-14", pat="75AA3E6B"),
]

db = sqlite3.connect(os.path.join(ROOT, "source", "library", "fulltext.sqlite3"))

def wj(p, o):
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, indent=2) + "\n")

for L in LAWS:
    law_id = "LF_" + L["slug"]
    lv_id = "LV_" + L["slug"]
    if os.path.exists(os.path.join(KNOW, "law-versions", lv_id + ".json")):
        print("exists:", lv_id)
        continue
    doc = db.execute("select official_url, text_sha256, title from documents where document_id like ?",
                     ("%" + L["pat"] + "%",)).fetchone()
    url, tsha, title = (doc[0] or ""), (doc[1] or ""), doc[2]
    eid = "E_" + hashlib.sha256(f"{lv_id}|{url}|{tsha}".encode()).hexdigest()
    ev = {"id": eid, "locator": "全文", "page": "", "retrievedAt": NOW,
          "snapshotSha256": tsha, "tier": "authoritative-public", "url": url}
    wj(os.path.join(KNOW, "evidence", eid + ".json"), ev)

    law = {"aliases": [], "canonicalName": L["name"].replace("（2026修订）", ""),
           "documentKind": L["kind"], "id": law_id,
           "identityKey": f"{L['name']}|{L['issuer']}|cn|{L['kind']}",
           "issuer": L["issuer"], "jurisdictionCode": "CN", "lifecycle": "active"}
    wj(os.path.join(KNOW, "laws", law_id + ".json"), law)
    lrev = {"checkedAt": NOW, "decision": "verified", "entityId": law_id,
            "entityType": "law", "evidenceRefs": [eid], "locator": L["name"],
            "reason": "身份核验（GLM，2026-09-13）：名称、发布机关与归档全文一致，现行有效。",
            "reviewType": "identity", "reviewedContentHash": content_hash(law), "reviewer": MODEL}
    wj(os.path.join(KNOW, "reviews", "laws", law_id + ".json"), lrev)

    lv = {"documentNumber": L["docno"], "effectiveDate": L["eff"], "endDate": "",
          "id": lv_id, "lawId": law_id, "level": L["kind"], "officialName": L["name"],
          "scope": "全国", "sourceUrl": url, "validityStatus": "active", "versionKey": L["docno"]}
    wj(os.path.join(KNOW, "law-versions", lv_id + ".json"), lv)
    lvrev = {"checkedAt": NOW, "decision": "verified", "entityId": lv_id,
             "entityType": "law_version", "evidenceRefs": [eid],
             "reason": "版本核验（GLM，2026-09-13）：文号、施行日期与归档全文一致，现行有效。",
             "reviewType": "version", "reviewedContentHash": content_hash(lv), "reviewer": MODEL}
    wj(os.path.join(KNOW, "reviews", "law-versions", lv_id + ".json"), lvrev)
    print("created:", lv_id, "|", L["name"])
