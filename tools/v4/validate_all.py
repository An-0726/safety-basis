# -*- coding: utf-8 -*-
"""Phase 16: V4 整合 Validator（总入口）。

按顺序运行并汇总：
1. check_catalogue   - schema / 引用完整性（law-lawVersion-clause-succession）
2. check_requirements- Requirement 层（ref / hash / review meta / lifecycle）
3. check_review_binding - review content hash 绑定
4. scan_evidence_exact - review evidence 与 clause 法规匹配
5. scan_quality      - 质量扫描（duplicates / dangling / stale refs / obligation patterns）
6. version_impact    - 版本影响（只报告，不阻塞）

退出码：0=全部通过；1=存在结构性错误（1-3 任一失败）。
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
TOOLS = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("check_catalogue", "check_catalogue.py"),
    ("check_requirements", "check_requirements.py"),
    ("check_review_binding", "check_review_binding.py"),
    ("scan_evidence_exact", "scan_evidence_exact.py"),
    ("scan_quality", "scan_quality_v4.py"),
    ("version_impact", "version_impact.py"),
]
BLOCKING = {"check_catalogue", "check_requirements", "check_review_binding"}


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
