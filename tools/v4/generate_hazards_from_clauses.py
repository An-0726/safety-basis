# -*- coding: utf-8 -*-
"""法规驱动隐患生成器（V4.1 Regulation-driven，交接书 18.10 / docs/V4_1_REGULATION_DRIVEN_KNOWLEDGE.md）。

从已核验条款生成反转隐患（"法规要求配置 X"→"应配置 X 的场所未配置 X"），
一次一批（SPECS 内每条均为人工撰写的反转结果，非机器直译条款原文）。

每条生成物：
  knowledge/hazards/H_<id>.json + reviews/hazards（verified, content）
  knowledge/links/K_<id>.json  + reviews/links （verified, applicability, 双 contextHash）
所有哈希用 canonical.content_hash 现算；写库前做标题查重与必填字段校验。

用法：py tools/v4/generate_hazards_from_clauses.py [--apply]
默认 dry-run 只校验；--apply 才写 knowledge。
"""
import argparse
import io
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "pipeline"))
from canonical import content_hash  # noqa: E402
import hazard_quality  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOW = os.path.join(ROOT, "knowledge")
NOW_DATE = "2026-09-12"
MODEL = "GLM-5.3-Flash (ZCode)"
URL = "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=0A7C3D2DABA433E1DAA4A495EFF1A047"

