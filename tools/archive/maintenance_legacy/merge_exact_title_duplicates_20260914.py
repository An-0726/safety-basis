# -*- coding: utf-8 -*-
"""Merge only exact-title candidate duplicates with existing formal records."""
import json
from pathlib import Path
import sys
import re

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
AS_OF = "2026-09-14"

PAIRS = (
    ("H_E802C3AF73D1BDF70B0251EE4A_1", "H_998C5607F7EAB6589B9DD35598_2"),
    ("H_03BA3BFFA73DDEFE94C3ACED_1", "H_A6FFD804B89A850BBF832DC4_1"),
    ("H_45A24EA090E13562E178D67F6E_1", "H_128CF6B2AEFB46EA98D63BE037"),
    ("H_15577_8_1_5_1", "H_6F52BBD3B8764A2EB1BD84D811"),
    ("H_C8694BE798B94E39B4566EAB6B", "H_15577_4_7_1"),
)


def title_key(value):
    return re.sub(r"[\s，。；：、,.;:（）()【】\[\]“”\"‘’/\\\-—_]+", "", str(value or "")).casefold()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    sys.path.insert(0, str(ROOT / "tools" / "v4"))
    from canonical import content_hash
    hazards = {p.stem: read(p) for p in (KNOW / "hazards").glob("*.json")}
    merged = []
    for canonical_id, duplicate_id in PAIRS:
        canonical = hazards[canonical_id]
        duplicate = hazards[duplicate_id]
        if duplicate.get("mergedInto") == canonical_id:
            continue
        if duplicate.get("lifecycle") != "proposed":
            raise SystemExit(f"duplicate is not proposed: {duplicate_id}")
        if title_key(duplicate.get("title")) != title_key(canonical.get("title")):
            raise SystemExit(f"title mismatch: {canonical_id} / {duplicate_id}")
        duplicate["lifecycle"] = "active"
        duplicate["mergedInto"] = canonical_id
        duplicate.pop("proposalStatus", None)
        duplicate.pop("sourceRow", None)
        duplicate["note"] = (str(duplicate.get("note") or "").rstrip() +
                              f"\n本批已与 {canonical_id} 合并：标题、对象和整改主题相同，正式条款关系保留在主记录。").strip()
        write(KNOW / "hazards" / f"{duplicate_id}.json", duplicate)
        review = {
            "checkedAt": AS_OF,
            "decision": "verified",
            "entityId": duplicate_id,
            "entityType": "hazard",
            "evidenceRefs": read(KNOW / "reviews" / "hazards" / f"{canonical_id}.json").get("evidenceRefs", []),
            "reason": f"与 {canonical_id} 为同标题同主题重复候选，已合并；不重复发布。",
            "reviewType": "deduplication",
            "reviewedContentHash": content_hash(duplicate),
            "reviewer": "Codex新版整改去重批次20260914",
        }
        write(KNOW / "reviews" / "hazards" / f"{duplicate_id}.json", review)
        merged.append({"canonical": canonical_id, "merged": duplicate_id})

    manifest_path = KNOW / "manifest.json"
    manifest = read(manifest_path)
    batch_id = "merge-exact-title-duplicates-20260914"
    if batch_id not in {b.get("id") for b in manifest.get("batches", [])}:
        manifest.setdefault("batches", []).append({
            "id": batch_id,
            "hazardsMerged": len(merged),
            "selection": "Merge only exact-title candidate duplicates into existing formal hazards; retain distinct clause contexts separately.",
        })
    manifest.setdefault("counts", {})["hazards"] = len(list((KNOW / "hazards").glob("*.json")))
    manifest["counts"]["clauses"] = len(list((KNOW / "clauses").glob("*.json")))
    manifest["counts"]["links"] = len(list((KNOW / "links").glob("*.json")))
    write(manifest_path, manifest)
    out = ROOT / "source" / "proposals" / "excel-20260914" / "merge-exact-title-report.json"
    write(out, {"asOf": AS_OF, "merged": merged, "note": "Other same-title groups with distinct article contexts were intentionally retained."})
    print(json.dumps({"merged": merged, "count": len(merged)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
