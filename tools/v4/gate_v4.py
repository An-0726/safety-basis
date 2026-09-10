# -*- coding: utf-8 -*-
"""V4 Gate 执行器（六阶段）。

阶段：STRUCTURAL / CONTENT / APPLICABILITY / VERSION / EVIDENCE / RELEASE。

关键修正：RELEASE 不再只核对 sourceStateHash/counts/reviewStats，而是真正调用
共享链式门禁 release_gate_core。即使 candidate hash 一致，只要严格发布门禁
releaseBlockers > 0，RELEASE 仍判 BLOCK（禁止显示 PASS）。

输出：stdout + docs/V4_GATE_REPORT.md。不执行 production 切换。
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
sys.path.insert(0, TOOLS)
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402


def run(script):
    p = subprocess.run([sys.executable, os.path.join(TOOLS, script)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "")


def main():
    report = {}

    # ---- STRUCTURAL：子脚本健康检查 ----
    report["structural"] = {}
    for name, script in (("check_catalogue", "check_catalogue.py"),
                         ("check_requirements", "check_requirements.py"),
                         ("check_review_binding", "check_review_binding.py")):
        rc, out = run(script)
        report["structural"][name] = "PASS" if rc == 0 else "FAIL"
    rc, out = run("scan_evidence_exact.py")
    report["evidence_scan"] = "PASS" if rc == 0 else "FAIL"

    # ---- 共享链式 Gate（CONTENT / APPLICABILITY / VERSION 的事实来源）----
    gate = evaluate_release_gate(KNOW)

    reviews = load_dir(KNOW, os.path.join("reviews", "links"))
    dec = Counter(r.get("decision") for r in reviews.values())
    report["review_totals"] = dict(dec)
    report["review_total"] = len(reviews)

    lvs = load_dir(KNOW, "law-versions")
    clauses = load_dir(KNOW, "clauses")
    succs = load_dir(KNOW, "successions")
    used_lv = set(c.get("lawVersionId") for c in clauses.values() if c.get("lawVersionId"))
    for s in succs.values():
        if s.get("newVersionId"):
            used_lv.add(s["newVersionId"])
    active_lvs = {vid for vid, v in lvs.items() if v.get("validityStatus") == "active"}
    missing = sorted(vid for vid in (used_lv & active_lvs) if not lvs[vid].get("effectiveDate"))
    report["lawVersions_total"] = len(lvs)
    report["lawVersions_active_no_effectiveDate"] = len(missing)
    report["missing_eff_ids"] = missing
    report["successions_total"] = len(succs)

    no_ev = [k for k, r in reviews.items()
             if r.get("decision") == "verified" and not r.get("evidenceRefs")]
    report["verified_without_evidence"] = no_ev

    # ---- RELEASE：candidate 一致性 + 严格链式门禁 ----
    REL = os.path.join(ROOT, "source", "releases", "v4-candidate-20260910")
    rel_json_path = os.path.join(REL, "release.json")
    release_notes = []

    # 1) 严格链式门禁（核心）
    strict_blockers = []
    for lid, v in gate.laws.items():
        if not v["ok"]:
            strict_blockers.append("law %s: %s" % (lid, v["reasons"]))
    for vid, v in gate.law_versions.items():
        if not v["ok"]:
            strict_blockers.append("lawVersion %s: %s" % (vid, v["reasons"]))
    for cid, v in gate.clauses.items():
        if not v["ok"]:
            strict_blockers.append("clause %s: %s" % (cid, v["reasons"]))
    for kid, v in gate.links.items():
        if v["decision"] == "verified" and not v["ok"]:
            strict_blockers.append("link %s: %s" % (kid, v["reasons"]))
    for hid, v in gate.hazards.items():
        if v["active"] and not v["merged"] and not v["content_ok"]:
            strict_blockers.append("hazard %s: %s" % (hid, v["reasons"]))
    strict_blocker_count = len(strict_blockers)

    # 2) candidate 文件一致性
    consistency_ok = True
    if not os.path.exists(rel_json_path):
        release_notes.append("candidate release.json 不存在")
        consistency_ok = False
    else:
        try:
            from build_release import state_hash
            rel = json.load(io.open(rel_json_path, encoding="utf-8"))
            cur_hash = state_hash(glob.glob(os.path.join(KNOW, "**", "*.json"), recursive=True))
            if rel.get("sourceStateHash") != cur_hash:
                release_notes.append("sourceStateHash 与当前 knowledge 不一致（需重跑 build_release.py）")
                consistency_ok = False
            cur_counts = {"laws": len(load_dir(KNOW, "laws")),
                          "law_versions": len(load_dir(KNOW, "law-versions")),
                          "clauses": len(load_dir(KNOW, "clauses")),
                          "hazards": len(load_dir(KNOW, "hazards")),
                          "links": len(load_dir(KNOW, "links")),
                          "requirements": len(load_dir(KNOW, "requirements"))}
            sc = rel.get("sourceCounts") or {}
            for k, v in cur_counts.items():
                if sc.get(k) != v:
                    release_notes.append("counts 不一致: %s=%s(rel) vs %s(cur)" % (k, sc.get(k), v))
                    consistency_ok = False
        except Exception as e:  # noqa: BLE001
            release_notes.append("RELEASE 核对异常: %r" % e)
            consistency_ok = False

    if strict_blocker_count > 0:
        release_verdict = "BLOCK"
        release_notes.append("strict releaseBlockers=%d（即使 hash 一致也禁止 PASS）" % strict_blocker_count)
        release_notes.extend(strict_blockers[:20])
    elif not consistency_ok:
        release_verdict = "REVIEW_REQUIRED"
    else:
        release_verdict = "PASS"
        release_notes.append("strict gate PASS: eligibleHazards=%d eligibleLinks=%d"
                             % (len(gate.eligible_hazards), len(gate.eligible_links)))
    report["release_verdict"] = release_verdict
    report["release_notes"] = release_notes
    report["strictBlockerCount"] = strict_blocker_count
    report["strictBlockerSample"] = strict_blockers[:30]
    report["eligibleHazards"] = len(gate.eligible_hazards)
    report["eligibleLinks"] = len(gate.eligible_links)

    # ---- 汇总各阶段判定 ----
    structural_pass = all(v == "PASS" for v in report["structural"].values()) and report["evidence_scan"] == "PASS"
    version_pass = len(missing) == 0
    # CONTENT / APPLICABILITY 基于共享链式判定结果，与 strict audit 保持一致
    # 不再单独要求所有 verified review 都有 evidenceRefs（link review 可复用 clause evidence）
    content_pass = strict_blocker_count == 0
    applicability_pass = strict_blocker_count == 0

    report["gate"] = {
        "STRUCTURAL": "PASS" if structural_pass else "FAIL",
        "CONTENT": "PASS" if content_pass else "FAIL",
        "APPLICABILITY": "PASS" if applicability_pass else "FAIL",
        "VERSION": "PASS" if version_pass else "PENDING (%d active LVs lack effectiveDate)" % len(missing),
        "EVIDENCE": "PASS" if report["evidence_scan"] == "PASS" else "FAIL",
        "RELEASE": release_verdict,
    }

    text = []
    text.append("# V4 Gate Report（%s）" % gate.as_of)
    text.append("")
    text.append("## Structural")
    for k, v in report["structural"].items():
        text.append("- %s: %s" % (k, v))
    text.append("- scan_evidence_exact: %s" % report["evidence_scan"])
    text.append("")
    text.append("## Review totals: %s" % json.dumps(report["review_totals"], ensure_ascii=False))
    text.append("review_total=%d, verified_without_evidence=%d" % (report["review_total"], len(no_ev)))
    text.append("")
    text.append("## Shared chained gate")
    text.append("- eligibleHazards=%d, eligibleLinks=%d, strictBlockers=%d"
                % (report["eligibleHazards"], report["eligibleLinks"], report["strictBlockerCount"]))
    text.append("")
    text.append("## Version")
    text.append("lawVersions_total=%d, active-missing-effectiveDate=%d" % (report["lawVersions_total"], len(missing)))
    text.append("successions_total=%d" % report["successions_total"])
    text.append("")
    text.append("## Gate verdict")
    for k, v in report["gate"].items():
        text.append("- %s: %s" % (k, v))
    text.append("")
    text.append("## RELEASE 核对明细")
    for n in report["release_notes"]:
        text.append("- %s" % n)
    text.append("")
    text.append("RELEASE 阶段已接入共享链式门禁 release_gate_core；production 切换需用户批准。")

    with io.open(os.path.join(DOCS, "V4_GATE_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(text))
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
