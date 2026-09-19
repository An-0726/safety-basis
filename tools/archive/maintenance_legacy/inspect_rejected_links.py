# -*- coding: utf-8 -*-
"""打印 14 个 rejected 关联的详细信息。"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

def main():
    with open(ROOT / "docs" / "scan_findings.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["rule_id"] == "RULE_REJECTED_LINK_ACTIVE":
                lid = d["entity_id"]
                l = json.loads((KNOW / "links" / f"{lid}.json").read_text(encoding="utf-8"))
                r = json.loads((KNOW / "reviews" / "links" / f"{lid}.json").read_text(encoding="utf-8"))
                hid = l.get("hazardId")
                h = json.loads((KNOW / "hazards" / f"{hid}.json").read_text(encoding="utf-8"))
                print(f"{lid} | hid={hid} (hazard_lifecycle={h.get('lifecycle')}) | cid={l.get('clauseId')} | reason={r.get('reason')}")

if __name__ == "__main__":
    main()
