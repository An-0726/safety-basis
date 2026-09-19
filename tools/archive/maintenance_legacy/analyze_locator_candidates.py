# -*- coding: utf-8 -*-
"""分析有定位或特定原因的候选明细。"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

def main():
    proposed_ids = set(
        p.stem for p in (KNOW / "hazards").glob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("lifecycle") == "proposed"
    )

    with open(ROOT / "docs" / "phase6-final-disposition.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("recordType") == "metadata":
                continue
            if d["hazardId"] in proposed_ids:
                code = d.get("reasonCode")
                if code != "no_exact_current_reviewed_clause":
                    hid = d["hazardId"]
                    cids = d.get("clauseIds")
                    title = d.get("title", "")[:30]
                    reason = d.get("reason", "")
                    print(f"{hid} | {code} | {cids} | {title} | {reason}")

if __name__ == "__main__":
    main()
