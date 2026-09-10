# -*- coding: utf-8 -*-
"""审核内容绑定批量刷新工具（替代一次性重绑脚本）。

用途：修改 knowledge 实体后，自动发现并（可选）修复所有失效的内容绑定。

覆盖的绑定关系：
- law / law_version / clause / hazard / link 的 review.reviewedContentHash
  必须等于对应实体当前的 canonical 内容哈希；
- link review 的 contextHashes.hazard / contextHashes.clause
  必须等于其目标 hazard / clause 当前的内容哈希。

用法：
    python tools/v4/rebind.py            # 只报告，不修改（默认）
    python tools/v4/rebind.py --fix      # 自动把失效绑定刷新为当前值
    python tools/v4/rebind.py --json     # 以 JSON 输出报告

退出码：0 = 无失效绑定；2 = 存在失效绑定（--fix 修复后仍以 0 退出并列出修复项）。

说明：本工具只改哈希值，不改 decision / reason / reasonCodes 等审核判断字段；
若某条引用的实体不存在（外键断裂），只报告、不猜测。
"""
import argparse
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")

# review 目录 -> 实体目录
REVIEW_TO_ENTITY = {
    "laws": "laws",
    "law-versions": "law-versions",
    "clauses": "clauses",
    "hazards": "hazards",
    "links": "links",
    "requirements": "requirements",
}


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        key = d.get("id") or os.path.splitext(os.path.basename(f))[0]
        out[key] = (d, f)
    return out


def load_reviews(rel):
    out = []
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        out.append((d, f))
    return out


def patch_hash(path, old, new):
    """只替换文件中的哈希字符串，完全保留原缩进与行尾，避免产生格式噪音。"""
    with open(path, "rb") as f:
        raw = f.read().decode("utf-8")
    if old is None or raw.count(old) != 1:
        return False
    with open(path, "wb") as f:
        f.write(raw.replace(old, new).encode("utf-8"))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="自动刷新失效绑定")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    entities = {k: load_dir(v) for k, v in REVIEW_TO_ENTITY.items()}
    issues = []
    fixed = []

    for rev_dir, ent_dir in REVIEW_TO_ENTITY.items():
        for rev, path in load_reviews(os.path.join("reviews", rev_dir)):
            eid = rev.get("entityId")
            if not eid:
                issues.append({"file": path, "kind": "review_without_entityId"})
                continue
            ent = entities[ent_dir].get(eid)
            if not ent:
                issues.append({"file": path, "entityId": eid, "kind": "missing_entity"})
                continue
            obj, _ = ent
            cur = content_hash(obj)

            if rev.get("reviewedContentHash") != cur:
                old_val = rev.get("reviewedContentHash")
                issues.append({"file": path, "entityId": eid, "kind": "stale_content_hash",
                               "was": old_val, "now": cur})
                if args.fix and patch_hash(path, old_val, cur):
                    fixed.append({"file": path, "entityId": eid, "kind": "stale_content_hash"})

            if rev_dir == "links":
                ctx = rev.get("contextHashes") or {}
                link = obj
                hz = entities["hazards"].get(link.get("hazardId"))
                cl = entities["clauses"].get(link.get("clauseId"))
                if not hz:
                    issues.append({"file": path, "entityId": eid, "kind": "missing_hazard",
                                   "ref": link.get("hazardId")})
                elif ctx.get("hazard") != content_hash(hz[0]):
                    cur_h = content_hash(hz[0])
                    issues.append({"file": path, "entityId": eid, "kind": "stale_hazard_context",
                                   "was": ctx.get("hazard"), "now": cur_h})
                    if args.fix and patch_hash(path, ctx.get("hazard"), cur_h):
                        fixed.append({"file": path, "entityId": eid, "kind": "stale_hazard_context"})
                if not cl:
                    issues.append({"file": path, "entityId": eid, "kind": "missing_clause",
                                   "ref": link.get("clauseId")})
                elif ctx.get("clause") != content_hash(cl[0]):
                    cur_c = content_hash(cl[0])
                    issues.append({"file": path, "entityId": eid, "kind": "stale_clause_context",
                                   "was": ctx.get("clause"), "now": cur_c})
                    if args.fix and patch_hash(path, ctx.get("clause"), cur_c):
                        fixed.append({"file": path, "entityId": eid, "kind": "stale_clause_context"})

    # requirement 实体自带 reviewStatus；标记 verified 却没有 sidecar 属于审核留痕缺失
    req_rev_ids = {rev.get("entityId") for rev, _ in load_reviews(os.path.join("reviews", "requirements"))}
    for rid, (obj, path) in entities["requirements"].items():
        if obj.get("reviewStatus") == "verified" and rid not in req_rev_ids:
            issues.append({"file": path, "entityId": rid, "kind": "verified_without_sidecar"})

    fixed_keys = {(f["file"], f["kind"]) for f in fixed}
    unfixed = [it for it in issues if (it["file"], it["kind"]) not in fixed_keys]
    report = {
        "checked": {k: len(v) for k, v in entities.items()},
        "issues": issues,
        "issueCount": len(issues),
        "fixed": fixed,
        "fixedCount": len(fixed),
        "unfixedCount": len(unfixed),
        "fixMode": bool(args.fix),
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("checked entities:", report["checked"])
        if not issues:
            print("no stale bindings found.")
        else:
            print("stale/abnormal bindings: %d" % len(issues))
            for it in issues[:60]:
                print("  %-22s %-24s %s" % (it.get("kind"), it.get("entityId"), os.path.relpath(it["file"], ROOT)))
            if len(issues) > 60:
                print("  ... and %d more" % (len(issues) - 60))
            if args.fix:
                print("fixed: %d, still needing manual attention: %d" % (len(fixed), len(unfixed)))
            else:
                print("re-run with --fix to refresh them.")
    return 0 if not unfixed else 2


if __name__ == "__main__":
    sys.exit(main())
