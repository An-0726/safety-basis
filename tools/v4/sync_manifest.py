# -*- coding: utf-8 -*-
"""同步 knowledge/manifest.json 到真实文件状态（幂等）。"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
MANIFEST = os.path.join(KNOW, "manifest.json")


def count(sub):
    return len(glob.glob(os.path.join(KNOW, sub, "*.json")))


counts = {
    "laws": count("laws"),
    "lawVersions": count("law-versions"),
    "clauses": count("clauses"),
    "hazards": count("hazards"),
    "links": count("links"),
    "evidence": count("evidence"),
    "successions": count("successions"),
    "requirements": count("requirements"),
}
print("real counts:", counts)

m = json.load(io.open(MANIFEST, encoding="utf-8"))
m["counts"] = counts
m["migrationPhase"] = "Phase 22 (final acceptance stage; production switch pending user approval)"
m["batch"] = "v4-final-20260910"
m["scope"] = (
    "V4 knowledge base at final acceptance: catalogue 68 laws/68 lawVersions, 76 clauses, "
    "75 requirement drafts, 662 hazards (642 migrated + 20 V3-verified backfill), 181 links "
    "with full applicability review (128 verified / 21 rejected / 32 pending), 552 evidence, "
    "22 successions. Composite hazards registered in docs/V4_HAZARD_SPLIT_TASKS.md. "
    "Candidate release v4-candidate-20260910 (production NOT switched)."
)
io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(json.dumps(m, ensure_ascii=False, indent=1) + "\n")
print("manifest synced")
