# -*- coding: utf-8 -*-
"""校验 5 份审校裁决并合成 --from-file 应用清单。"""
import io
import re
import sys

ROOT = r"D:\ESH\ESH_Codex\work\safety-basis"

# 候选全集（1449 空间）：N -> (clause, title)；标题内嵌换行产生的断行并回上一行
full = {}
broken = []
for ln in io.open(ROOT + r"\tmp\candidates_full.txt", encoding="utf-8").read().splitlines():
    if ln.count("|") < 2:
        if full:
            last = max(full)
            cid, t = full[last]
            full[last] = (cid, t + ln.strip())  # 不影响裁决：断行候选均不在审校池
            broken.append(last)
        continue
    n, cid, t = ln.split("|", 2)
    full[int(n)] = (cid, t.strip())
if broken:
    print("joined continuation lines after N:", broken)

# 审校池输入：校验输出与输入逐行对齐
BAD = re.compile(r"(未急|相适未|相未|未无|（[一二三四五六七八九十]）|———|——|：a\)|：1\)|： （一)")
stats = {"KEEP": 0, "FIX": 0, "DROP": 0}
apply_lines, warns, seen = [], [], set()

for c in range(1, 6):
    inp = io.open(ROOT + rf"\tmp\review2_in_{c}.txt", encoding="utf-8").read().splitlines()
    out = io.open(ROOT + rf"\tmp\review2_out_{c}.txt", encoding="utf-8").read().splitlines()
    if len(inp) != len(out):
        sys.exit(f"FATAL chunk {c}: input {len(inp)} vs output {len(out)} 行数不一致")
    for k, (il, ol) in enumerate(zip(inp, out), 1):
        n_in = int(il.split("|", 1)[0])
        parts = ol.split("|", 2)
        if len(parts) != 3:
            sys.exit(f"FATAL chunk {c} 行{k}: 竖线数不对: {ol[:60]!r}")
        n, verdict, content = int(parts[0]), parts[1], parts[2].strip()
        if n != n_in:
            sys.exit(f"FATAL chunk {c} 行{k}: N 错位 out={n} in={n_in}")
        if n in seen:
            sys.exit(f"FATAL: N={n} 重复裁决")
        seen.add(n)
        if verdict not in stats:
            sys.exit(f"FATAL chunk {c} 行{k}: 非法裁决 {verdict!r}")
        stats[verdict] += 1
        if verdict == "KEEP":
            cid, t = full[n]
            if BAD.search(t):
                warns.append(f"KEEP残留 N={n}: {t[:50]}")
            apply_lines.append(f"{n}|{cid}|{t}")
        elif verdict == "FIX":
            t = content.strip()
            if not (8 <= len(t) <= 62):
                warns.append(f"FIX长度{len(t)} N={n}: {t[:40]}")
            if BAD.search(t):
                warns.append(f"FIX残留 N={n}: {t[:50]}")
            cid = full[n][0]
            apply_lines.append(f"{n}|{cid}|{t}")
        # DROP: 不进应用清单

pool_n = {int(l.split("|", 1)[0]) for l in
          io.open(ROOT + r"\tmp\candidates_review.txt", encoding="utf-8").read().splitlines()}
missing = pool_n - seen
extra = seen - pool_n

with io.open(ROOT + r"\tmp\apply_r23.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(apply_lines) + "\n")

print("verdicts:", stats, "| apply lines:", len(apply_lines))
print("pool coverage: missing", len(missing), sorted(missing)[:8], "| extra", len(extra), sorted(extra)[:8])
print("warnings:", len(warns))
for w in warns[:25]:
    print("  W:", w)
