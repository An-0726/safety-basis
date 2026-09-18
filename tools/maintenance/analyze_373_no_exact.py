# -*- coding: utf-8 -*-
"""分析 373 条 no_exact_current_reviewed_clause 候选的依据分布与知识库/母库覆盖度。"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"

def main():
    proposed_ids = set(
        p.stem for p in (KNOW / "hazards").glob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("lifecycle") == "proposed"
    )

    hazards = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in (KNOW / "hazards").glob("*.json")
        if p.stem in proposed_ids
    }

    lvs = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in (KNOW / "law-versions").glob("*.json")
    }

    laws = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in (KNOW / "laws").glob("*.json")
    }

    clauses = {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in (KNOW / "clauses").glob("*.json")
    }

    p6_records = {}
    with open(ROOT / "docs" / "phase6-final-disposition.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("recordType") == "metadata":
                continue
            if d["hazardId"] in proposed_ids:
                p6_records[d["hazardId"]] = d

    no_exact = [
        hid for hid in proposed_ids
        if p6_records.get(hid, {}).get("reasonCode") == "no_exact_current_reviewed_clause"
    ]

    print(f"Total no_exact_current_reviewed_clause: {len(no_exact)}")

    # 提取依据法规线索
    std_regex = re.compile(
        r"(GB/T\s?\d{3,5}(?:\.\d+)?(?:[-—]\d{4})?|"
        r"GB\s?[1-5]\d{4}(?:\.\d+)?(?:[-—]\d{4})?|"
        r"AQ/T\s?\d{3,5}(?:[-—]\d{4})?|"
        r"AQ\s?\d{3,5}(?:[-—]\d{4})?|"
        r"TSG\s?[A-Z0-9\-]+|"
        r"JGJ\s?\d+(?:[-—]\d{4})?|"
        r"HJ\s?\d+(?:[-—]\d{4})?|"
        r"HG/T\s?\d+(?:[-—]\d{4})?|"
        r"DL/T\s?\d+(?:[-—]\d{4})?|"
        r"GA\s?\d+(?:[-—]\d{4})?|"
        r"中华人民共和国[\u4e00-\u9fa5]+法|"
        r"江苏省[\u4e00-\u9fa5]+条例|"
        r"南京市[\u4e00-\u9fa5]+条例|"
        r"危险化学品安全管理条例|"
        r"工贸企业粉尘防爆安全规定|"
        r"工贸企业有限空间作业安全规定|"
        r"工贸企业重大事故隐患判定标准|"
        r"安全生产事故隐患排查治理暂行规定|"
        r"特种设备安全监察条例)"
    )

    std_counts = Counter()
    hazard_stds = defaultdict(list)
    no_std_found = []

    for hid in no_exact:
        h = hazards[hid]
        text = f"{h.get('title', '')} {h.get('description', '')} {h.get('note', '')}"
        found = set()
        for m in std_regex.findall(text):
            clean = re.sub(r"\s+", " ", m).strip()
            # 归一化一些常见名称
            clean = clean.replace("—", "-")
            found.add(clean)
        if found:
            for s in found:
                std_counts[s] += 1
                hazard_stds[s].append(hid)
        else:
            no_std_found.append(hid)

    print("\nTop 35 standards/laws mentioned in no_exact hazards:")
    for s, count in std_counts.most_common(35):
        print(f"  {s}: {count}")

    print(f"\nHazards with no standard regex match: {len(no_std_found)}")
    for hid in no_std_found[:10]:
        h = hazards[hid]
        print(f"  {hid} | {h.get('title')} | note: {h.get('note', '')[:70]}")

if __name__ == "__main__":
    main()
