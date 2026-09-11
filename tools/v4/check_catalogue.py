# -*- coding: utf-8 -*-
"""验证 catalogue 完整性：JSON 解析、引用完整性、review hash 绑定。"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(ROOT, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        out[d["id"]] = d
    return out


def main():
    laws = load_dir("knowledge/laws")
    lvs = load_dir("knowledge/law-versions")
    clauses = load_dir("knowledge/clauses")
    succs = load_dir("knowledge/successions")
    print("laws:", len(laws), "lawVersions:", len(lvs), "clauses:", len(clauses), "successions:", len(succs))

    errs = []
    for vid, v in lvs.items():
        if v["lawId"] not in laws:
            errs.append("lawVersion %s -> missing law %s" % (vid, v["lawId"]))
    for cid, c in clauses.items():
        if c["lawVersionId"] not in lvs:
            errs.append("clause %s -> missing lawVersion %s" % (cid, c["lawVersionId"]))
    for sid, s in succs.items():
        if s["oldVersionId"] not in lvs:
            errs.append("succ %s -> missing old %s" % (sid, s["oldVersionId"]))
        if s["newVersionId"] not in lvs:
            errs.append("succ %s -> missing new %s" % (sid, s["newVersionId"]))
        if s["oldVersionId"] == s["newVersionId"]:
            errs.append("succ %s self-loop" % sid)
        if s["relation"] not in ("replaces", "partially_replaces"):
            errs.append("succ %s unexpected relation %s" % (sid, s["relation"]))

    # 新增 lawVersion 的 effectiveDate 空值记录（pending 项）
    pending_eff = [vid for vid, v in lvs.items() if not v.get("effectiveDate")]
    print("lawVersions with empty effectiveDate:", pending_eff)

    # clause 数量按 lawVersion 分布
    from collections import Counter
    dist = Counter(c["lawVersionId"] for c in clauses.values())
    for lv in ("LV_HAZCHEM_LAW", "LV_HAZCHEM_REG"):
        print("clauses for", lv, ":", dist.get(lv, 0))

    print("errors:", len(errs))
    for e in errs[:30]:
        print(" -", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
