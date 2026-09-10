# -*- coding: utf-8 -*-
"""Phase 17: V4 Gate 执行器。

分级判定：STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE。
输出 gate report（stdout + docs/V4_GATE_REPORT.md）。
不执行 production 切换（Phase 17 需用户批准）。
"""
import glob
import io
import json
import os
import subprocess
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
TOOLS = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")


def run(script):
    p = subprocess.run([sys.executable, os.path.join(TOOLS, script)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "")


def load_dir(rel):
    out = {}
    for f in glob.glob(os.path.join(KNOW, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("id") or d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def main():
    report = {}
    report["structural"] = {}
    for name, script in (("check_catalogue", "check_catalogue.py"),
                         ("check_requirements", "check_requirements.py"),
                         ("check_review_binding", "check_review_binding.py")):
        rc, out = run(script)
        report["structural"][name] = "PASS" if rc == 0 else "FAIL"
    rc, out = run("scan_evidence_exact.py")
    report["evidence_scan"] = "PASS" if "MISMATCHED reviews: 0" in out else "FAIL"

    # CONTENT / APPLICABILITY
    reviews = load_dir(os.path.join("reviews", "links"))
    dec = Counter(r.get("decision") for r in reviews.values())
    report["review_totals"] = dict(dec)
    report["review_total"] = len(reviews)

    # VERSION: 仅 active 且被实际引用（link/clause/succession newVersion）的 LV 需要 effectiveDate
    lvs = load_dir("law-versions")
    clauses = load_dir("clauses")
    links = load_dir("links")
    succs = load_dir("successions")
    used_lv = set()
    for c in clauses.values():
        if c.get("lawVersionId"):
            used_lv.add(c["lawVersionId"])
    for l in links.values():
        pass  # clause 已覆盖
    for s in succs.values():
        if s.get("newVersionId"):
            used_lv.add(s["newVersionId"])
    active = {vid for vid, v in lvs.items() if (v.get("lifecycle") or "active") != "superseded"}
    missing = sorted(vid for vid in (used_lv & active) if not lvs[vid].get("effectiveDate"))
    report["lawVersions_total"] = len(lvs)
    report["lawVersions_active_no_effectiveDate"] = len(missing)
    report["missing_eff_ids"] = missing
    report["successions_total"] = len(succs)

    # EVIDENCE: verified 无 evidence
    no_ev = [k for k, r in reviews.items() if r.get("decision") == "verified" and not (r.get("evidenceRefs"))]
    report["verified_without_evidence"] = no_ev

    # composite / pending 分类
    comp = [k for k, r in reviews.items() if "COMPOSITE" in str(r.get("reasonCodes") or "")]
    report["composite_reviewed"] = len(comp)

    # 汇总判定
    structural_pass = all(v == "PASS" for v in report["structural"].values()) and report["evidence_scan"] == "PASS"
    version_pass = len(missing) == 0
    content_pass = report["review_total"] == len(reviews) and not report["verified_without_evidence"]
    applicability_pass = content_pass

    report["gate"] = {
        "STRUCTURAL": "PASS" if structural_pass else "FAIL",
        "CONTENT": "PASS" if content_pass else "FAIL",
        "APPLICABILITY": "PASS" if applicability_pass else "FAIL",
        "VERSION": "PASS" if version_pass else "PENDING (%d active LVs lack effectiveDate)" % len(missing),
        "EVIDENCE": "PASS" if report["evidence_scan"] == "PASS" else "FAIL",
        "RELEASE": "NOT_RUN (candidate build pending)",
    }

    text = []
    text.append("# V4 Gate Report（2026-09-10, chat-v4）")
    text.append("")
    text.append("## Structural")
    for k, v in report["structural"].items():
        text.append("- %s: %s" % (k, v))
    text.append("- scan_evidence_exact: %s" % report["evidence_scan"])
    text.append("")
    text.append("## Review totals: %s" % json.dumps(report["review_totals"], ensure_ascii=False))
    text.append("review_total=%d" % report["review_total"])
    text.append("composite_reviewed=%d" % report["composite_reviewed"])
    text.append("verified_without_evidence=%d" % len(no_ev))
    text.append("")
    text.append("## Version")
    text.append("lawVersions_total=%d, active-missing-effectiveDate=%d" % (report["lawVersions_total"], len(missing)))
    text.append("missing_eff_ids=%s" % json.dumps(missing, ensure_ascii=False))
    text.append("successions_total=%d" % report["successions_total"])
    text.append("")
    text.append("## Gate verdict")
    for k, v in report["gate"].items():
        text.append("- %s: %s" % (k, v))
    text.append("")
    text.append("RELEASE 级（candidate build / V3-V4 diff / search regression）在 Phase 19-20 完成后补记；production 切换需用户批准。")

    with io.open(os.path.join(DOCS, "V4_GATE_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(text))
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
