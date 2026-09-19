# -*- coding: utf-8 -*-
"""修复 14 个 review rejected 但 link lifecycle 仍为 active 的状态不一致问题。"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

def main():
    with open(ROOT / "docs" / "scan_findings.jsonl", "r", encoding="utf-8") as f:
        findings = [json.loads(line) for line in f]

    rejected_links = [f["entity_id"] for f in findings if f["rule_id"] == "RULE_REJECTED_LINK_ACTIVE"]
    print(f"Total rejected links to remediate: {len(rejected_links)}")

    for lid in rejected_links:
        lpath = KNOW / "links" / f"{lid}.json"
        l = json.loads(lpath.read_text(encoding="utf-8"))
        rpath = KNOW / "reviews" / "links" / f"{lid}.json"
        r = json.loads(rpath.read_text(encoding="utf-8"))
        hid = l.get("hazardId")
        h = json.loads((KNOW / "hazards" / f"{hid}.json").read_text(encoding="utf-8"))
        h_life = h.get("lifecycle")

        # 确定修正后的 lifecycle
        if h_life == "superseded":
            new_life = "superseded"
        else:
            new_life = "proposed"

        print(f"Link {lid}: hazard {hid} ({h_life}), current link lifecycle={l.get('lifecycle')} -> new link lifecycle={new_life}")

if __name__ == "__main__":
    main()
