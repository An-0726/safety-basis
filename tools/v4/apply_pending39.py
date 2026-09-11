# -*- coding: utf-8 -*-
"""Pending 39 落定：verified 1 / rejected 6 / pending 32（reason 补强+拆分任务登记）。

依据：
- V3 SQLite links 表已核验记录（K_13863d87 -> C001 消防法16条，role=直接依据, status=已核验）
- GB 2894-2025 官方解读核验（舟山/安徽应急厅）
- 逐条专业研判（见 reason 文本）
"""
import glob
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import content_hash  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "knowledge")
REV_DIR = os.path.join(BASE, "reviews", "links")
HAZ_DIR = os.path.join(BASE, "hazards")
CHECKED_AT = "2026-09-10T13:30:00+08:00"
REVIEWER = "Doubao-Agent"

def load_dir(sub):
    out = {}
    for f in glob.glob(os.path.join(BASE, sub, "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        eid = d.get("id") or d.get("entityId")
        out[eid] = d
    return out

reviews = load_dir("reviews/links")
hazards = load_dir("hazards")

# ---- 决策表 ----
DECISIONS = {
    # verified
    "K_13863d87b22b4a3eb596ad05": {
        "decision": "verified",
        "codes": ["DIRECT_MATCH", "V3_VERIFIED_CROSS_REF"],
        "reason": "V3 SQLite links 表已核验记录确认：K_13863d87 -> C001（消防法第16条'按照国家标准、行业标准配置消防设施、器材…确保完好有效'）role=直接依据、status=已核验（source=concurrent_reverify_20260909）。灭火器筒体存在明显缺陷/机械损伤即未保持完好有效，消防法16条直接覆盖；Hazard title 双重否定（'未无明显缺陷'）为 V3 同源数据瑕疵，语义按 V3 核验=筒体存在缺陷，不修改原文，仅记录。",
    },
    # rejected：FACT_NOT_HAZARD / 关联不成立
    "K_1ce59ea0c2a4692ab95e6a10": {
        "decision": "rejected",
        "codes": ["FACT_NOT_HAZARD"],
        "reason": "Hazard 为《江苏省工业企业安全生产风险报告工作实施方案》第九条授权性规范复述（'可以一并纳入较大以上安全风险进行管理'）：非缺陷事实、非强制性义务；C024（安法41条第1款）无法与任何'未履行'事实对应，关联不成立。已登记 hazard 数据修复任务（待现场缺陷事实改写或拆分）。",
    },
    "K_572a04b023a8b17211c06526": {
        "decision": "rejected",
        "codes": ["FACT_NOT_HAZARD"],
        "reason": "Hazard 为起重机'十不吊'操作要求复述（源自 GB 6067.1），未指明违反操作规程的具体缺陷事实（如违规起吊行为）；C019（安法第21条第2项）仅为间接的规程制定义务，不能与未执行十不吊的操作缺陷直接对应，关联不成立。已登记 hazard 数据修复任务。",
    },
    "K_5bfae4aa6d1056875adbfb9a": {
        "decision": "rejected",
        "codes": ["FACT_NOT_HAZARD"],
        "reason": "Hazard 为消防法第16条第（五）项义务原文复述（'组织防火检查，及时消除火灾隐患'），未指明未组织防火检查或火灾隐患未及时消除的具体缺陷事实；C021 为义务条文本身，关联不成立（Hazard 实体不合格而非条款问题）。已登记 hazard 数据修复任务（须以检查记录中的实际缺陷改写）。",
    },
    "K_cb144fd956f2f35643dcb94f": {
        "decision": "rejected",
        "codes": ["FACT_NOT_HAZARD"],
        "reason": "同 K_5bfae4aa：Hazard 为消防法第16条第（五）项义务复述（H_E144206D），无具体缺陷事实；C021 关联不成立。已登记 hazard 数据修复任务。",
    },
    "K_817f978ac504cebac8791378": {
        "decision": "rejected",
        "codes": ["SCOPE_MISMATCH"],
        "reason": "Clause 为 GB 18597-2023 第11.2条（危险废物贮存设施的应急管理要求），Hazard 为通用应急预案落实义务（应急指挥体系/救援队伍/物资装备，依据《生产安全事故应急预案管理办法》应急部令第2号），场所与适用对象不一致；正确 direct 依据应为《生产安全事故应急预案管理办法》相应条款。",
    },
    "K_fbbb1ecbbd84aabaa391d077": {
        "decision": "rejected",
        "codes": ["SCOPE_MISMATCH", "SPECIFIC_CLAUSE_REQUIRED"],
        "reason": "Hazard 缺陷为易制毒企业主要负责人未了解易制毒化学品管理法律法规及基本知识（知识能力缺陷）；C_64588491（安法第5条）仅确立主要负责人第一责任人地位，不直接规定知识能力要求；正确依据为安法第27条第1款（具备相应安全生产知识和管理能力，对应 C033），本条关联不成立。",
    },
}

# ---- pending：reason 追加 ----
PENDING_APPEND = {
    "K_3af925c80dbe5edabd333656": "2026-09-10 官方核验：GB 2894-2025（舟山市应急管理局解读全文、安徽省应急厅解读）设置要求为'标志应设置在醒目位置，不得被设备、物料、构筑物遮挡'、平面与视线夹角≥75°等；2008版'标志牌不应设在门、窗、架等可移动的物体上'的明确禁令未在 2025 版官方解读中延续。'张贴在门上'是否违规需结合门扇移动是否影响认读的现场事实判定，维持 pending。",
    "K_7caf3e9d8e91a30ec04247bf": "2026-09-10 补充：direct 专项依据指向 TSG 81-2022《场（厂）内专用机动车辆安全技术规程》首次检验相关条款或特设法第25条（监督检验），待建立专项 clause/link 后再判定，维持 pending。",
}

# 复合 hazard 拆分任务登记（id -> 描述 + 拆分建议）
SPLIT_TASKS = {
    "H_56B7B9F8379B4E6E93F2342596": "安法第4条全文复述，混合全员责任制/规章制度/资金投入/双重预防等多项独立义务（links: K_01250036->C018, K_401ab2c6->C020, K_af4ab233->C019）",
    "H_83C122272BA54FE1AB0F410B4F": "GB18597-2023 6.2.2 液体泄漏收集 与 6.2.3 气体导出净化 两类独立设施（links: K_03BF627B->6.2.2, K_A3DB2344->6.2.3）",
    "H_9D076BD9D82444DCAA72489164": "责任制+安全规章制度+事故应急救援预案+各级人员责任（links: K_04361764->C018, K_fb679390->C019；预案对应安法第81条）",
    "H_CB180AFAA53646A7A9A5F9D350": "检修防护用品（安法45条）+ 加药设施洗眼装置（GB/T28742 专项）两类义务（K_1152264e->C016）",
    "H_44549E43707D4EBCB2D1BC7E67": "GB45067-2024 4.1 六类特种设备重大事故隐患情形（未取得许可/明令淘汰报废/事故未全面检查/未监督检验/超参数等；links: K_1e1990fb->C035, K_7780c2c2->安法38条）",
    "H_89BC396EBC084489B0CC25B02B": "铭牌/操作指示标牌（GB/T25711-2010 3.12.1）+ 安全标牌（安法35条）三类标牌（K_3aa0366e->C030）",
    "H_D68030A1FF76475CB16F6AF998": "正压式空气呼吸器（安法45条）+ 氨气检测仪（重点监管危化品专项）两类防护（K_44463045->C016）",
    "H_8C5C628FAFD544CF8FF58A7732": "储存区警示标志（安法35条）+ 钢瓶容器接地跨接（防静电专项）+ 消防器材及泄漏应急设备（消防法16条）三类义务（K_6965d51d->C030）",
    "H_997F60F5C9034C5593A316E08F": "焊接/热切割特种作业证（安法30条/消防法21条2款）+ 特种设备焊接作业人员证（TSG体系）两类持证（links: K_6ee0642e->C073, K_d70e5b34->C039）",
    "H_A1696721CCC94F65AE95751A5E": "GB45067-2024 4.4 压力管道：a 定期检验不合格仍用（特设法40条）+ b 安全附件缺失失效（TSG D0001/GB45067 专项）（K_7c750e6a->C035）",
    "H_AC55E4B5240544A7AA7A1CB3F8": "GB45067-2024 4.3 压力容器六类情形：a 特设法40条覆盖；b-f 改作移动式/安全阀爆破片紧急切断/快开门联锁/氧舱接地/氧舱联锁（TSG21/GB45067 专项）（K_affa50e6->C035）",
    "H_22D804731C0D4F90A6BF2A83CD": "GB45067-2024 4.10 场内车辆五类情形：a 特设法40条覆盖；b-e 电源紧急切断/制动/牵引连接/超坡度（TSG81/GB45067 专项）（K_b064b1dc->C035）",
    "H_F57270BED8114BB69A556DEBA2": "危化品仓库专人管理/专业技术人员（GB15603/危化品条例）+ 管理人员个人防护用品（安法45条）两类义务（K_8395b048->C016）",
    "H_9BC92F4558404DA9B14A721492": "仓储电气线路定期检查检测（消防法27条2款）+ 禁止长时间超负荷运行（XF1131 8.10）两类义务（K_86116589->C005）",
    "H_5F59F50EE244471C81C2757635": "粉尘废屑储存六项独立义务（压块压实/干式密闭/冷却常温/分类不混装/镁屑单层存放；links: K_8cc09e65->GB18597 4.9, K_9dd4248d->4.3；专项依据苏安办〔2020〕13号）",
    "H_D0E34E3CC9C64F458BCCDA4674": "危废库选址 6.1 六项要求（地质地震/地下水位/环评距离/溶洞洪水/危化品高压线隔离/下风向；现行 GB18597-2023 5.2 仅覆盖部分，含版本差异）（K_D2E0A559->C_94B0EF32）",
    "H_475C71B0AA9E4C08B82E9C8B29": "剧毒/监控/易制毒/易制爆备案（危化品条例/易制毒条例）+ 重大危险源备案（安法40条）+ 剧毒专用库双人收发（危化品条例24条）三类义务（K_d84f4527->C044）",
    "H_4B099AC576B249B6A7A28AE8E0": "储存区警示标志（安法35条）+ 灌装流速控制/接地防静电（重点监管危化品专项）+ 消防器材及泄漏应急设备（消防法16条）三类义务（K_df15e916->C030）",
    "H_1DB6AE75F00A4EB682FA20136E": "暂存区警示标志（安法35条）+ 消防器材（消防法16条）+ 泄漏应急设备（专项）三类义务（K_e67fe6b5->C030）",
    "H_0AB8998CB24041C894BB326A69": "全员安全生产责任制（安法21条1项 C018）+ 主要负责人第一责任人（安法5条）两类义务（K_f0ef428a->C_64588491）",
    "H_9DCBB0D8DB5441A2A3E4811603": "隐患排查治理制度建立/定期排查（安法41条2款）+ 信息系统记录通报 + 重大隐患记录保存5年（南京市条例第20条，地方要求）三类义务（K_5de4afe5->C003）",
}

# ---- 执行：review 更新 ----
changed = 0
for rid, rev in reviews.items():
    if rid not in DECISIONS and rid not in PENDING_APPEND:
        continue
    if rev.get("decision") == "pending" and rid not in DECISIONS:
        # pending 追加
        add = PENDING_APPEND.get(rid)
        if add:
            old = rev.get("reason") or ""
            rev["reason"] = old + "\n" + add
            rev["checkedAt"] = CHECKED_AT
            changed += 1
        continue
    dec = DECISIONS.get(rid)
    if not dec:
        continue
    rev["decision"] = dec["decision"]
    rev["reasonCodes"] = dec["codes"]
    rev["reason"] = dec["reason"]
    rev["checkedAt"] = CHECKED_AT
    rev["reviewer"] = REVIEWER
    changed += 1

# 复合 hazard 的 pending review 追加拆分任务登记引用
split_lines = {}
SPLIT_REVIEWS = set()
for hid, desc in SPLIT_TASKS.items():
    for rid, rev in reviews.items():
        if rid in DECISIONS:
            continue
        link = None
        for f in glob.glob(os.path.join(BASE, "links", "*.json")):
            l = json.load(io.open(f, encoding="utf-8"))
            if (l.get("id") or l.get("entityId")) == rid:
                link = l
                break
        if not link:
            continue
        lhid = link.get("hazardId") or (link.get("hazard") or {}).get("id")
        if lhid == hid and rev.get("decision") == "pending":
            if "V4_HAZARD_SPLIT_TASKS" not in (rev.get("reason") or ""):
                rev["reason"] = (rev.get("reason") or "") + "\n【Phase8-20260910】复合隐患：已登记拆分任务 docs/V4_HAZARD_SPLIT_TASKS.md 项（" + hid + "）；拆分后再判定 link 角色。"
                rev["checkedAt"] = CHECKED_AT
                changed += 1
            SPLIT_REVIEWS.add(rid)
            split_lines.setdefault(hid, []).append(rid)

# 写入更新过的 review 文件（保持原 indent=2 格式；只写有改动的条目）
def save_review(rid, rev):
    p = os.path.join(REV_DIR, rid + ".json")
    if os.path.exists(p):
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(rev, ensure_ascii=False, indent=2) + "\n")

for rid, rev in reviews.items():
    if rid in DECISIONS:
        save_review(rid, rev)
    elif rid in PENDING_APPEND:
        save_review(rid, rev)
    elif rid in SPLIT_REVIEWS:
        save_review(rid, rev)

# ---- hazard note 标记（FACT_NOT_HAZARD）----
NOTE_ADD = {
    "H_0AEEA3C7BD0D4396AF871679A0": "【Phase8-20260910】义务/授权性规范复述，非隐患事实；link K_1ce59ea0 已 rejected，待以现场缺陷事实改写或拆分。",
    "H_AC1FE4D91A8E44AF90E86B9F6C": "【Phase8-20260910】起重机'十不吊'操作要求复述，未指明违规事实；link K_572a04b0 已 rejected，待改写为具体违规行为。",
    "H_DBB3FBAC606D4719B52CEF1A5E": "【Phase8-20260910】消防法16条（五）项义务复述，非隐患事实；link K_5bfae4aa 已 rejected，待以检查记录实际缺陷改写。",
    "H_E144206DA62A4A1F83CCF8F896": "【Phase8-20260910】消防法16条（五）项义务复述，非隐患事实；link K_cb144fd9 已 rejected，待以检查记录实际缺陷改写。",
}
haz_changed = []
for hid, note in NOTE_ADD.items():
    h = hazards.get(hid)
    if not h:
        print("WARN missing hazard", hid)
        continue
    if note.split("】")[0] + "】" not in (h.get("note") or ""):
        h["note"] = (h.get("note") or "") + "\n" + note
        # hazard 原文件为 compact JSON（无缩进），保持同格式
        io.open(os.path.join(HAZ_DIR, hid + ".json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps(h, ensure_ascii=False) + "\n")
        haz_changed.append(hid)

# ---- 重绑所有 review 的 contextHashes（hazard hash 可能因 note 变化）----
rebound = 0
for rid, rev in reviews.items():
    ctx = rev.get("contextHashes") or {}
    # 找到该 review 对应 link 的 hazardId
    link = None
    for f in glob.glob(os.path.join(BASE, "links", "*.json")):
        l = json.load(io.open(f, encoding="utf-8"))
        if (l.get("id") or l.get("entityId")) == rid:
            link = l
            break
    if not link:
        continue
    lhid = link.get("hazardId") or (link.get("hazard") or {}).get("id")
    h = hazards.get(lhid)
    if not h:
        continue
    new_h = content_hash(h)
    if ctx.get("hazard") != new_h:
        ctx["hazard"] = new_h
        rev["contextHashes"] = ctx
        save_review(rid, rev)
        rebound += 1

# ---- 生成拆分任务文档 ----
lines = [
    "# V4 Hazard 拆分任务登记（V4_HAZARD_SPLIT_TASKS）",
    "",
    "> 生成时间：2026-09-10（Pending 39 落定轮）。",
    "> 复合 Hazard（COMPOSITE_HAZARD）指一条 Hazard 混合多个相互独立的检查义务。",
    "> 拆分必须保持来源可追踪（V3 原文/Hazard 原实体），不得改变原始历史含义。",
    "> 拆分完成后需重审对应 link 角色（direct/supporting/fallback）并重绑 review hash。",
    "",
    "| # | Hazard ID | 混合义务与拆分建议 | 相关 Link |",
    "|---|---|---|---|",
]
for i, (hid, desc) in enumerate(sorted(SPLIT_TASKS.items()), 1):
    rids = "、".join(split_lines.get(hid, []))
    lines.append(f"| {i} | `{hid}` | {desc} | {rids} |")
lines.append("")
io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "V4_HAZARD_SPLIT_TASKS.md"),
        "w", encoding="utf-8").write("\n".join(lines))

print("reviews updated:", changed)
print("hazards noted:", haz_changed)
print("contexts rebound:", rebound)
print("split tasks:", len(SPLIT_TASKS))
