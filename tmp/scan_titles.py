# -*- coding: utf-8 -*-
"""候选标题全量机械扫描。"""
import re

lines = open("tmp/titles_all.txt", encoding="utf-8").read().splitlines()
bad_pat = re.compile(r"(未急|相适未|相未|未当|未力|未严整|未高度|未无|的的|了了|（[一二三四五六七八九十]）|^[0-9]+[）〕)]|[a-h]\)$|：$|：如$|包括：$|下列情形|下列|——)")
COMPOUNDS = ("适应", "应急", "应该", "供应", "相应", "反应")


def modal_resid(t):
    for i, ch in enumerate(t):
        if ch == "应":
            if t[i:i + 2] in COMPOUNDS or t[i - 1:i + 1] in COMPOUNDS:
                continue
            return True
    return False


issues = []
dups = {}
for ln in lines:
    n, cid, t = ln.split("|", 2)
    t = t.strip()
    if bad_pat.search(t):
        issues.append((n, "pattern", t[:52]))
    elif modal_resid(t):
        issues.append((n, "modal", t[:52]))
    dups.setdefault(t, []).append(n)
for t, ns in sorted(dups.items()):
    if len(ns) > 1:
        issues.append((ns[0], "dup×%d" % len(ns), t[:52]))
print("mechanical issues:", len(issues))
for n, k, t in issues[:50]:
    print(" ", n, k, t)
short = [l.split("|", 2)[2].strip() for l in lines if len(l.split("|", 2)[2].strip()) < 8]
print("short(<8):", len(short), short[:10])
print("total:", len(lines))
