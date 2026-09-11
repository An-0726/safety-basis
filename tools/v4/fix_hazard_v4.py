# -*- coding: utf-8 -*-
"""
Phase 8: 历史 Hazard 结构质量修复（第一轮，机械性/明确性修复）。

范围：
A. 版本迁移：Hazard conditions 中的旧标准号 -> 现行标准号
   （依据 Phase 10 官方核验 + successions；条款号跨版本不保证对应，移至 note 待核验）
B. 危化品条款号修正（官方原文核验）：
   - H_0A53849 第22条 -> 第21条（通信、报警装置条款）
   - H_F3E7D18 第二十八条 -> 第四条、第二十八条（总则制度条款 + 使用单位制度条款）
C. FACT_NOT_HAZARD / 碎片文本 note 标记（不重写正文，留待最终验收）
D. 联动更新受影响 review 的 contextHashes.hazard + reason + checkedAt

原则：修改 Hazard 实体后重算 content hash；只更新受影响的 review 绑定；
reviewedContentHash（link 实体 hash）不受 Hazard 修改影响。
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HZ = os.path.join(ROOT, "knowledge", "hazards")
RV = os.path.join(ROOT, "knowledge", "reviews", "links")
CHECKED = "2026-09-10T15:00:00+08:00"

# (hazardId, 旧conditions精确串, 新conditions)
VERSION_FIX = [
    ("H_38AB017ED1E34FCB964087B0EA", "依据：《安全标志及其使用导则》 (GB 2894-2008)",
     "依据：《安全色和安全标志》（GB 2894-2025）"),
    ("H_F692794FBBA74CFB83648A73CF", "依据：《安全标志及其使用导则》 (GB 2894-2008)",
     "依据：《安全色和安全标志》（GB 2894-2025）"),
    ("H_409EF7D84AB8469C91AEC3385C", "依据：《常用化学危险品贮存通则》GB 15603-1995 4.6",
     "依据：《危险化学品仓库储存通则》（GB 15603-2022）"),
    ("H_F57270BED8114BB69A556DEBA2", "依据：《常用化学危险品贮存通则》GB 15603-1995 4.4",
     "依据：《危险化学品仓库储存通则》（GB 15603-2022）"),
    ("H_58B8DD3B2F5E42F69265ECA65D", "依据：《生产设备安全卫生设计总则》GB 5083-1999 6.2.1",
     "依据：《生产设备安全卫生设计总则》（GB 5083-2023）"),
    ("H_86746E9DDF904453A53248278C", "依据：《生产设备安全卫生设计总则》GB 5083-1999 5.6.3.2",
     "依据：《生产设备安全卫生设计总则》（GB 5083-2023）"),
    ("H_C067799BCC9B44A398A2595C28", "依据：《生产设备安全卫生设计总则》GB 5083-1999 5.6.1.4",
     "依据：《生产设备安全卫生设计总则》（GB 5083-2023）"),
    ("H_C6F79739AB464612BC5A5E47C3", "依据：《生产设备安全卫生设计总则》 (GB 5083-1999)第6.6条",
     "依据：《生产设备安全卫生设计总则》（GB 5083-2023）"),
    ("H_DC8FD0AA53E24CBE9C30552E91", "依据：《生产设备安全卫生设计总则》GB 5083-1999 5.5.2",
     "依据：《生产设备安全卫生设计总则》（GB 5083-2023）"),
    ("H_EC527E40F25347948ADA08A388", "依据：《生产设备安全卫生设计总则》GB 5083-1999 5.6.2.1",
     "依据：《生产设备安全卫生设计总则》（GB 5083-2023）"),
    ("H_5C632EB0FC8E4DC586BDF3567E", "依据：《焊接与切割安全》(GB 9448-1999)",
     "依据：《焊接与切割安全》（GB 9448-2025）"),
    ("H_67303D31915B4AC0A6902EB975", "依据：《焊接与切割安全》(GB 9448-1999)",
     "依据：《焊接与切割安全》（GB 9448-2025）"),
    ("H_0A53849CB39848628056FDADEB", "依据：《危险化学品安全管理条例》第22条",
     "依据：《危险化学品安全管理条例》第21条"),
    ("H_F3E7D18DBD77459B983AB5CD06", "依据：《危险化学品安全管理条例》第二十八条",
     "依据：《危险化学品安全管理条例》第四条、第二十八条"),
]

# note 追加（追溯）
NOTE_APPEND = {
    "H_38AB017ED1E34FCB964087B0EA": "【Phase8】原依据 GB 2894-2008 已由 GB 2894-2025 替代（2026-03-01 实施，整合替代 GB 2893-2008/GB 2894-2008/GB 7231-2003）；新版条款号待按官方全文核验。",
    "H_F692794FBBA74CFB83648A73CF": "【Phase8】原依据 GB 2894-2008 已由 GB 2894-2025 替代（2026-03-01 实施）；新版条款号待按官方全文核验。",
    "H_409EF7D84AB8469C91AEC3385C": "【Phase8】原依据 GB 15603-1995 第4.6条已由 GB 15603-2022 替代（2023-07-01 实施）；新版对应条款号待核验。",
    "H_F57270BED8114BB69A556DEBA2": "【Phase8】原依据 GB 15603-1995 第4.4条已由 GB 15603-2022 替代（2023-07-01 实施）；新版对应条款号待核验。",
    "H_58B8DD3B2F5E42F69265ECA65D": "【Phase8】原依据 GB 5083-1999 第6.2.1条已由 GB 5083-2023 替代（2025-01-01 实施）；新版条款结构重排，对应条款号待核验。",
    "H_86746E9DDF904453A53248278C": "【Phase8】原依据 GB 5083-1999 第5.6.3.2条已由 GB 5083-2023 替代（2025-01-01 实施）；对应条款号待核验。",
    "H_C067799BCC9B44A398A2595C28": "【Phase8】原依据 GB 5083-1999 第5.6.1.4条已由 GB 5083-2023 替代（2025-01-01 实施）；对应条款号待核验。",
    "H_C6F79739AB464612BC5A5E47C3": "【Phase8】原依据 GB 5083-1999 第6.6条已由 GB 5083-2023 替代（2025-01-01 实施）；对应条款号待核验。",
    "H_DC8FD0AA53E24CBE9C30552E91": "【Phase8】原依据 GB 5083-1999 第5.5.2条已由 GB 5083-2023 替代（2025-01-01 实施）；对应条款号待核验。",
    "H_EC527E40F25347948ADA08A388": "【Phase8】原依据 GB 5083-1999 第5.6.2.1条已由 GB 5083-2023 替代（2025-01-01 实施）；对应条款号待核验。",
    "H_5C632EB0FC8E4DC586BDF3567E": "【Phase8】原依据 GB 9448-1999 已由 GB 9448-2025 替代（2026-08-01 实施）。本条 title/description 为 V3 迁移碎片文本（以'中的气瓶…'开头），建议后续改写为完整隐患事实表述。",
    "H_67303D31915B4AC0A6902EB975": "【Phase8】原依据 GB 9448-1999 已由 GB 9448-2025 替代（2026-08-01 实施）。本条为义务复述+缺陷事实混合描述，建议后续改写为现场缺陷事实表述。",
    "H_0A53849CB39848628056FDADEB": "【Phase8】原引用条例第22条（专用仓库储存）为条款号错误；作业场所通信、报警装置义务对应条例第21条（官方全文核验），已修正。",
    "H_F3E7D18DBD77459B983AB5CD06": "【Phase8】补充条例第四条（危险化学品单位应建立、健全安全管理规章制度和岗位安全责任制度）；第二十八条为使用单位的制度义务条款，两条并用更准确。",
}

# FACT_NOT_HAZARD / 义务复述标记（只加 note，不改正文）
OBLIGATION_NOTE = [
    "H_58B8DD3B2F5E42F69265ECA65D", "H_86746E9DDF904453A53248278C",
    "H_C067799BCC9B44A398A2595C28", "H_C6F79739AB464612BC5A5E47C3",
    "H_DC8FD0AA53E24CBE9C30552E91", "H_EC527E40F25347948ADA08A388",
]
OBLIGATION_TEXT = "【Phase8】义务条款复述型描述（'必须…未配置…'句式），非现场缺陷事实本身，FACT_NOT_HAZARD 候选；建议后续改写为隐患事实表述。"


def load_hazards():
    out = {}
    for f in glob.glob(os.path.join(HZ, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        out[d["id"]] = d
    return out


def main():
    hazards = load_hazards()
    changed = []
    for hid, old_cond, new_cond in VERSION_FIX:
        h = hazards.get(hid)
        if h is None:
            print("MISSING hazard", hid)
            continue
        if h.get("conditions") != old_cond:
            print("CONDITION MISMATCH for", hid, "| now:", repr(h.get("conditions"))[:80])
            continue
        h["conditions"] = new_cond
        note = h.get("note") or ""
        if NOTE_APPEND.get(hid):
            note = (note + "\n" if note else "") + NOTE_APPEND[hid]
        if hid in OBLIGATION_NOTE:
            note = (note + "\n" if note else "") + OBLIGATION_TEXT
        h["note"] = note
        with io.open(os.path.join(HZ, hid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(h, fh, ensure_ascii=False, indent=1)
        changed.append(hid)
    print("hazards updated:", len(changed))

    # 更新受影响 review 的 contextHashes.hazard
    links = {}
    for f in glob.glob(os.path.join(ROOT, "knowledge", "links", "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            l = json.load(fh)
        links[l["id"]] = l
    rev_updated = 0
    for hid in changed:
        for kid, l in links.items():
            if l.get("hazardId") != hid:
                continue
            rf = os.path.join(RV, kid + ".json")
            if not os.path.exists(rf):
                print("MISSING review", kid)
                continue
            with io.open(rf, encoding="utf-8") as fh:
                rev = json.load(fh)
            hh = content_hash(hazards[hid])
            ctx = dict(rev.get("contextHashes") or {})
            ctx["hazard"] = hh
            rev["contextHashes"] = ctx
            reason = str(rev.get("reason") or "")
            if hid == "H_0A53849CB39848628056FDADEB" and "第22条" in reason:
                reason = reason.replace("第22条", "第21条")
            if hid == "H_F692794FBBA74CFB83648A73CF" and "GB2894-2008" in reason:
                reason = reason.replace("GB2894-2008", "GB 2894-2025").replace("GB2894", "GB 2894")
            rev["reason"] = reason
            rev["checkedAt"] = CHECKED
            with io.open(rf, "w", encoding="utf-8") as fh:
                json.dump(rev, fh, ensure_ascii=False, indent=1)
            rev_updated += 1
    print("reviews updated:", rev_updated)


if __name__ == "__main__":
    main()
