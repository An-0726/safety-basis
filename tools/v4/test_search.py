# -*- coding: utf-8 -*-
"""Phase 18: 搜索回归测试（对 v4-candidate search-index 运行）。

与 js/search.js 相同评分算法（Python 复刻）：
title 全等 120 / title 包含 80 / aliases 70 / keywords 60 / lawNames 40。
覆盖：口语、专业术语、法规名称、标准号、隐患别名、消防、电气、危化、
特种设备、机械、粉尘、有限空间典型场景。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
REL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "source", "releases", "v4-candidate-20260910")


def _norm_std(s):
    import re
    return re.sub(r"[\s\-—–/]", "", str(s)).lower()


def load():
    with io.open(os.path.join(REL, "data", "search-index.json"), encoding="utf-8") as fh:
        return json.load(fh)


def score(q, rec):
    qs = q.strip().lower()
    if not qs:
        return 0
    title = (rec.get("title") or "").lower()
    aliases = " ".join(rec.get("aliases") or []).lower()
    keywords = " ".join(rec.get("keywords") or []).lower()
    law = " ".join(rec.get("lawNames") or []).lower()
    stds_norm = [_norm_std(s) for s in (rec.get("stdNumbers") or [])]
    qs_norm = _norm_std(qs)
    s = 0
    if title == qs:
        s += 120
    if qs in title:
        s += 80
    if qs in aliases:
        s += 70
    if qs in keywords:
        s += 60
    if qs in law:
        s += 40
    if any(std == qs_norm or std.startswith(qs_norm) for std in stds_norm):
        s += 60
    return s


def search(idx, q):
    scored = [(score(q, r), r) for r in idx]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [r for _, r in scored]


# (query, 期望至少命中, 说明)
CASES = [
    ("灭火器", 3, "消防-口语"),
    ("消火栓", 1, "消防-专业"),
    ("配电柜", 1, "电气"),
    ("防爆", 3, "电气-防爆"),
    ("危化品", 3, "危化-口语"),
    ("危险化学品", 5, "危化-专业"),
    ("易燃", 1, "危化-属性"),
    ("压力容器", 1, "特种设备"),
    ("行车", 1, "特种设备-起重"),
    ("防护罩", 2, "机械"),
    ("冲压", 1, "机械-冲压"),
    ("粉尘", 3, "粉尘"),
    ("除尘", 2, "粉尘-除尘"),
    ("有限空间", 1, "有限空间"),
    ("安全标志", 2, "标志"),
    ("GB 2894", 1, "标准号"),
    ("临时线", 1, "电气-口语"),
    ("气瓶", 2, "特种设备-气瓶"),
    ("仓库", 3, "场所"),
    ("危废", 2, "危废"),
]

FAILED = []
INDEX = load()
for q, min_hits, label in CASES:
    hits = search(INDEX, q)
    top = hits[0]["title"][:40] if hits else "(none)"
    ok = len(hits) >= min_hits
    if not ok:
        FAILED.append((q, label, len(hits), min_hits))
    print("%-3s %-10s %-12s hits=%-3d top=%s" % ("OK" if ok else "!!", q, label, len(hits), top))

print("\nTOTAL: %d cases, failed: %d" % (len(CASES), len(FAILED)))
for f in FAILED:
    print("  FAIL %s (%s): %d < %d" % f)
sys.exit(1 if FAILED else 0)
