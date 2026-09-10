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
m["migrationPhase"] = "Phase 16 (final acceptance in progress; production switch pending user approval)"
m["batch"] = "v4-final-20260910"
m["scope"] = (
    "V4 knowledge base in Phase 16 final acceptance: %d laws, %d lawVersions, %d clauses, "
    "%d requirements, %d hazards, %d links, %d evidence, and %d successions. "
    "Candidate release v4-candidate-20260910 remains candidate-only; production is NOT switched. "
    "Composite-hazard split history remains traceable in docs/V4_HAZARD_SPLIT_TASKS.md."
    % (counts["laws"], counts["lawVersions"], counts["clauses"], counts["requirements"],
       counts["hazards"], counts["links"], counts["evidence"], counts["successions"])
)
io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(
    json.dumps(m, ensure_ascii=False, indent=1) + "\n")
print("manifest synced")
