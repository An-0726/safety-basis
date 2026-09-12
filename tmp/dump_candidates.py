# -*- coding: utf-8 -*-
"""按 from-file 应用路径的同一枚举导出候选清单（保证行号对齐）。"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))

# 与 generate_hazards_from_clauses.main() 完全相同的条款装载方式
clauses = {}
for f in os.listdir(os.path.join(KNOW, "clauses")):
    d = json.load(io.open(os.path.join(KNOW, "clauses", f), encoding="utf-8"))
    clauses[d["id"]] = d

import importlib.util
gspec = importlib.util.spec_from_file_location(
    "gen", os.path.join(ROOT, "tools", "v4", "generate_hazards_from_clauses.py"))
gen = importlib.util.module_from_spec(gspec)
gspec.loader.exec_module(gen)

# 应用代码路径：auto_specs_for(clauses, exclude_clause_ids=set())
all_specs = gen.auto_specs_for(clauses, exclude_clause_ids=set())
with io.open(os.path.join(ROOT, "tmp", "candidates_full.txt"), "w", encoding="utf-8", newline="\n") as f:
    for i, s in enumerate(all_specs, 1):
        f.write(f"{i}|{s['clause']}|{s['title']}\n")
print("candidates (exclude=set, same as apply path):", len(all_specs))

# r22 基线里已被挂接的条款（对这些再做自动反转=重复覆盖，剔除出审校池）
linked = set()
for f in os.listdir(os.path.join(KNOW, "links")):
    d = json.load(io.open(os.path.join(KNOW, "links", f), encoding="utf-8"))
    if d.get("clauseId"):
        linked.add(d["clauseId"])
print("linked clauses in baseline:", len(linked))

pool = [(i, s) for i, s in enumerate(all_specs, 1) if s["clause"] not in linked]
with io.open(os.path.join(ROOT, "tmp", "candidates_review.txt"), "w", encoding="utf-8", newline="\n") as f:
    for i, s in pool:
        f.write(f"{i}|{s['clause']}|{s['title']}\n")
print("review pool (clause not linked):", len(pool))