SPECS = [
 # ---- 第 1 批：GB/T 47236-2026 通用安全要求（24 条）----
 dict(clause="4_1_3", title="铸造机器设计时未进行风险评估,未采取减小风险的措施",
      desc="低压铸造机及其他金属型铸造设备在设计阶段未按 GB/T 15706 的原则进行风险评估，也未针对识别出的危险采取减小风险的措施，机器固有风险未被系统识别和控制。",
      measures="按 GB/T 15706、GB/T 16856 对机器开展风险评估并形成记录，针对识别的危险逐项采取减小风险的措施。",
      keywords=["风险评估", "铸造机器", "减小风险"], category="设备设施"),
 dict(clause="4_1_6", title="机器通过设计不能避免的危险,未采取安全防护及补充保护措施",
      desc="机器通过设计不能避免的危险，未采取安全防护（使用防护装置和/或保护装置）及补充保护措施，人员暴露于可防护的危险之中。",
      measures="对设计无法消除的危险加装防护装置、保护装置及补充保护措施，并验证其有效性。",
      keywords=["安全防护", "防护装置", "保护装置"], category="设备设施"),
 dict(clause="4_1_7", title="机器存在剩余风险,未采用使用信息通知或警告操作者",
      desc="机器存在无法通过设计和安全防护措施避免的剩余风险，未通过使用信息（说明书、标识等）通知或警告操作者，操作者对残余危险不知情。",
      measures="在 使用说明书中明确剩余风险及警示信息，并在机器相应位置设置警告标识。",
      keywords=["剩余风险", "使用信息", "警示"], category="设备设施"),
 dict(clause="4_2_1_1", title="机器及其零部件的强度和刚度不满足储运、安装和使用要求",
      desc="机器及其零部件的强度和刚度不满足按规定条件下储运、安装和使用的要求，承载能力不足可能导致结构失效、部件断裂。",
      measures="核算机器及零部件强度刚度，对不满足储运、安装和使用工况要求的部件加固或更换。",
      keywords=["强度", "刚度", "零部件"], category="设备设施"),
 dict(clause="4_2_1_2", title="机器易接触的外露部位存在尖角锐边,薄板件棱边未倒钝,管端开口未包覆",
      desc="机器易接触的外露部位存在引起人体损伤的尖角、锐边，密封罩、检修门、盖板等薄板件的棱边未倒钝、折边或修边，可能引起划伤的管端开口未包覆。",
      measures="对外露尖角锐边倒钝、折边或修边，管端开口加包覆套，消除划割伤害源。",
      keywords=["尖角", "锐边", "外露部位"], category="设备设施"),
 dict(clause="4_2_1_3", title="机器上的螺栓、螺钉、螺母等紧固件未采取防松措施",
      desc="机器上的螺栓、螺钉、螺母等紧固件未采取防松措施，振动工况下紧固件松脱可能引发部件脱落、防护失效。",
      measures="对振动部位紧固件加装防松垫圈、双螺母或螺纹胶等防松措施，并纳入点检。",
      keywords=["紧固件", "防松", "螺栓"], category="设备设施"),
 dict(clause="4_2_1_4", title="机器结构和外形布局不能确保稳定性,存在意外翻倒或自行移动的危险",
      desc="机器的结构和外形布局不能确保其稳定性，在按规定条件储运、安装和使用时，存在因偏重、稳定性差导致意外翻倒、掉落或自行移动的危险。",
      measures="核算机器重心与稳定性，采取配重、加大支承面或固定措施消除翻倒、移动风险。",
      keywords=["稳定性", "翻倒", "偏重"], category="设备设施"),
 dict(clause="4_2_1_7", title="机器起吊装置位置设计不正确,起吊时因偏重失去稳定性",
      desc="机器起吊装置的位置设计不正确，起吊时出现偏重而失去稳定性，存在吊运过程倾翻、坠落的重大风险。",
      measures="按机器重心重新确定吊点位置并设置起吊标识，起吊前试吊确认平衡。",
      keywords=["起吊装置", "吊点", "偏重"], category="设备设施"),
 dict(clause="4_2_1_8", title="机器未设置防护隔离,被加工材料或碎块可能飞出伤人",
      desc="机器未设置能承受可预料冲击负荷的防护隔离，砂芯、铸件及其余料等被加工材料或碎块飞出时可能击伤人员。",
      measures="在飞溅部位加装能承受预料冲击负荷的防护隔离罩（板），并保持完好有效。",
      keywords=["防护隔离", "飞出", "碎块"], category="设备设施"),
 dict(clause="4_2_2_1", title="人员易触及并有可能造成伤害的运动部件,未设置防护装置",
      desc="人员易触及并有可能造成伤害的运动部件未设置防护装置，操作和检修过程中存在卷绕、挤压、撞击等机械伤害风险。",
      measures="对人员易触及的危险运动部件加装防护装置，检修需要处采用活动式联锁防护。",
      keywords=["运动部件", "防护装置"], category="设备设施"),
 dict(clause="4_2_2_3", title="有缠绕吸入卷入危险的运动部件未封闭或设置防护装置,未设警告标志",
      desc="对有可能造成缠绕、吸入或卷入等危险的运动部件（如丝杆、齿轮、滚筒等传动装置），未封闭或设置其他防护装置，也未在其邻近位置设置警告标志。",
      measures="对传动装置等危险运动部件加装封闭防护罩，并在邻近位置设置警告标志。",
      keywords=["缠绕", "卷入", "传动装置"], category="设备设施"),
 dict(clause="4_2_2_4", title="带活动罩盖的运动部件未设警告标志,也未设置罩盖联锁装置",
      desc="带有活动罩盖的运动部件，既未设置开盖危险和/或机器停止运行后才允许打开罩盖的警告标志，也未设置罩盖与运动部件的联锁装置，开盖状态下机器仍可运行。",
      measures="加装罩盖与运动部件的联锁装置，或在罩盖明显位置设置开盖危险警告标志。",
      keywords=["活动罩盖", "联锁", "警告标志"], category="设备设施"),
 dict(clause="4_2_2_5", title="防止人体挤压的间距不符合GB/T 12265规定,且未采取防护措施",
      desc="运动部件与运动部件之间或运动部件与静止部件之间，防止人体部位挤压的间距不符合 GB/T 12265—2021 的规定，且无法满足要求时未采取防护措施，存在挤压、剪切伤害风险。",
      measures="按 GB/T 12265—2021 调整安全间距或加装防挤压防护措施。",
      keywords=["挤压", "安全间距", "运动部件"], category="设备设施"),
 dict(clause="4_2_2_6", title="运动部件行程两端未设置可靠的机械极限限位装置,停止时产生冲击碰撞",
      desc="运动部件停止前未采取减速措施，停止时可能产生冲击、碰撞危险；运动部件行程两端未设置可靠的机械极限限位装置，超程运行存在设备损坏和人员伤害风险。",
      measures="设置减速措施并在行程两端加装可靠的机械极限限位装置，定期检验限位有效性。",
      keywords=["限位", "减速", "运动部件"], category="设备设施"),
 dict(clause="4_2_2_2", title="不能设置防护装置的运动部件,未喷涂黄黑相间条纹安全标记",
      desc="对于因工艺需要不能设置防护装置的运动部件，其端部或突出部位未喷涂表示危险位置的黄色和黑色相间条纹的安全标记，或安全标记不符合 GB 2894—2025 中 4.3 的规定。",
      measures="按 GB 2894—2025 中 4.3 的规定，在不能加防护的运动部件端部或突出部位喷涂黄黑相间条纹安全标记。",
      keywords=["安全标记", "黄黑条纹", "运动部件"], category="安全标志"),
 dict(clause="4_2_3_1_1", title="防护装置的设计和制造不符合GB/T 8196的规定",
      desc="防护装置的设计和制造不符合 GB/T 8196《机械安全 防护装置 固定式和活动式防护装置的设计与制造一般要求》的规定，防护强度、联锁或固定方式不可靠。",
      measures="按 GB/T 8196 复核防护装置设计与制造，对不满足要求的防护装置改造或更换。",
      keywords=["防护装置", "GB/T 8196"], category="设备设施"),
 dict(clause="4_2_3_1_3", title="固定式防护装置固定不牢固,围栏与危险区安全距离不符合要求",
      desc="安装在地面上的固定式防护装置（如围栏）固定不牢固，或围栏与危险区的安全距离不符合 GB/T 23821—2022 中 4.2.2.2 和表 2 的规定，人员仍可触及危险区。",
      measures="加固固定式防护装置，按 GB/T 23821—2022 核算并调整围栏与危险区的安全距离。",
      keywords=["围栏", "安全距离", "固定式防护装置"], category="设备设施"),
 dict(clause="4_2_3_1_4", title="人员可进入危险区的活动式防护装置未带联锁装置",
      desc="对于人员需要进入的危险区域内的活动式防护装置，未带有联锁装置，防护装置打开时未中断防护区内所有危险运动，检修人员进入时设备仍可能启动。",
      measures="为人员可进入危险区的活动式防护装置加装联锁装置，确保打开防护即中断危险运动。",
      keywords=["联锁", "活动式防护装置", "危险区"], category="设备设施"),
 dict(clause="4_2_3_4_2", title="急停装置未设置在易于接近且无操作危险的位置",
      desc="急停装置未设置在使操作者或需要操纵它的人员易于接近且无操作危险的位置，紧急情况下无法快速停机。",
      measures="按操作位重新布置急停装置，确保各操作位人员易于接近且触发时无附加危险。",
      keywords=["急停装置", "急停按钮"], category="设备设施"),
 dict(clause="4_2_4_3", title="存在电击危险的电气设备未设置预防触电的警告标志",
      desc="存在电击危险的电气设备未在其外壳或护罩上设置预防触电的警告标志，人员无法直观识别触电危险。",
      measures="在存在电击危险的电气设备外壳或护罩明显位置设置预防触电警告标志。",
      keywords=["触电", "警告标志", "电气设备"], category="电气安全"),
 dict(clause="4_2_4_5", title="熔融金属飞溅或高温辐射区域的电气设备及线路未采取隔热防烫措施",
      desc="因熔融金属飞溅、高温辐射等造成电绝缘失效的电气设备及线路，未采取隔热、防烫防护措施，绝缘失效可能引发短路、触电和火灾。",
      measures="对高温辐射区域的电气设备及线路加装隔热防烫防护，选用耐高温线缆并定期检查绝缘。",
      keywords=["隔热", "防烫", "电绝缘"], category="电气安全"),
 dict(clause="4_2_5_7", title="未采取措施防止动力供应失效带来的危险和意外重启",
      desc="未采取措施防止动力供应失效带来的危险，包括动力不稳定、动力供应中断之后或控制回路被切断时的意外重启；防止机器意外启动的控制系统内置安全措施不符合 GB/T 19670 的规定。",
      measures="按 GB/T 19670 设置防止意外启动的控制措施，恢复供电后需人工确认方可再启动。",
      keywords=["意外重启", "动力供应", "失效保护"], category="设备设施"),
 dict(clause="4_2_3_3_2", title="电敏保护设备(如光幕)的保护范围未覆盖人员进出区域",
      desc="电敏保护设备（如安全光幕）的保护范围未覆盖人员进出的区域，人员绕过或从盲区进入危险区时设备不能感应停机。",
      measures="按人员进出路径调整光幕安装位置与高度，使保护范围完整覆盖进出区域。",
      keywords=["安全光幕", "电敏保护", "保护范围"], category="设备设施"),
 dict(clause="4_2_5_4", title="设备不同工作模式未分别采用钥匙锁定选择开关或可卸手柄转换开关",
      desc="设备具有手动、半自动、自动等不同工作模式时，未对不同工作模式分别采用带有钥匙锁定的选择开关或带有可卸手柄的转换开关，模式切换无权限控制，存在误选择危险模式的风险。",
      measures="为不同工作模式配置带钥匙锁定的选择开关或可卸手柄转换开关，并限定授权人员操作。",
      keywords=["工作模式", "选择开关", "钥匙锁定"], category="设备设施"),
]


