#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quarantine the 36 PR #70 Changfeng batch records pending semantic re-audit.

This is deliberately review-only: no Stable ID, entity content, clause, or link
record is deleted or rewritten. Hazard definition reviews become pending and
the imported applicability reviews become rejected so the batch cannot enter
the public release until each record is independently re-verified.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
STAMP = "2026-09-21T00:20:00+08:00"
HAZARD_REASON = (
    "2026-09-21工程级审计发现PR #70批量导入存在重复实体、泛化direct依据及适用条件不足；"
    "本隐患暂时退出正式发布，待逐条去重并完成直接技术条款复核后再决定恢复。"
)
LINK_REASON = (
    "2026-09-21工程级审计撤销PR #70批量verified/direct结论：现有关联未证明该条款可直接覆盖"
    "本隐患全部构成要件，需逐条复核后另建或恢复合格关联。"
)

def dump(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    ids = [f"H_CF_GEN_{i:02d}" for i in range(1, 29)]
    ids += [f"H_CF_MAJOR_{i:02d}" for i in range(1, 9)]
    changed = 0
    for hid in ids:
        hp = KNOW / "reviews" / "hazards" / f"{hid}.json"
        if not hp.is_file():
            raise SystemExit(f"missing hazard review: {hp}")
        h = json.loads(hp.read_text(encoding="utf-8"))
        if h.get("entityId") != hid:
            raise SystemExit(f"hazard review entity mismatch: {hp}")
        h["decision"] = "pending"
        h["checkedAt"] = STAMP
        h["reviewer"] = "ChatGPT / Engineering Audit"
        h["reason"] = HAZARD_REASON
        dump(hp, h)
        changed += 1

        matches = sorted((KNOW / "links").glob(f"K_{hid[2:]}_*.json"))
        if len(matches) != 1:
            raise SystemExit(f"expected exactly one PR70 link for {hid}, got {len(matches)}")
        kid = matches[0].stem
        rp = KNOW / "reviews" / "links" / f"{kid}.json"
        if not rp.is_file():
            raise SystemExit(f"missing link review: {rp}")
        r = json.loads(rp.read_text(encoding="utf-8"))
        if r.get("entityId") != kid:
            raise SystemExit(f"link review entity mismatch: {rp}")
        r["decision"] = "rejected"
        r["checkedAt"] = STAMP
        r["reviewer"] = "ChatGPT / Engineering Audit"
        r["reason"] = LINK_REASON
        dump(rp, r)
        changed += 1

    print(f"quarantined reviews: {changed} (36 hazards + 36 links)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
