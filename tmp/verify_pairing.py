# -*- coding: utf-8 -*-
"""全量配对验证：844 条应用的 hazard/link/desc 必须与同一枚举的 spec 严格一致。"""
import importlib.util
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")

clauses = {}
for f in os.listdir(os.path.join(KNOW, "clauses")):
    d = json.load(io.open(os.path.join(KNOW, "clauses", f), encoding="utf-8"))
    clauses[d["id"]] = d

gspec = importlib.util.spec_from_file_location(
    "gen", os.path.join(ROOT, "tools", "v4", "generate_hazards_from_clauses.py"))
gen = importlib.util.module_from_spec(gspec)
gspec.loader.exec_module(gen)
all_specs = gen.auto_specs_for(clauses, exclude_clause_ids=set())

ok = bad = 0
problems = []
for ln in io.open(os.path.join(ROOT, "tmp", "apply_r23.txt"), encoding="utf-8").read().splitlines():
    n, cid, title = ln.split("|", 2)
    spec = all_specs[int(n) - 1]
    if spec["clause"] != cid:
        problems.append(f"N={n}: 枚举错位 spec={spec['clause']} vs list={cid}")
        bad += 1
        continue
    if cid.startswith("C_GBT47236_"):
        hid = "H_GBT47236_" + cid[len("C_GBT47236_"):] + "_" + str(spec.get("seq", 1))
        kid = "K_GBT47236_" + cid[len("C_GBT47236_"):] + "_" + str(spec.get("seq", 1))
    else:
        hid = "H" + cid[1:] + "_" + str(spec.get("seq", 1))
        kid = "K" + cid[1:] + "_" + str(spec.get("seq", 1))
    hp = os.path.join(KNOW, "hazards", hid + ".json")
    lp = os.path.join(KNOW, "links", kid + ".json")
    if not os.path.exists(hp) or not os.path.exists(lp):
        problems.append(f"N={n}: 缺文件 {hid}/{kid}")
        bad += 1
        continue
    h = json.load(io.open(hp, encoding="utf-8"))
    k = json.load(io.open(lp, encoding="utf-8"))
    errs = []
    if h["title"] != title:
        errs.append(f"标题不符 disk={h['title'][:30]!r}")
    if h["description"] != spec["desc"]:
        errs.append(f"描述与条款不符 disk={h['description'][:30]!r}")
    if k["clauseId"] != cid:
        errs.append(f"链接条款不符 {k['clauseId']}")
    if not os.path.exists(os.path.join(KNOW, "reviews", "hazards", hid + ".json")):
        errs.append("缺审阅记录")
    if errs:
        problems.append(f"N={n} {hid}: " + "; ".join(errs))
        bad += 1
    else:
        ok += 1

print(f"pairing verified: ok={ok} bad={bad}")
for p in problems[:10]:
    print("  !", p)