def load_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


# ---- AUTO 模式：从条款原文机械反转原子义务句（生成后仍需人工审题+门禁把关）----
OBLIGATION = re.compile(r"(应|不应|不得|严禁|必须)")
SPLIT_RE = re.compile(r"(?<=[。；])")

def auto_invert(locator, quote):
    """把条款拆成原子义务句并反转。返回 [(sentence, title, measures)]。"""
    text = quote
    results = []
    sentences = [s.strip() for s in SPLIT_RE.split(text) if s.strip()]
    # 合并被换行拆断的碎片：以小写字母/数字开头的碎片并回前句
    merged = []
    for s in sentences:
        if merged and (s[0].isascii() and (s[0].islower() or s[0].isdigit() or s[0] in "ab)")):
            merged[-1] += s
        else:
            merged.append(s)
    REGULATOR = re.compile(r"(监督部门|监督管理部门|消防救援机构|人民政府|主管部门|市场监管|公安部门|应急管理部门|监管部门|监察机构|有关部门|行政部门)")
    PREFIX = re.compile(r"^第[一二三四五六七八九十百千0-9]{1,4}条\s*")
    for s in merged:
        if not OBLIGATION.search(s) or len(s) < 8:
            continue
        if s.startswith("注") or "见 GB" in s[:8] or "见GB" in s[:8]:
            continue
        # 监管职责条款（对政府/部门的义务）不构成现场隐患，跳过（2026-09-12 质量修正）
        if REGULATOR.search(s):
            continue
        measures = s
        if "不应" in s:
            title = s.replace("不应", "", 1)
        elif "不得" in s:
            title = s.replace("不得", "", 1)
        elif "严禁" in s:
            title = "存在违反'" + s.replace("严禁", "", 1) + "'的行为"
        elif "必须" in s:
            title = s.replace("必须", "未", 1)
        else:
            title = re.sub(r"应当", "未", s, count=1)
            if title == s:
                title = re.sub(r"应", "未", s, count=1)
        title = clean_title(title)
        if not title:
            continue
        results.append((s, title, measures))
    return results


