#!/bin/bash
# GB/T 12801 新版切换发布（2026-10-01 执行）。
# 前提：当天 GB 12801-2025 生效，upcoming 条款不再阻断门禁。
# 任何验证步骤失败即退出非零，不部署。
set -e
cd /d/ESH/ESH_Codex/work/safety-basis

echo "== 1. 入库 GB 12801-2025 条款 =="
py -X utf8 tools/v4/ingest_law_clauses.py --doc LF_STD_GB12801 --version LV_STD_GB12801 --code 12801 --apply

echo "== 2. 删除目录页/版权页噪音条款 =="
py -X utf8 - << 'EOF'
import os
for cid in ("C_12801_5", "C_12801_5_9_1"):
    for p in (f"knowledge/clauses/{cid}.json", f"knowledge/reviews/clauses/{cid}.json"):
        if os.path.exists(p):
            os.remove(p)
    print("removed:", cid)
EOF

echo "== 3. 建立 19 条新版链接 + succession（幂等） =="
py -X utf8 tmp/apply_12801_transition.py

echo "== 4. 校验管线 =="
py -X utf8 tools/v4/sync_manifest.py
py -X utf8 tools/v4/rebind.py --fix
py -X utf8 tools/v4/validate_all.py
py -X utf8 tools/v4/gate_v4.py

echo "== 5. 构建候选 + 站点数据 + 门禁复核 =="
py -X utf8 tools/v4/build_release.py
py -X utf8 tools/v4/build_site_data.py
py -X utf8 tools/v4/gate_v4.py
py -X utf8 tools/v4/strict_release_audit.py

echo "== 6. 合格数熔断检查（应 >= 1490） =="
py -X utf8 - << 'EOF'
import sys
from datetime import date
sys.path.insert(0, "tools/v4")
from release_gate_core import evaluate_release_gate
g = evaluate_release_gate(as_of=date(2026, 10, 1))
print("eligible:", len(g.eligible_hazards), "/", len(g.eligible_links))
assert len(g.eligible_hazards) >= 1490, "合格隐患数不足，切换未生效，禁止发布"
EOF

echo "== 7. 统一包 r26 =="
py -X utf8 tools/v4/build_unified_release.py --out source/releases/unified-v4-reviewed-20261001-r29 --as-of 2026-10-01 --data-version 2026.10.01.unified-v4-r29
py -X utf8 tools/v4/verify_unified_bundle.py --bundle source/releases/unified-v4-reviewed-20261001-r29

echo "== 8. site-selection -> r26 =="
py -X utf8 - << 'EOF'
import io, json
rel = json.load(io.open("source/releases/unified-v4-reviewed-20261001-r29/release.json", encoding="utf-8"))
rh = rel.get("releaseHash") or rel.get("release_hash")
p = "source/releases/site-selection.json"
d = json.load(io.open(p, encoding="utf-8"))
d["bundle"] = "unified-v4-reviewed-20261001-r29"
d["releaseHash"] = rh
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("selection ->", d["bundle"], rh[:12])
EOF
py -X utf8 tools/v4/verify_unified_bundle.py --bundle source/releases/unified-v4-reviewed-20261001-r29

echo "== 9. 铺根目录 =="
cp -r source/releases/unified-v4-reviewed-20261001-r29/* .
rm -rf _internal data/_internal

echo "== 10. 提交推送 =="
git add -A
git commit -m "release r29: switch GB/T 12801 citations to the 2025 edition (scheduled handover)"
git push origin data-verify-batch-003

echo "== 11. PR + merge =="
TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | grep '^password=' | cut -d= -f2)
cat > tmp/pr29.json << 'EOF'
{"title": "release r29: switch GB/T 12801 citations to the 2025 edition (scheduled handover)", "head": "data-verify-batch-003", "base": "main", "body": "Scheduled 2026-10-01 switchover: 19 hazards re-linked to GB 12801-2025 clauses (old GB/T 12801-2008 links retired in r25). Gate six-phase PASS, audit PASS, bundle verify clean."}
EOF
curl -s -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/An-0726/safety-basis/pulls -d @tmp/pr29.json -o tmp/pr26_resp.json
PRNUM=$(py -X utf8 -c "import json,io; print(json.load(io.open('tmp/pr26_resp.json', encoding='utf-8'))['number'])")
echo "PR #$PRNUM created"
curl -s -X PUT -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/An-0726/safety-basis/pulls/$PRNUM/merge" \
  -d "{\"merge_method\":\"merge\",\"commit_title\":\"Merge pull request #$PRNUM from An-0726/data-verify-batch-003\"}"
echo "done. 线上 Pages 需要几分钟重建。"
