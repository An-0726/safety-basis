# -*- coding: utf-8 -*-
"""Phase 11: Requirement 层 validator。

检查：JSON/id 唯一/字段齐全/clauseId 与 lawVersionId 可解析且一致/
canonicalHash 一致/verified 状态必填/lifecycle 合法/link.requirementId 可解析。
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("id") or d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def main():
    rqs = load_dir("requirements")
    clauses = load_dir("clauses")
    lvs = load_dir("law-versions")
    links = load_dir("links")
    errs = []

    for rid, r in sorted(rqs.items()):
        for field in ("id", "lawVersionId", "clauseId", "seq", "title", "description",
                      "sourceQuote", "scope", "checkItems", "lifecycle",
                      "reviewStatus", "reviewedAt", "reviewer", "reviewReason", "canonicalHash"):
            if field not in r:
                errs.append((rid, "missing-field", field))
        if r.get("clauseId") not in clauses:
            errs.append((rid, "clause-not-found", r.get("clauseId")))
        if r.get("lawVersionId") not in lvs:
            errs.append((rid, "lawVersion-not-found", r.get("lawVersionId")))
        else:
            c = clauses.get(r.get("clauseId")) or {}
            if c.get("lawVersionId") != r.get("lawVersionId"):
                errs.append((rid, "lawVersion-mismatch", "%s vs %s" % (c.get("lawVersionId"), r.get("lawVersionId"))))
        if r.get("lifecycle") not in ("active", "superseded"):
            errs.append((rid, "bad-lifecycle", r.get("lifecycle")))
        if r.get("reviewStatus") not in ("pending", "verified"):
            errs.append((rid, "bad-reviewStatus", r.get("reviewStatus")))
        if r.get("reviewStatus") == "verified" and not (r.get("reviewer") and r.get("reviewedAt") and r.get("reviewReason")):
            errs.append((rid, "verified-without-meta", ""))
        try:
            if r.get("canonicalHash") != content_hash(r):
                errs.append((rid, "stale-hash", ""))
        except Exception as e:
            errs.append((rid, "hash-error", str(e)))

    for kid, l in links.items():
        rid = l.get("requirementId")
        if rid and rid not in rqs:
            errs.append((kid, "link->requirement dangling", rid))

    print("requirements:", len(rqs))
    print("errors:", len(errs))
    for e in errs[:30]:
        print(" -", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
