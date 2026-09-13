# -*- coding: utf-8 -*-
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
AS_OF = "2026-09-13"
LAW = "LF_META_AQPX"
VID = "LV_META_FC43256C0F595A6F9165697E"
URL = "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/201201/t20120119_405680.shtml"


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    law = {"canonicalName": "安全生产培训管理办法", "documentKind": "部门规章", "id": LAW,
           "identityKey": "安全生产培训管理办法|国家安全生产监督管理总局|CN|部门规章",
           "issuer": "国家安全生产监督管理总局", "jurisdictionCode": "CN",
           "officialName": "安全生产培训管理办法", "sourceUrl": URL,
           "aliases": ["国家安全生产监督管理总局令第44号", "第63号修正", "第80号修正"]}
    lv = {"documentNumber": "国家安全生产监督管理总局令第44号（2015年修正）",
          "effectiveDate": "2012-03-01", "endDate": "", "id": VID, "lawId": LAW,
          "level": "部门规章", "officialName": "安全生产培训管理办法", "scope": "CN",
          "sourceUrl": URL, "validityStatus": "active", "versionKey": "2015修正"}
    eid = "E_XLSX_AQPX_OFFICIAL"
    evidence = {"id": eid, "locator": "全文", "page": "", "retrievedAt": AS_OF,
                "snapshotSha256": "official-training-pdf", "tier": "authoritative-public", "url": URL}
    write(os.path.join(KNOW, "laws", LAW + ".json"), law)
    write(os.path.join(KNOW, "law-versions", VID + ".json"), lv)
    write(os.path.join(KNOW, "evidence", eid + ".json"), evidence)
    write(os.path.join(KNOW, "reviews", "laws", LAW + ".json"), {
        "checkedAt": AS_OF, "decision": "verified", "entityId": LAW, "entityType": "law",
        "evidenceRefs": [eid], "reason": "已核对应急管理部官方规章页面及2015年修正说明。",
        "reviewType": "identity", "reviewedContentHash": content_hash(law),
        "reviewer": "Codex正式核验批次20260913"})
    write(os.path.join(KNOW, "reviews", "law-versions", VID + ".json"), {
        "checkedAt": AS_OF, "decision": "verified", "entityId": VID, "entityType": "law_version",
        "evidenceRefs": [eid], "reason": "官方页面确认第44号规章经第63号、第80号修正，实施日为2012-03-01。",
        "reviewType": "version", "reviewedContentHash": content_hash(lv),
        "reviewer": "Codex正式核验批次20260913"})
    mp = os.path.join(KNOW, "manifest.json")
    manifest = read(mp); bid = "law-identity-aqpx-20260913"
    if bid not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({"id": bid, "lawsAdded": 1,
            "lawVersionsAdded": 1, "evidenceAdded": 1,
            "selection": "Official MEM page and PDF verified for 安全生产培训管理办法 (2015 amendment)."})
    manifest.setdefault("counts", {})["laws"] = len(load_dir(KNOW, "laws"))
    manifest["counts"]["lawVersions"] = len(load_dir(KNOW, "law-versions"))
    manifest["counts"]["evidence"] = len(load_dir(KNOW, "evidence"))
    write(mp, manifest)
    print(json.dumps({"law": LAW, "lawVersion": VID}, ensure_ascii=False))


if __name__ == "__main__":
    main()
