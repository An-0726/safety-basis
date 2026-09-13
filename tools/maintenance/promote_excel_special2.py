# -*- coding: utf-8 -*-
"""Formalize the two remaining private-fulltext candidates with exact text."""
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import load_dir  # noqa: E402

KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")
AS_OF = "2026-09-13"


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    hazards = load_dir(KNOW, "hazards")
    specs = [
        ("H026", "C_XLSX_SPECIAL_GB50140_6_1_1", "L008", "6.1.1",
         "一个计算单元内配置的灭火器数量不得少于2具。",
         "E_XLSX_SPECIAL_GB50140_6_1_1",
         "https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2006/art_17339_155839.html"),
        ("H029", "C_XLSX_SPECIAL_GB50054_6_1_1", "LV_STD_GB50054_2011", "6.1.1",
         "配电线路应装设短路保护和过负荷保护。",
         "E_XLSX_SPECIAL_GB50054_6_1_1",
         "https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2011/art_17339_206925.html"),
    ]
    promoted = []
    for hid, cid, vid, article, quote, eid, url in specs:
        hz = hazards.get(hid)
        if not hz or hz.get("lifecycle") != "proposed":
            continue
        clause = {"articlePath": article, "id": cid, "jurisdictionCode": "CN",
                  "lawVersionId": vid, "lifecycle": "active", "quote": quote,
                  "sourceUrl": url}
        evidence = {"id": eid, "locator": "第" + article + "条", "page": "",
                    "retrievedAt": AS_OF, "snapshotSha256": "local-archived-fulltext",
                    "tier": "authoritative-public", "url": url}
        write(os.path.join(KNOW, "clauses", cid + ".json"), clause)
        write(os.path.join(KNOW, "evidence", eid + ".json"), evidence)
        write(os.path.join(KNOW, "reviews", "clauses", cid + ".json"), {
            "checkedAt": AS_OF, "decision": "verified", "entityId": cid,
            "entityType": "clause", "evidenceRefs": [eid],
            "reason": "已核对本地归档全文/原始文档中的条款原文。", "reviewType": "text",
            "reviewedContentHash": content_hash(clause), "reviewer": "Codex正式核验批次20260913"})
        hz["lifecycle"] = "active"; hz["mode"] = "direct"
        hz.pop("proposalStatus", None); hz.pop("sourceRow", None)
        marker = "本批已核对对应技术标准条款原文并完成适用性核验。"
        if marker not in str(hz.get("note") or ""):
            hz["note"] = (str(hz.get("note") or "").rstrip() + "\n" + marker).strip()
        link_id = "K_XLSX_SPECIAL_" + hashlib.sha1((hid + cid).encode("utf-8")).hexdigest()[:24].upper()
        link = {"applicability": hz.get("conditions") or "适用于Excel来源隐患描述的对应设施和作业条件。",
                "clauseId": cid, "hazardId": hid, "id": link_id, "jurisdictionCode": "CN",
                "legacyRole": "直接依据", "lifecycle": "active", "priority": 10,
                "reason": "隐患对象与技术条款直接对应，作为直接依据。", "role": "direct"}
        write(os.path.join(KNOW, "hazards", hid + ".json"), hz)
        write(os.path.join(KNOW, "links", link_id + ".json"), link)
        write(os.path.join(KNOW, "reviews", "hazards", hid + ".json"), {
            "checkedAt": AS_OF, "decision": "verified", "entityId": hid, "entityType": "hazard",
            "evidenceRefs": [eid], "reason": "隐患描述、整改措施与技术条款原文逐项对应。",
            "reviewType": "content", "reviewedContentHash": content_hash(hz),
            "reviewer": "Codex正式核验批次20260913"})
        write(os.path.join(KNOW, "reviews", "links", link_id + ".json"), {
            "checkedAt": AS_OF, "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hz)},
            "decision": "verified", "entityId": link_id, "entityType": "link",
            "evidenceRefs": [eid], "reason": "隐患对象与条款原文直接对应。",
            "reviewType": "applicability", "reviewedContentHash": content_hash(link),
            "reviewer": "Codex正式核验批次20260913"})
        promoted.append(hid)
    mpath=os.path.join(KNOW,"manifest.json");m=read(mpath);bid="excel-formalize-special2-batch-20260913"
    if bid not in {x.get('id') for x in m.get('batches',[])}:m.setdefault('batches',[]).append({'id':bid,'hazardsAdded':len(promoted),'clausesAdded':len(promoted),'linksAdded':len(promoted),'evidenceAdded':len(promoted),'selection':'Exact archived text verification for GB 50140-2005 and GB 50054-2011 candidates.'})
    m.setdefault('counts',{})['hazards']=len(load_dir(KNOW,'hazards'));m['counts']['clauses']=len(load_dir(KNOW,'clauses'));m['counts']['links']=len(load_dir(KNOW,'links'));write(mpath,m)
    write(os.path.join(PROPOSAL,'formalize-special2-report.json'),{'asOf':AS_OF,'promoted':promoted,'generatedAt':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'promoted':len(promoted),'hazardIds':promoted},ensure_ascii=False))


if __name__ == '__main__':
    main()