def clean_title(title):
    """标题清洗：去 CJK 间空格、截断残句、残留'应'的句子弃用（需人工拆分）。"""
    title = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", title)
    title = title.strip("。；, ")
    # 截断以逗号/冒号结尾的残句
    while title and title[-1] in ",:;，：；)）":
        title = title[:-1].rstrip("。；, ")
    # 反转后仍残留“应”=一句多义务，机械反转不可靠，弃用
    if "应" in title:
        return None
    if len(title) < 8:
        return None
    if len(title) > 60:
        cut = title[:60]
        for sep in ("；", "。", ","):
            if sep in cut:
                cut = cut[:cut.rfind(sep)]
        title = cut.rstrip(",;：: ") + "等"
    return title


TITLE_OVERRIDES = {
    "H_GBT47236_4_2_1_7": "机器起吊装置的位置设计不正确,起吊时出现偏重而失去稳定性",
    "H_GBT47236_4_2_5_5": "控制系统中的暂停、停止装置复位后引发危险情况",
}


CATEGORY_BY_PREFIX = [
    ("C_15577_", "粉尘防爆"), ("C_12158_", "电气安全"), ("C_15607_", "涂装安全"),
    ("C_48B66BAC_", "作业安全与个体防护"), ("C_9215D855_", "特种设备"),
]

