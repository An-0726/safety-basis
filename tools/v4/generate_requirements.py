# -*- coding: utf-8 -*-
"""
Phase 11: 从 Clause 全量生成 Requirement 草案（regulation-driven 中间层）。

规则：
- 每个 clause 至少生成 1 条 requirement（seq 递增）
- 从 clause.quote 提炼：去"应当/必须/不得"句式后取核心义务描述
- reviewStatus=pending（AI 草案，需人工/专业校准）
- 幂等：已存在 RQ id 跳过
- canonicalHash 由 canonical.content_hash 现算
"""
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CL = os.path.join(ROOT, "knowledge", "clauses")
LV = os.path.join(ROOT, "knowledge", "law-versions")
RQ = os.path.join(ROOT, "knowledge", "requirements")
MANIFEST = os.path.join(ROOT, "knowledge", "manifest.json")


def rq_id(lv_id, clause_id, seq):
    import hashlib
    return "RQ_" + hashlib.sha1(("%s|%s|%d" % (lv_id, clause_id, seq)).encode("utf-8")).hexdigest()[:22].upper()


def refine(quote, article):
    """从条款原文提炼义务描述（保守：保留原文核心句，不虚构检查项）。"""
    q = re.sub(r"\s+", " ", quote or "").strip()
    return q[:500]


def main():
    os.makedirs(RQ, exist_ok=True)
    existing = set()
    for f in glob.glob(os.path.join(RQ, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            existing.add(json.load(fh)["id"])

    added = 0
    for f in sorted(glob.glob(os.path.join(CL, "*.json"))):
        with io.open(f, encoding="utf-8") as fh:
            c = json.load(fh)
        cid = c["id"]
        lv_id = c.get("lawVersionId", "")
        article = c.get("articlePath", "")
        quote = c.get("quote", "")
        rid = rq_id(lv_id, cid, 1)
        if rid in existing:
            continue
        obj = {
            "id": rid,
            "lawVersionId": lv_id,
            "clauseId": cid,
            "seq": 1,
            "title": "%s：%s" % (article, quote[:40] if quote else cid),
            "description": refine(quote, article),
            "sourceQuote": quote,
            "scope": "依据条款适用范围",
            "checkItems": [],
            "lifecycle": "active",
            "reviewStatus": "pending",
            "reviewedAt": "",
            "reviewer": "",
            "reviewReason": "AI 草案，待专业校准（checkItems 未填充）",
        }
        obj["canonicalHash"] = content_hash(obj)
        with io.open(os.path.join(RQ, rid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        added += 1

    # manifest batch
    if os.path.exists(MANIFEST):
        mf = json.load(io.open(MANIFEST, encoding="utf-8"))
    else:
        mf = {"asOf": "2026-09-10", "batches": []}
    mf["batches"].append({
        "id": "requirements-v4.1-001",
        "requirementsAdded": added,
        "selection": "Phase 11: auto-generated Requirement layer drafts from all clauses (reviewStatus=pending; calibration deferred).",
    })
    with io.open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(mf, fh, ensure_ascii=False, indent=1)
    print("requirements added:", added)


if __name__ == "__main__":
    main()
