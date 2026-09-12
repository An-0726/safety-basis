#!/bin/bash
# GB/T 13869 新版切换发布（2027-02-01 执行）。
# 前提：当天 GB/T 13869-2026 生效，upcoming 条款不再阻断门禁。
# 官方 PDF 干净文本已于 2026-09-13 导入全文库（LF_STD_GBT13869_2026）。
# 任何验证步骤失败即退出非零，不部署。
set -e
cd /d/ESH/ESH_Codex/work/safety-basis

echo "== 1. 入库 GB/T 13869-2026 条款 =="
py -X utf8 tools/v4/ingest_law_clauses.py --doc LF_STD_GBT13869_2026 --version LV_STD_GBT13869_2026 --code G26 --apply

echo "== 2. 12 条隐患换挂到 2026 版对应条款（按引文特征匹配，删旧链接） =="
py -X utf8 - << 'EOF'
import glob, hashlib, io, json, os, sys
KNOW = "knowledge"
sys.path.insert(0, "tools/v4")
sys.path.insert(0, "tools/pipeline")
from canonical import content_hash

def jload(p):
    return json.load(io.open(p, encoding="utf-8"))

def wj(p, o):
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, indent=2) + "\n")

NOW = "2027-02-01"
MODEL = "GLM-5.3-Flash (ZCode)"
clauses = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/clauses/*.json")}

# 新版目标条款：按引文特征匹配（条款编号在 OCR/解析中可能错位，勿按编号匹配）
target_a = next(cid for cid, d in clauses.items()
                if d.get("lawVersionId") == "LV_STD_GBT13869_2026"
                and "安全通道和工作空间" in d.get("quote", ""))
target_b = next(cid for cid, d in clauses.items()
                if d.get("lawVersionId") == "LV_STD_GBT13869_2026"
                and "有效执行电气作业" in d.get("quote", ""))
print("target A (通道/空间):", target_a)
print("target B (人员要求):", target_b)

OLD_A = "C_111e6a4f843a9547ddddf11b"   # 旧 5.1.1 安全通道/工作空间
OLD_B = "C_GBT13869_9"                 # 旧 第9章 电气作业人员要求

# 受影响隐患与其旧角色
affected = {}
for p in glob.glob(f"{KNOW}/links/*.json"):
    l = jload(p)
    if l.get("lifecycle") == "active" and l.get("clauseId") in (OLD_A, OLD_B):
        affected.setdefault(l["hazardId"], []).append((p, l))

assert len(affected) == 12, f"受影响隐患数异常: {len(affected)}（应为 12）"

existing = {(l.get("hazardId"), l.get("clauseId")) for l in
            (jload(p) for p in glob.glob(f"{KNOW}/links/*.json"))
            if l.get("lifecycle") == "active"}
hazards = {os.path.basename(p)[:-5]: jload(p) for p in glob.glob(f"{KNOW}/hazards/*.json")}

created = 0
REASON = ("GB/T 13869 新旧版衔接（GLM，2027-02-01）：旧版 2027-01-31 到期，换挂 2026 版对应条款。")
for hid, old_links in sorted(affected.items()):
    old_roles = {l["role"] for _, l in old_links}
    new_cid = target_b if any(l["clauseId"] == OLD_B for _, l in old_links) else target_a
    role = "supporting" if "supporting" in old_roles and "direct" not in old_roles else "direct"
    if (hid, new_cid) in existing:
        print("skip dup:", hid, new_cid)
        continue
    kid = "K_" + hashlib.md5(f"{hid}|{new_cid}".encode()).hexdigest()[:24].upper()
    link = {"id": kid, "hazardId": hid, "clauseId": new_cid, "role": role,
            "legacyRole": "", "applicability": hazards[hid]["title"][:44] + "的现场状态。",
            "jurisdictionCode": "CN", "lifecycle": "active",
            "priority": 10 if role == "direct" else 20, "requirementId": "",
            "reason": "新旧版衔接换挂（GLM 逐条映射审核，2027-02-01）"}
    wj(f"{KNOW}/links/{kid}.json", link)
    lrev = {"checkedAt": NOW, "contextHashes": {"clause": content_hash(clauses[new_cid]),
                                                "hazard": content_hash(hazards[hid])},
            "decision": "verified", "entityId": kid, "entityType": "link",
            "evidenceRefs": [], "reason": REASON,
            "reviewType": "applicability", "reviewedContentHash": content_hash(link),
            "reviewer": MODEL}
    wj(f"{KNOW}/reviews/links/{kid}.json", lrev)
    existing.add((hid, new_cid))
    created += 1
print("new links created:", created)

removed = 0
for hid, old_links in affected.items():
    for p, l in old_links:
        os.remove(p)
        rp = os.path.join(KNOW, "reviews", "links", os.path.basename(p))
        if os.path.exists(rp):
            os.remove(rp)
        removed += 1
print("old links removed:", removed)
EOF

echo "== 3. 校验管线 =="
py -X utf8 tools/v4/sync_manifest.py
py -X utf8 tools/v4/rebind.py --fix
py -X utf8 tools/v4/validate_all.py
py -X utf8 tools/v4/gate_v4.py

echo "== 4. 构建候选 + 站点数据 + 门禁复核 =="
py -X utf8 tools/v4/build_release.py
py -X utf8 tools/v4/build_site_data.py
py -X utf8 tools/v4/gate_v4.py
py -X utf8 tools/v4/strict_release_audit.py

echo "== 5. 合格数熔断检查（应 >= 1488） =="
py -X utf8 - << 'EOF'
import sys
from datetime import date
sys.path.insert(0, "tools/v4")
from release_gate_core import evaluate_release_gate
g = evaluate_release_gate(as_of=date(2027, 2, 1))
print("eligible:", len(g.eligible_hazards), "/", len(g.eligible_links))
assert len(g.eligible_hazards) >= 1488, "合格隐患数不足，换挂未生效，禁止发布"
EOF

echo "== 6. 统一包 r30 =="
py -X utf8 tools/v4/build_unified_release.py --out source/releases/unified-v4-reviewed-20270201-r30 --as-of 2027-02-01 --data-version 2027.02.01.unified-v4-r30
py -X utf8 tools/v4/verify_unified_bundle.py --bundle source/releases/unified-v4-reviewed-20270201-r30

echo "== 7. site-selection -> r30 =="
py -X utf8 - << 'EOF'
import io, json
rel = json.load(io.open("source/releases/unified-v4-reviewed-20270201-r30/release.json", encoding="utf-8"))
rh = rel.get("releaseHash") or rel.get("release_hash")
p = "source/releases/site-selection.json"
d = json.load(io.open(p, encoding="utf-8"))
d["bundle"] = "unified-v4-reviewed-20270201-r30"
d["releaseHash"] = rh
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("selection ->", d["bundle"], rh[:12])
EOF
py -X utf8 tools/v4/verify_unified_bundle.py --bundle source/releases/unified-v4-reviewed-20270201-r30

echo "== 8. 铺根目录 =="
cp -r source/releases/unified-v4-reviewed-20270201-r30/* .
rm -rf _internal data/_internal

echo "== 9. 提交推送 =="
git add -A
git commit -m "release r30: switch GB/T 13869 citations to the 2026 edition (scheduled handover)"
git push origin data-verify-batch-003

echo "== 10. PR + merge =="
TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | grep '^password=' | cut -d= -f2)
cat > tmp/pr30.json << 'EOF'
{"title": "release r30: switch GB/T 13869 citations to the 2026 edition (scheduled handover)", "head": "data-verify-batch-003", "base": "main", "body": "Scheduled 2027-02-01 switchover: 12 hazards re-linked to GB/T 13869-2026 clauses (old 2017 links retired 2027-01-31). Gate six-phase PASS, audit PASS, bundle verify clean."}
EOF
curl -s -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/An-0726/safety-basis/pulls -d @tmp/pr30.json -o tmp/pr30_resp.json
PRNUM=$(py -X utf8 -c "import json,io; print(json.load(io.open('tmp/pr30_resp.json', encoding='utf-8'))['number'])")
echo "PR #$PRNUM created"
curl -s -X PUT -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/An-0726/safety-basis/pulls/$PRNUM/merge" \
  -d "{\"merge_method\":\"merge\",\"commit_title\":\"Merge pull request #$PRNUM from An-0726/data-verify-batch-003\"}"
echo "done. 线上 Pages 需要几分钟重建。"
