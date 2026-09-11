# -*- coding: utf-8 -*-
"""Phase 8: 修复 review evidence 错配（5 条）。

依据 scan_evidence_exact.py 精确扫描结果：
1. K_01DD57C7 / K_03BF627B / K_04BD5E63：clause 为《危险废物贮存污染控制标准》(GB 18597-2023)，
   evidence 错误指向消防法 flk 页面 -> 改指 mee.gov.cn GB 18597 官方全文（E_026fdfa9）。
2. K_A43B448D：clause 为《易制毒化学品管理条例》第三十六条，
   evidence 错误指向 mee.gov.cn 危废 PDF -> 新建商务部（国务院令第445号）官方全文 evidence。
3. K_6ee0642e：clause 为消防法（2021修正）第二十一条第二款，
   evidence 指向 samr.gov.cn 办公厅文件（弱引用）-> 新建 flk.npc.gov.cn 消防法原文 evidence（第二十一条第二款）。

原则：不删除既有 evidence 实体（可能被其他 review 正确引用）；只修正 review 引用与 reason 说明。
"""
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
EV = os.path.join(KNOW, "evidence")
RV = os.path.join(KNOW, "reviews", "links")
CHECKED = "2026-09-10T16:00:00+08:00"


def new_evidence(url, locator):
    eid = "E_" + hashlib.sha256((url + "|" + locator).encode("utf-8")).hexdigest()
    obj = {
        "id": eid,
        "locator": locator,
        "page": "",
        "retrievedAt": CHECKED,
        "snapshotSha256": "",
        "tier": "authoritative-public",
        "url": url,
    }
    with io.open(os.path.join(EV, eid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    return eid


def main():
    yizhidu_url = "https://www.mofcom.gov.cn/zcfb/zgdwjjmywg/art/2005/art_105e2b2a02b347629a54e6b87edc61a1.html"
    fire_url = "https://flk.npc.gov.cn/detail?id=ff8081817ab22e0c017abd909312060a"
    e_yizhidu = new_evidence(yizhidu_url, "第三十六条")
    e_fire21 = new_evidence(fire_url, "第二十一条第二款")
    mee_pdf = "E_026fdfa94508deea38f0f150b79c87a9a3ae47136eb94c8a17aefbd2b273e992"
    print("new evidence:", e_yizhidu[:20], e_fire21[:20])

    fixes = {
        "K_01DD57C7DD1768B0CD4B56F12C": (["E_0d32c4cce961a92a4907df8e724d162ba60113e84300c1c90fd8b5e72104c0ab"], [mee_pdf], "修复：该 review clause 为《危险废物贮存污染控制标准》（GB 18597-2023）条款，原 evidence 错误指向消防法页面，现改指生态环境部 GB 18597-2023 官方全文（mee.gov.cn）。"),
        "K_03BF627B0B2DF4D35F2FCF5C39": (["E_0d32c4cce961a92a4907df8e724d162ba60113e84300c1c90fd8b5e72104c0ab"], [mee_pdf], "修复：该 review clause 为《危险废物贮存污染控制标准》（GB 18597-2023）条款，原 evidence 错误指向消防法页面，现改指生态环境部 GB 18597-2023 官方全文（mee.gov.cn）。"),
        "K_04BD5E63412B9DEE6F3374C7F3": (["E_0d32c4cce961a92a4907df8e724d162ba60113e84300c1c90fd8b5e72104c0ab"], [mee_pdf], "修复：该 review clause 为《危险废物贮存污染控制标准》（GB 18597-2023）条款，原 evidence 错误指向消防法页面，现改指生态环境部 GB 18597-2023 官方全文（mee.gov.cn）。"),
        "K_A43B448D1E611C41A5212F686D": (["E_026fdfa94508deea38f0f150b79c87a9a3ae47136eb94c8a17aefbd2b273e992"], [e_yizhidu], "修复：该 review clause 为《易制毒化学品管理条例》第三十六条（年度报告义务），原 evidence 错误指向 GB 18597 危废标准 PDF，现改指商务部转载的国务院令第445号官方全文（第三十六条）。"),
        "K_6ee0642e5ff1afa64ba4bc74": (["E_8b8355be0707a8a1ef5c8a4bad6e000b2aeb11703b3c3ff60dce64a6c7f4f04c"], [e_fire21], "修复：该 review clause 为消防法（2021修正）第二十一条第二款（动火作业），原 evidence 为市场监管总局办公厅文件（弱引用），现改指国家法律法规数据库消防法原文（第二十一条第二款）。"),
    }
    for kid, (old_refs, new_refs, note) in fixes.items():
        rf = os.path.join(RV, kid + ".json")
        if not os.path.exists(rf):
            print("MISSING review", kid)
            continue
        with io.open(rf, encoding="utf-8") as fh:
            rev = json.load(fh)
        refs = [r for r in (rev.get("evidenceRefs") or []) if r not in old_refs]
        for nr in new_refs:
            if nr not in refs:
                refs.append(nr)
        rev["evidenceRefs"] = refs
        reason = str(rev.get("reason") or "")
        if "修复：" not in reason:
            rev["reason"] = (reason + "\n" if reason else "") + note
        rev["checkedAt"] = CHECKED
        with io.open(rf, "w", encoding="utf-8") as fh:
            json.dump(rev, fh, ensure_ascii=False, indent=1)
        print("fixed", kid, "->", refs)


if __name__ == "__main__":
    main()