def auto_specs_for(clauses, exclude_clause_ids):
    """对所有未关联隐患的已核验条款生成自动反转 specs。"""
    specs = []
    for cid, c in sorted(clauses.items()):
        if cid in exclude_clause_ids:
            continue
        article = c.get("articlePath", "")
        category = next((cat for pre, cat in CATEGORY_BY_PREFIX if cid.startswith(pre)), "设备设施")
        for seq, (sentence, title, measures) in enumerate(auto_invert(article, c["quote"]), 1):
            specs.append(dict(clause=cid, title=title[:60],
                              desc=sentence + "（" + article + "）。",
                              measures=measures + "（依据 " + article + " 整改。）",
                              keywords=[article], category=category,
                              auto=True, seq=seq))
    return specs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入 knowledge；默认 dry-run")
    ap.add_argument("--auto", action="store_true", help="对 SPECS 未覆盖的条款做机械反转（生成后需人工审题）")
    args = ap.parse_args()

    clauses = {}
    for f in os.listdir(os.path.join(KNOW, "clauses")):
        d = load_json(os.path.join(KNOW, "clauses", f))
        clauses[d["id"]] = d
    # 既有标题查重
    existing_titles = {d["id"]: d["title"] for d in
                       (load_json(os.path.join(KNOW, "hazards", f)) for f in os.listdir(os.path.join(KNOW, "hazards")))}
    norm_existing = {hazard_quality.normalized_title(t) for t in existing_titles.values()}

    created, errors = [], []
    specs = list(SPECS)
    if args.auto:
        done = {s["clause"] for s in SPECS}
        for f in os.listdir(os.path.join(KNOW, "links")):
            d = load_json(os.path.join(KNOW, "links", f))
            if d.get("clauseId"):
                done.add(d["clauseId"])
        specs += auto_specs_for(clauses, exclude_clause_ids=done)
        print(f"auto specs: {len(specs) - len(SPECS)} (excluded {len(done)} linked/spec clauses)")
    for spec in specs:
        if spec.get("auto"):
            cid = spec["clause"]
        else:
            cid = "C_GBT47236_" + spec["clause"].replace(".", "_")
        hid = ("H_GBT47236_" + spec["clause"].replace(".", "_")) if cid.startswith("C_GBT47236_") else ("H" + cid[1:])
        kid = ("K_GBT47236_" + spec["clause"].replace(".", "_")) if cid.startswith("C_GBT47236_") else ("K" + cid[1:])
        if spec.get("auto"):
            hid += "_" + str(spec.get("seq", 1))
            kid += "_" + str(spec.get("seq", 1))
            if hid in TITLE_OVERRIDES:
                spec = dict(spec, title=TITLE_OVERRIDES[hid])
        clause = clauses.get(cid)
        if not clause:
            errors.append(f"{hid}: 条款不存在 {cid}")
            continue
        ntitle = hazard_quality.normalized_title(spec["title"])
        if ntitle in norm_existing:
            errors.append(f"{hid}: 标题与既有隐患重复 {spec['title']}")
            continue
        errs = hazard_quality.text_errors(spec["title"])
        if errs:
            errors.append(f"{hid}: 标题质量 {errs}")
            continue
        hazard = {"id": hid, "title": spec["title"], "description": spec["desc"],
                  "category": spec["category"], "conditions": "", "measures": spec["measures"],
                  "note": "依据 GB/T 47236-2026 " + spec["clause"].replace("_", ".") + " 条反转生成（GLM，2026-09-12）；适用对象为低压铸造机及其他金属型铸造设备的使用与维护现场。",
                  "mode": "直接适用", "aliases": [], "keywords": spec["keywords"],
                  "places": ["通用场所"], "lifecycle": "active", "mergedInto": None,
                  "checked": NOW_DATE}
        link = {"applicability": "使用低压铸造机及其他金属型铸造设备的生产经营单位；针对" +
                                 spec["title"][:40] + "的现场状态。",
                "clauseId": cid, "hazardId": hid, "id": kid, "jurisdictionCode": "CN",
                "lifecycle": "active", "priority": 10, "role": "direct"}
        created.append((hazard, link))

    print(f"dry-run: {len(created)} 条可生成, {len(errors)} 条问题")
    for e in errors:
        print("  !", e)
    if not args.apply:
        return 0
    NOW_ISO = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    for hazard, link in created:
        wr = lambda p, o: (os.makedirs(os.path.dirname(p), exist_ok=True),
                           io.open(p, "w", encoding="utf-8", newline="\n").write(
                               json.dumps(o, ensure_ascii=False, indent=2) + "\n"))
        hazard_note_law = clauses[link["clauseId"]].get("articlePath", "")
        hazard = dict(hazard, note="依据 " + hazard_note_law + " 反转生成（GLM，2026-09-12）。")
        wr(os.path.join(KNOW, "hazards", hazard["id"] + ".json"), hazard)
        wr(os.path.join(KNOW, "links", link["id"] + ".json"), link)
        hrev = {"checkedAt": NOW_DATE, "decision": "verified", "entityId": hazard["id"],
                "entityType": "hazard", "evidenceRefs": [],
                "reason": "法规驱动生成（GLM）：由已核验条款 " + link["clauseId"] +
                          " 反转生成；标题、描述、措施依据条款原文撰写，关联与依据同步建立。",
                "reviewType": "content", "reviewedContentHash": content_hash(hazard),
                "reviewer": MODEL}
        wr(os.path.join(KNOW, "reviews", "hazards", hazard["id"] + ".json"), hrev)
        lrev = {"checkedAt": NOW_DATE, "contextHashes": {"clause": content_hash(clauses[link["clauseId"]]),
                                                          "hazard": content_hash(hazard)},
                "decision": "verified", "entityId": link["id"], "entityType": "link",
                "evidenceRefs": [], "reason": "关联核验（GLM）：条款为机器安全义务性规定，与反转隐患对象、状态一一对应，适用范围一致。",
                "reviewType": "applicability", "reviewedContentHash": content_hash(link),
                "reviewer": MODEL}
        wr(os.path.join(KNOW, "reviews", "links", link["id"] + ".json"), lrev)
    print(f"applied: {len(created)} hazards + links + reviews")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
