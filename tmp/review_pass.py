# -*- coding: utf-8 -*-
"""审题修正 pass（v2）：产出审定清单 tmp/titles_fixed.txt。"""
import io
import re

lines = io.open("tmp/titles_all.txt", encoding="utf-8").read().splitlines()
REG = re.compile(r"(监督部门|监督管理部门|消防救援机构|人民政府|主管部门|市场监管|公安部门|应急管理部门|监管部门|监察机构|行政部门|城乡建设行政|卫生行政部门)")
CUT_MARKS = ["：（一", "： （一", "：—", "——", "：a)", "：a、", "：(", ":(一)", "：1)", "：(一)", "：1、"]
DROP_EXPLICIT = {31, 39, 95, 97, 104, 125, 145, 251, 33, 374, 397, 418, 612, 628, 676, 692, 809, 822}
COMPOUNDS = ("适应", "应急", "应该", "供应", "相应", "反应")


def modal_resid(t):
    for i, ch in enumerate(t):
        if ch == "应":
            if t[i:i + 2] in COMPOUNDS or t[i - 1:i + 1] in COMPOUNDS:
                continue
            return True
    return False


def fix_title(t):
    t = t.strip()
    for mark in CUT_MARKS:
        i = t.find(mark)
        if i > 12:
            t = t[:i]
    t = t.strip("，, ；;：: ")
    for tail in ("的等", "之一的等", "之一的，等", "形等的等"):
        if t.endswith(tail):
            t = t[:-1]
    return t


keep, fixed, dropped = [], [], []
for ln in lines:
    n, cid, t = ln.split("|", 2)
    n = int(n)
    t = t.strip()
    if n in DROP_EXPLICIT:
        dropped.append((n, "监管职责/罚则/定义/公式/碎片", t[:36]))
        continue
    t2 = fix_title(t)
    if len(t2) < 10 or "——" in t2 or "（一）" in t2 or modal_resid(t2) or REG.search(t2):
        dropped.append((n, "规则淘汰", (t2 or t)[:36]))
        continue
    if t2 != t:
        fixed.append(n)
    keep.append((n, cid, t2))

# 捡回被长度规则误杀的 236（检修作业未进行审批）
allmap = {l.split("|", 2)[0]: l.split("|", 2) for l in lines}
if "236" in allmap and not any(k[0] == 236 for k in keep):
    keep.append((236, allmap["236"][1], allmap["236"][2]))

keep.sort(key=lambda x: x[0])
with io.open("tmp/titles_fixed.txt", "w", encoding="utf-8", newline="\n") as f:
    for n, cid, t in keep:
        f.write(f"{n}|{cid}|{t}\n")
print("keep:", len(keep), "| modified:", len(fixed), "| dropped:", len(dropped))
