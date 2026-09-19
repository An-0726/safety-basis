# -*- coding: utf-8 -*-
"""修复 4 个 link review 的 contextHashes 和 decision。"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash

def main():
    # 1. K_XLSX_FT_F2F31FEEE9DC4C57B899A82F -> decision: "superseded"
    lr_path1 = KNOW / "reviews" / "links" / "K_XLSX_FT_F2F31FEEE9DC4C57B899A82F.json"
    lr1 = json.loads(lr_path1.read_text(encoding="utf-8"))
    lr1["decision"] = "superseded"
    lr1["reason"] = "所属隐患已合并至 H_66B2A0967E8B4E4BAD7749DF_1，该关联随之退出正式发布。"
    lr_path1.write_text(json.dumps(lr1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Updated K_XLSX_FT_F2F31FEEE9DC4C57B899A82F -> superseded")

    # 2. 刷新所有 active hazard 关联的 link review 的 contextHashes
    hazards = {}
    for p in (KNOW / "hazards").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        hazards[d["id"]] = d

    clauses = {}
    for p in (KNOW / "clauses").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        clauses[d["id"]] = d

    target_links = [
        "K_PHASE6_0BFFBEFB652BB2DF5B13E5D4",
        "K_XLSX_a5bcf36a6d6084de67d76489",
        "K_XLSX_NEW14_C3B79F3ED9952CE724957201"
    ]

    for lid in target_links:
        lpath = KNOW / "links" / f"{lid}.json"
        l = json.loads(lpath.read_text(encoding="utf-8"))
        hid = l["hazardId"]
        cid = l["clauseId"]
        h = hazards[hid]
        c = clauses[cid]

        lr_path = KNOW / "reviews" / "links" / f"{lid}.json"
        lr = json.loads(lr_path.read_text(encoding="utf-8"))

        h_hash = content_hash(h)
        c_hash = content_hash(c)
        l_hash = content_hash(l)

        lr["reviewedContentHash"] = l_hash
        lr["contextHashes"] = {
            "clause": c_hash,
            "hazard": h_hash,
            "link": l_hash
        }
        lr_path.write_text(json.dumps(lr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Refreshed contextHashes for {lid} (hid={hid})")

if __name__ == "__main__":
    main()
