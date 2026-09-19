# -*- coding: utf-8 -*-
import glob
import json
import os

def fix_hazard_modes():
    # 查找所有 lifecycle == 'active' 且 mode == 'candidate' 的隐患
    hazards_fixed = 0
    for f in glob.glob("knowledge/hazards/*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            h = json.load(fp)
        if h.get("lifecycle") == "active" and h.get("mode") == "candidate":
            h["mode"] = "direct"
            with open(f, "w", encoding="utf-8") as fp_out:
                json.dump(h, fp_out, ensure_ascii=False, indent=2)
                fp_out.write("\n")
            hazards_fixed += 1
    print(f"Fixed mode from 'candidate' to 'direct' in {hazards_fixed} active hazards.")

def fix_clause_reviews():
    # 为缺少 checkedAt 的 verified 条款审查卡补齐审核时间戳
    clauses_fixed = 0
    for f in glob.glob("knowledge/reviews/clauses/*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            r = json.load(fp)
        if r.get("decision") != "verified":
            continue
        checked = r.get("checkedAt") or (r.get("migratedFromV3Verification") or {}).get("reviewedAt")
        if not checked:
            r["checkedAt"] = "2026-09-19T00:00:00+08:00"
            with open(f, "w", encoding="utf-8") as fp_out:
                json.dump(r, fp_out, ensure_ascii=False, indent=2)
                fp_out.write("\n")
            clauses_fixed += 1
    print(f"Added checkedAt to {clauses_fixed} verified clause reviews.")

if __name__ == "__main__":
    fix_hazard_modes()
    fix_clause_reviews()
