# -*- coding: utf-8 -*-
"""生成器增加 --from-file（按人工审定清单应用）。"""
import io

p = "tools/v4/generate_hazards_from_clauses.py"
s = io.open(p, encoding="utf-8").read()

a1_old = '    ap.add_argument("--auto", action="store_true", help="对 SPECS 未覆盖的条款做机械反转（生成后需人工审题）")'
a1_new = a1_old + '\n    ap.add_argument("--from-file", dest="from_file", help="按人工审定清单（N|clause|title）应用，未列入的候选丢弃")'
assert a1_old in s
s = s.replace(a1_old, a1_new, 1)

a2_old = '''    specs = list(SPECS)
    if args.auto:'''
a2_new = '''    specs = list(SPECS)
    if args.from_file:
        all_specs = auto_specs_for(clauses, exclude_clause_ids=set())
        fixed_lines = [l.split("|", 2) for l in io.open(args.from_file, encoding="utf-8").read().splitlines() if l.strip()]
        keep_specs = []
        for ln in fixed_lines:
            n = int(ln[0])
            if 1 <= n <= len(all_specs):
                spec = dict(all_specs[n - 1])
                spec["title"] = ln[2]
                keep_specs.append(spec)
        specs = list(SPECS) + keep_specs
        print(f"from-file specs: {len(keep_specs)} (of {len(all_specs)} candidates)")
    elif args.auto:'''
assert a2_old in s
s = s.replace(a2_old, a2_new, 1)

a3_old = '''    for spec in specs:
        if spec.get("auto"):
            cid = spec["clause"]'''
a3_new = '''    for spec in specs:
        if spec.get("auto") or args.from_file:
            spec = dict(spec, auto=True)
            cid = spec["clause"]'''
assert a3_old in s
s = s.replace(a3_old, a3_new, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched --from-file")
