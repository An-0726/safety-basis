# -*- coding: utf-8 -*-
"""Phase 16: V4 整合 Validator（总入口）。

按顺序运行并汇总：
1. check_manifest / check_commerce_dispositions - 库存/生命周期及44候选处置绑定
2. check_catalogue   - schema / 引用完整性（law-lawVersion-clause-succession）
3. check_requirements- Requirement 层（ref / hash / review meta / lifecycle）
4. check_field_profiles - governed profile schema / 引用；不要求全量分类或审批完成
5. check_major_criteria - controlled catalog schema / 引用；不自动核准条款或全量覆盖
6. check_major_criteria_references - reference-only metadata/short-topic结构，不核准全文
7. check_major_criteria_directory - 通用文件题录、null日期说明及主补充关系
8. check_major_criteria_reading - 独立原文查阅结构，不授予当前依据资格
9. check_review_binding - review content hash 绑定
10. scan_evidence_exact - review evidence 与 clause 法规匹配
11. scan_quality      - 质量扫描（duplicates / dangling / stale refs / obligation patterns）
12. version_impact    - 版本影响（只报告，不阻塞）

退出码：0=全部通过；1=存在阻断性错误。

阻断集合 = manifest / catalogue / requirements / field_profiles / major_criteria / major_criteria_references / major_criteria_directory / review_binding / evidence_exact：
- 前八个是结构性错误；field_profiles / major_criteria / major_criteria_references 不把缺失/未审核覆盖率当作完成或全局阻断；
- scan_evidence_exact 会返回非零（review 引用的证据与其条款所属法规不匹配），
  属于数据错误，此前被排除在阻断之外，导致它失败时 validate_all 仍报
  "BLOCKING failures: none" 且退出码 0 —— 与 CI 中 gate_v4 的 EVIDENCE 阶段判定不一致。
scan_quality / version_impact 是候选清单型报告，只输出不阻断。
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
TOOLS = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("check_manifest", "check_manifest_inventory.py"),
    ("check_commerce_dispositions", "check_commerce_candidate_dispositions.py"),
    ("check_catalogue", "check_catalogue.py"),
    ("check_requirements", "check_requirements.py"),
    ("check_field_profiles", "check_field_profiles.py"),
    ("check_major_criteria", "check_major_criteria.py"),
    ("check_major_criteria_references", "check_major_criteria_references.py"),
    ("check_major_criteria_directory", "check_major_criteria_directory.py"),
    ("check_major_criteria_reading", "check_major_criteria_reading.py"),
    ("check_review_binding", "check_review_binding.py"),
    ("scan_evidence_exact", "scan_evidence_exact.py"),
    ("scan_quality", "scan_quality_v4.py"),
    ("version_impact", "version_impact.py"),
]
BLOCKING = {"check_manifest", "check_commerce_dispositions", "check_catalogue", "check_requirements", "check_field_profiles", "check_major_criteria", "check_major_criteria_references", "check_major_criteria_directory", "check_major_criteria_reading", "check_review_binding", "scan_evidence_exact"}


def main():
    results = {}
    for name, script in STEPS:
        print("\n===== %s (%s) =====" % (name, script))
        p = subprocess.run([sys.executable, os.path.join(TOOLS, script)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (p.stdout or "").strip()
        # 只显示关键行
        for line in out.splitlines():
            if any(k in line for k in ("errors:", "stale", "unbound", "MISMATCHED", "TOTAL", "requirements:", "reviews total",
                                       "dangling", "laws:", "hazards:", "clauses:", "successions:", "candidate")):
                print("  ", line)
        if p.returncode != 0:
            print("   [rc=%d]" % p.returncode)
        results[name] = p.returncode

    blocked = [n for n, rc in results.items() if n in BLOCKING and rc != 0]
    print("\n===== SUMMARY =====")
    for n, rc in results.items():
        print("  %-22s %s" % (n, "PASS" if rc == 0 else "FAIL(%d)" % rc))
    print("BLOCKING failures:", blocked if blocked else "none")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
