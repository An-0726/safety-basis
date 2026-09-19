# -*- coding: utf-8 -*-
"""Finalize PHASE 6 candidate evidence rebind conservatively.

This tool closes the PHASE 6 review queue without forcing every candidate into
active publication.  Every currently-proposed hazard receives a deterministic
final disposition.  Only an explicit, manually-reviewed allow-list is promoted;
all remaining records stay proposed with an auditable hold reason.

The tool never touches the private SQLite/library, stable hazard IDs, release
artifacts, pull requests, Pages, or deployment state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "tools" / "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate  # noqa: E402

AS_OF = "2026-09-16"
REVIEWER = "ChatGPT PHASE6 final review 20260916"
JS_URL = "https://www.jsrd.gov.cn/qwfb/sjfg/202406/t20240604_1221284.shtml"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8", newline="\n")


def load_dir(rel: str) -> dict[str, dict]:
    out = {}
    for p in (KNOW / rel).glob("*.json"):
        obj = read_json(p)
        out[obj.get("id") or obj.get("entityId") or p.stem] = obj
    return out


def load_jsonl_records(path: Path) -> tuple[dict | None, list[dict]]:
    meta = None
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if obj.get("recordType") == "metadata" and meta is None:
            meta = obj
        else:
            rows.append(obj)
    return meta, rows


def make_review(entity: dict, entity_type: str, evidence_refs: list[str], review_type: str, reason: str) -> dict:
    return {
        "checkedAt": AS_OF,
        "decision": "verified",
        "entityId": entity["id"],
        "entityType": entity_type,
        "evidenceRefs": list(dict.fromkeys(evidence_refs)),
        "reason": reason,
        "reviewType": review_type,
        "reviewedContentHash": content_hash(entity),
        "reviewer": REVIEWER,
    }


def ensure_current_jiangsu_risk_regulation() -> None:
    """Register the 2024 Jiangsu risk-management regulation and four direct clauses."""
    law = {
        "aliases": ["江苏省安全风险管理条例"],
        "canonicalName": "江苏省生产经营单位安全风险管理条例",
        "documentKind": "地方性法规",
        "id": "LF_REG_JS_RISK_MGMT_2024",
        "identityKey": "cn-32:江苏省生产经营单位安全风险管理条例",
        "issuer": "江苏省人民代表大会常务委员会",
        "jurisdictionCode": "CN-32",
        "lifecycle": "active",
    }
    lv = {
        "documentNumber": "",
        "effectiveDate": "2024-11-01",
        "endDate": "",
        "id": "LV_REG_JS_RISK_MGMT_2024",
        "lawId": law["id"],
        "level": "地方性法规",
        "officialName": "江苏省生产经营单位安全风险管理条例",
        "scope": "CN-32",
        "sourceUrl": JS_URL,
        "validityStatus": "active",
        "versionKey": "2024-05-29",
    }
    quotes = {
        "C_JS_RISK_MGMT_2024_8": ("第八条", "第八条 生产经营单位应当制定安全风险分级管控制度，明确安全风险辨识、评估的程序、方法以及分级管控职责分工等内容。"),
        "C_JS_RISK_MGMT_2024_11": ("第十一条", "第十一条 生产经营单位对辨识出的安全风险，应当按照安全风险等级实施分级管控，根据其特点从组织、技术、管理、应急等方面制定并落实管控措施，编制安全风险管控清单。管控措施应当符合相关法律、法规和标准规范要求。\n安全风险管控清单应当载明安全风险的名称、风险点、所处位置（场所、部位、环节）、等级、可能导致的事故类型、管控措施以及责任部门、责任人等信息。"),
        "C_JS_RISK_MGMT_2024_12": ("第十二条", "第十二条 有下列情形之一的，生产经营单位应当及时组织开展针对性的安全风险辨识、评估，确定或者调整安全风险等级，完善管控措施：\n（一）目录调整的；\n（二）国家和省对安全风险辨识、管控有新要求的；\n（三）生产工艺流程、主要设备设施、主要生产物料发生改变的；\n（四）需要开展安全风险辨识、评估的其他情形。\n生产经营单位发生死亡一人以上或者重伤三人以上的生产安全事故的，应当及时组织开展全面、系统的安全风险辨识、评估，完善管控措施。"),
        "C_JS_RISK_MGMT_2024_16": ("第十六条", "第十六条 生产经营单位应当在本单位醒目位置公示较大以上安全风险的名称、风险点、所处位置（场所、部位、环节）、等级、可能导致的事故类型以及责任部门、责任人和监督电话等信息。\n生产经营单位可以绘制“红橙黄蓝”四色安全风险空间分布图，公示全部安全风险。"),
    }
    snapshot_text = "\n".join(q for _a, q in quotes.values())
    evidence = {
        "id": "E_JS_RISK_MGMT_2024",
        "locator": "《江苏省生产经营单位安全风险管理条例》江苏人大官方全文；2024年5月29日通过，2024年11月1日起施行。本证据记录本批实际使用的第八、十一、十二、十六条逐字文本。",
        "page": "官方HTML全文",
        "retrievedAt": "2026-09-16T00:00:00+08:00",
        "snapshotSha256": hashlib.sha256(snapshot_text.encode("utf-8")).hexdigest(),
        "tier": "authoritative-public",
        "url": JS_URL,
    }
    clauses = []
    for cid, (article, quote) in quotes.items():
        clauses.append({
            "articlePath": article,
            "id": cid,
            "jurisdictionCode": "CN-32",
            "lawVersionId": lv["id"],
            "lifecycle": "active",
            "quote": quote,
            "sourceUrl": JS_URL,
        })

    write_json(KNOW / "laws" / f"{law['id']}.json", law)
    write_json(KNOW / "law-versions" / f"{lv['id']}.json", lv)
    write_json(KNOW / "evidence" / f"{evidence['id']}.json", evidence)
    write_json(KNOW / "reviews" / "laws" / f"{law['id']}.json", make_review(law, "law", [evidence["id"]], "identity", "江苏人大官方全文确认法规身份、制定机关和现行效力。"))
    write_json(KNOW / "reviews" / "law-versions" / f"{lv['id']}.json", make_review(lv, "law_version", [evidence["id"]], "version", "江苏人大官方全文确认2024年5月29日通过、2024年11月1日起施行。"))
    for clause in clauses:
        write_json(KNOW / "clauses" / f"{clause['id']}.json", clause)
        write_json(KNOW / "reviews" / "clauses" / f"{clause['id']}.json", make_review(clause, "clause", [evidence["id"]], "text", "逐字核对江苏人大官方全文。"))


# Only these exact objects have been independently checked for semantic scope in
# this PHASE 6 closeout.  Exact locator matches not in this table stay proposed.
PROMOTE: dict[str, dict] = {
    "H077": {"clause": "C_JGJ91_5_3_3", "applicability": "适用于使用强酸、强碱等存在化学品危险隐患的实验室。", "reason": "JGJ 91-2019第5.3.3条逐字要求就近设置应急洗眼器及应急喷淋，与隐患对象直接一致。"},
    "H_06CDCD67E7334680ABAC68431F": {"clause": "C_BDCBE6EE490CAEE5018F4F785A", "applicability": "适用于生产、经营、运输、储存、使用危险物品或者处置废弃危险物品的生产经营单位。", "reason": "《安全生产法》第三十九条对危险物品专门安全管理制度和可靠安全措施作出直接义务。"},
    "H_85FD7EA977B245058865D2E9B1": {"clause": "C039", "applicability": "适用于依法需要取得相应资格方可上岗的特种作业人员。", "reason": "《安全生产法》第三十条对特种作业人员专门培训并取得相应资格作出直接义务。"},
    "H_75F808A9B19847B9B052799971": {"clause": "C_90478B08DF6F7C6B8A9FE71B21", "applicability": "适用于生产经营单位依法参加工伤保险并为从业人员缴纳保险费。", "reason": "《安全生产法》第五十一条与隐患对象直接一致。"},
    "H_00DB7A50FF994B5DB5470A3B03": {"clause": "C_JS_RISK_MGMT_2024_16", "applicability": "适用于江苏省行政区域内生产经营单位的较大以上安全风险公示。", "reason": "2024年《江苏省生产经营单位安全风险管理条例》第十六条直接要求在醒目位置公示较大以上安全风险信息。"},
    "H_8DB944621AC043EF8758F7D4C3": {"clause": "C_JS_RISK_MGMT_2024_11", "applicability": "适用于江苏省行政区域内生产经营单位编制安全风险管控清单。", "reason": "2024年《江苏省生产经营单位安全风险管理条例》第十一条直接要求编制安全风险管控清单并列明规定信息。"},
    "H_DC6AE2637C1549ECA1FEB8F087": {"clause": "C_JS_RISK_MGMT_2024_8", "applicability": "适用于江苏省行政区域内生产经营单位建立安全风险分级管控制度。", "reason": "2024年《江苏省生产经营单位安全风险管理条例》第八条直接要求制定安全风险分级管控制度。"},
    "H_F8BD176AF46643EA9E3CC56A6F": {"clause": "C_GBT47236_4_2_2_3", "applicability": "适用于GB/T 47236-2026范围内、存在缠绕、吸入或卷入危险的运动/传动部件。", "reason": "第4.2.2.3条直接要求相关运动部件封闭或设置其他防护装置。"},
    "H_765CF0360EC54F0AA93C341B77": {"clause": "C_GB50187_4_3_5", "applicability": "适用于工业企业厂外道路规划及其与国家公路、城镇道路的连接。", "reason": "GB 50187-2012第4.3.5条与厂外道路规划、连接对象直接一致。"},
    "H_DC071E7B998C40CB8E96074401": {"clause": "C_GB5083_6_2_1", "applicability": "适用于高速旋转零部件的防护罩设计以及检查周期、更新标准。", "reason": "GB 5083-2023第6.2.1条逐字覆盖防护罩和检查/更换标准。"},
    "H_14FF17559BF1415B9F0007905D": {"clause": "C_PDDB_7", "applicability": "适用于机械企业铸造用熔炼炉、精炼炉、保温炉重大事故隐患判定。", "reason": "《工贸企业重大事故隐患判定标准》第七条第二项与隐患文本直接一致。"},
    "H_96106D7519F84C2DA149BB5819": {"clause": "C_PDDB_11", "applicability": "适用于存在可燃性金属粉尘的工贸企业除尘系统重大事故隐患判定。", "reason": "《工贸企业重大事故隐患判定标准》第十一条对应金属粉尘正压除尘/吹送及火花探测消除要求。"},
    "H_C372C4B450D94D7CACD38CDBD0": {"clause": "C_GB55037_3_4_5_1", "applicability": "适用于消防车道或兼作消防车道道路的转弯半径。", "reason": "GB 55037-2022第3.4.5条第2项直接要求转弯半径满足消防车转弯要求。"},
    "H_3DF895C1974245A29D51728DA7": {"clause": "C_GB50187_5_7_4", "applicability": "适用于工业企业主要货流出入口的布置。", "reason": "GB 50187-2012第5.7.4条第2项逐字覆盖主要货流方向、仓库堆场和外部运输线路连接。"},
    "H_2303005CE94D49BD88F75C7DC7": {"clause": "C_GB50187_7_1_2", "applicability": "适用于分期建设工业企业工程的竖向设计。", "reason": "GB 50187-2012第7.1.2条第8项逐字覆盖近期与远期工程在标高、坡度、排水方面协调。"},
    "H_CB60731890BF4F388E3225E634": {"clause": "C_GB50187_5_1_8", "applicability": "适用于工业企业总平面布置中的货流、人流及运输线路组织。", "reason": "GB 50187-2012第5.1.8条直接要求物流顺畅、径路短捷、不折返并合理组织人货流。"},
    "H_12158_10_2_1": {"clause": "C_12158_10_2", "applicability": "适用于静电危险场所工作人员需要使用手套的情形。", "reason": "GB 12158-2024第10.2条逐字要求所用手套的防静电性能符合GB/T 22845。"},
    "H_GBT47236_4_2_3_2_1_1": {"clause": "C_GBT47236_4_2_3_2_1", "applicability": "适用于GB/T 47236-2026范围内与防护装置相关的联锁装置选择和设计。", "reason": "第4.2.3.2.1条逐字要求联锁装置选择和设计符合GB/T 18831。"},
    "H_5D5ACB4A6D45FD9CEFC4654D": {"clause": "C035", "applicability": "适用于依法应进行定期检验的特种设备。", "reason": "《中华人民共和国特种设备安全法》第四十条直接规定未经定期检验或者检验不合格的特种设备不得继续使用。"},
    "H_0FA260A469ACC3B5EFA777ABAB_1": {"clause": "C_SANTONGSHI_17", "applicability": "适用于矿山、金属冶炼及生产、储存、装卸危险物品建设项目安全设施施工。", "reason": "《建设项目安全设施“三同时”监督管理办法》第十七条与未按批准安全设施设计施工对象直接一致。"},
}

HOLD_OVERRIDES: dict[str, tuple[str, str]] = {
    "H_EACC1ED8867C4F3DA5FBAC8B49": ("wording_strength_mismatch", "hazard使用“不得/禁止选址”，GB 50187-2012第3.0.14条原文为“不应选为厂址”；在修正规范措辞前不建立正式关联。"),
    "H_315C5D031AFC4502B69ACB9F38": ("multi_object_rebind_required", "同一hazard混合消防车道、人员紧急疏散和道路错车三个对象，现有第5.1.4条不能整体覆盖。"),
    "H_7B7329352589412BBC6B7121D0": ("recommended_wording_not_absolute", "GB 50187-2012第5.7.4条对出入口数量使用“不宜少于2个”，不能把少于2个机械写成绝对违法。"),
    "H_C50168CA681E44F4B795F32BF0": ("conditional_scope_not_resolved", "GB 50187-2012第5.1.6条中“避免西晒”仅适用于高温、热加工、有特殊要求和人员较多的建筑物，当前hazard合并表述过宽。"),
    "H_70E93B89545343998BEDFB6893": ("current_numeric_requirement_mismatch", "GB 55037-2022第3.4.5条现行原文规定消防车道坡度不应大于10%，不能支撑“坡度大于8%”的现有阈值。"),
    "H_7F41DF4810BA4E8C876859430B": ("current_numeric_requirement_absent", "GB 55037-2022第3.4.5条要求与外墙水平距离满足安全通行，但没有现有hazard中的固定5m阈值。"),
    "H_12158_3_1": ("scope_overbroad", "GB 12158-2024第8.5.5条的静置时间具有特定油舱/容积条件，不能支撑泛化的“易燃液体作业前至少30min”。"),
    "H_12158_7_6_1": ("clause_text_quality_anomaly", "当前knowledge中的第7.6条原文出现指数/结尾截断异常；在重新取得完整逐字原文前不进入正式链。"),
    "H_FC60ED3C946F4F18B89455526A": ("clause_object_mismatch", "GB/T 47236-2026第4.2.5.7条针对动力供应失效和意外重启，不能直接支撑“防松脱或防护装置”表述。"),
    "H_B5E5670E989F4955969803EF66": ("update_duty_not_explicit", "现有公示条款规定应公示的信息，但没有直接规定风险变更后的公示栏更新时间。"),
    "H_93E3E0EF2F34424185541915DA": ("update_duty_not_explicit", "现有公示条款规定应公示的信息，但没有直接规定风险变更后的公示栏更新时间。"),
    "H_AB6ECCCE1E89469C92E2DEA6C5": ("wrong_clause_object", "原候选第十六条是公示义务，不能支撑“未建立安全风险档案”。"),
    "H_417B030F12A14923A978E4DAB2": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条是粉尘清理及废物处置义务，不能支撑多套废气收集系统。"),
    "H_6459FF72A542499FBB3E0F70FC": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条不是过滤装置压差检测条款。"),
    "H_1B2F6A143A9E492DBA2A246473": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条不能支撑集气罩与生产工艺协调要求。"),
    "H_0F065B25BAC84C329610C8FBF8": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条不能支撑一般生产设备有害气体密闭/净化排放要求。"),
    "H_8C14C2BD0D4A4EF1B42FDC8C2E": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条针对可燃性粉尘清理，不能泛化支撑普通机加工废屑容器。"),
    "H_AA7C48BCF0E6458484759F407B": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条不能支撑作业场所选址/污染源风向要求。"),
    "H_A1DD3641D23C4DCB92FFE32354": ("wrong_clause_object", "《工贸企业粉尘防爆安全规定》第十八条不能支撑除尘系统启动/延时停机联锁逻辑。"),
    "H072": ("mixed_object_partial_basis", "现有候选把电气作业PPE与特种作业资格管理合并，《安全生产法》第四十五条仅能覆盖PPE义务，不能整体支撑。"),
    "H_FC756EA86AAF4A94BA7207A5B5": ("mixed_object_partial_basis", "《安全生产法》第四十五条只能直接覆盖个体防护用品，不能同时支撑设备工程降噪措施。"),
    "H_DB786B8BC54E4E55B1145D00D7": ("specific_technical_basis_not_proven", "候选对象为内部防雷装置，当前命中的危险化学品条例条款不是足够精确的防雷技术条款。"),
}


def classify_backlog_hold(item: dict) -> tuple[str, str]:
    status = str(item.get("proposalStatus") or "")
    if "bibliographic" in status or "catalog" in status:
        return "bibliographic_or_locator_evidence_insufficient", "仅有题录/依据线索，尚未形成现行具体条款逐字原文与适用性闭环。"
    if "rejected" in status:
        return "rejected_link_needs_new_evidence", "旧关联已拒绝，当前没有足够的新官方原文证据建立新的direct/fallback链。"
    if "no_link" in status:
        return "no_direct_link_evidence", "当前不存在可通过Gate的直接/兜底关联证据链。"
    return "no_exact_current_reviewed_clause", "本轮未找到可直接复用且通过当前Gate的精确现行条款；证据不足，继续proposed。"


def promote_one(hid: str, spec: dict, clauses: dict, clause_reviews: dict, hazards: dict) -> dict:
    clause = clauses[spec["clause"]]
    creview = clause_reviews.get(clause["id"]) or {}
    if creview.get("decision") != "verified" or creview.get("reviewedContentHash") != content_hash(clause) or not creview.get("evidenceRefs"):
        raise RuntimeError(f"clause review not current/authoritative: {clause['id']}")
    hazard = dict(hazards[hid])
    hazard["lifecycle"] = "active"
    hazard["mode"] = "direct"
    hazard.pop("proposalStatus", None)
    hazard.pop("sourceRow", None)
    hazard.pop("revisionState", None)
    marker = "【PHASE 6 2026-09-16】已回到官方原文复核对象、现行版本、逐字条款和适用边界，建立当前direct关联。"
    note = str(hazard.get("note") or "").rstrip()
    if marker not in note:
        hazard["note"] = (note + "\n" + marker).strip()
    evidence_refs = list(dict.fromkeys(creview.get("evidenceRefs") or []))
    write_json(KNOW / "hazards" / f"{hid}.json", hazard)
    hreview = make_review(hazard, "hazard", evidence_refs, "content", "PHASE 6最终核验：隐患对象表述与所选现行条款义务一致；未使用摘要替代官方原文。")
    write_json(KNOW / "reviews" / "hazards" / f"{hid}.json", hreview)

    kid = "K_PHASE6_" + hashlib.sha1((hid + "|" + clause["id"]).encode("utf-8")).hexdigest()[:24].upper()
    link = {
        "id": kid,
        "hazardId": hid,
        "clauseId": clause["id"],
        "role": "direct",
        "legacyRole": "直接依据",
        "applicability": spec["applicability"],
        "jurisdictionCode": clause.get("jurisdictionCode") or "CN",
        "lifecycle": "active",
        "priority": 10,
        "requirementId": "",
        "reason": spec["reason"],
    }
    lreview = {
        "checkedAt": AS_OF,
        "contextHashes": {"clause": content_hash(clause), "hazard": content_hash(hazard)},
        "decision": "verified",
        "entityId": kid,
        "entityType": "link",
        "evidenceRefs": evidence_refs,
        "reason": spec["reason"],
        "reviewType": "applicability",
        "reviewedContentHash": content_hash(link),
        "reviewer": REVIEWER,
    }
    write_json(KNOW / "links" / f"{kid}.json", link)
    write_json(KNOW / "reviews" / "links" / f"{kid}.json", lreview)
    return {"hazardId": hid, "clauseId": clause["id"], "linkId": kid, "reason": spec["reason"]}


def update_manifest(promoted_count: int) -> None:
    p = KNOW / "manifest.json"
    manifest = read_json(p)
    batch_id = "phase6-candidate-evidence-rebind-final-20260916"
    batches = [b for b in manifest.get("batches", []) if b.get("id") != batch_id]
    batches.append({
        "id": batch_id,
        "lawsAdded": 1,
        "lawVersionsAdded": 1,
        "clausesAdded": 4,
        "evidenceAdded": 1,
        "hazardsPromoted": promoted_count,
        "linksAdded": promoted_count,
        "candidatesReviewed": 519,
        "selection": "PHASE 6 final conservative review: promote only explicit semantic matches with current reviewed official clauses; all evidence/semantic gaps remain proposed with a final disposition reason.",
    })
    manifest["batches"] = batches
    counts = manifest.setdefault("counts", {})
    for key, rel in (("laws", "laws"), ("lawVersions", "law-versions"), ("clauses", "clauses"), ("hazards", "hazards"), ("links", "links"), ("evidence", "evidence")):
        counts[key] = len(list((KNOW / rel).glob("*.json")))
    manifest["asOf"] = AS_OF
    write_json(p, manifest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    backlog_meta, backlog_rows = load_jsonl_records(DOCS / "phase6-candidate-backlog.jsonl")
    reuse_meta, reuse_rows = load_jsonl_records(DOCS / "phase6-reuse-candidates.jsonl")
    backlog = {r["hazardId"]: r for r in backlog_rows if r.get("hazardId")}
    reuse = {r["hazardId"]: r for r in reuse_rows if r.get("hazardId")}
    hazards = load_dir("hazards")
    proposed_before = {hid for hid, h in hazards.items() if h.get("lifecycle") == "proposed" and not h.get("mergedInto")}
    if len(proposed_before) != 519:
        raise RuntimeError(f"PHASE6 baseline drift: expected 519 proposed, found {len(proposed_before)}")
    if proposed_before != set(backlog):
        missing = sorted(proposed_before - set(backlog))[:20]
        extra = sorted(set(backlog) - proposed_before)[:20]
        raise RuntimeError(f"backlog/proposed mismatch missing={missing} extra={extra}")
    if not set(PROMOTE).issubset(proposed_before):
        raise RuntimeError("promotion allow-list contains non-proposed IDs: " + repr(sorted(set(PROMOTE) - proposed_before)))

    if not args.apply:
        print(json.dumps({"phase6Candidates": len(proposed_before), "exactReuseCandidates": len(reuse), "promotionAllowList": len(PROMOTE)}, ensure_ascii=False, indent=2))
        return 0

    ensure_current_jiangsu_risk_regulation()
    clauses = load_dir("clauses")
    clause_reviews = load_dir("reviews/clauses")
    hazards = load_dir("hazards")
    gate = evaluate_release_gate(KNOW)
    for hid, spec in PROMOTE.items():
        cid = spec["clause"]
        if cid not in clauses:
            raise RuntimeError(f"missing clause {cid} for {hid}")
        cg = gate.clauses.get(cid) or {}
        if not cg.get("ok"):
            raise RuntimeError(f"clause gate failed for {cid}: {cg.get('reasons')}")

    promoted = []
    for hid, spec in sorted(PROMOTE.items()):
        promoted.append(promote_one(hid, spec, clauses, clause_reviews, hazards))

    dispositions = []
    reason_counts = Counter()
    for hid in sorted(proposed_before):
        h = hazards[hid]
        if hid in PROMOTE:
            spec = PROMOTE[hid]
            code = "promoted_verified_direct"
            reason = spec["reason"]
            outcome = "promoted_active"
            lifecycle_after = "active"
            clause_ids = [spec["clause"]]
        else:
            outcome = "retained_proposed"
            lifecycle_after = "proposed"
            clause_ids = [x.get("clauseId") for x in reuse.get(hid, {}).get("exactCurrentClauses", []) if x.get("clauseId")]
            if hid in HOLD_OVERRIDES:
                code, reason = HOLD_OVERRIDES[hid]
            elif hid in reuse:
                code = "exact_locator_match_only_semantic_applicability_not_proven"
                reason = "修订表条款定位可映射到当前已核条款，但PHASE 6复核未取得足以证明该hazard对象、条件和条款义务完全一致的直接证据；仅凭locator匹配不得转正。"
            else:
                code, reason = classify_backlog_hold(backlog[hid])
        reason_counts[code] += 1
        row = {
            "hazardId": hid,
            "title": h.get("title"),
            "sourceRow": backlog[hid].get("sourceRow"),
            "outcome": outcome,
            "lifecycleAfter": lifecycle_after,
            "reasonCode": code,
            "reason": reason,
            "clauseIds": clause_ids,
            "previousProposalStatus": backlog[hid].get("proposalStatus"),
            "targetScope": backlog[hid].get("targetScope"),
        }
        if lifecycle_after == "proposed":
            row["nextRequiredEvidence"] = backlog[hid].get("nextAction") or "补齐官方逐字原文、对象适用条件和当前上下文审核后再进入新的核验循环。"
        dispositions.append(row)

    meta = {
        "recordType": "metadata",
        "schemaVersion": 1,
        "asOf": AS_OF,
        "phase": 6,
        "phaseStatus": "DONE",
        "baselineProposed": len(proposed_before),
        "promoted": len(promoted),
        "retainedProposed": len(proposed_before) - len(promoted),
        "exactReuseCandidatesReviewed": len(reuse),
        "reasonCounts": dict(sorted(reason_counts.items())),
        "allBaselineCandidatesDisposed": True,
        "privateSqliteModified": False,
        "stableHazardIdsModified": False,
        "releaseOrPagesPerformed": False,
    }
    write_jsonl(DOCS / "phase6-final-disposition.jsonl", [meta] + dispositions)

    lines = [
        "# PHASE 6 最终处置报告",
        "",
        f"> 基准日：{AS_OF}。本报告是 PHASE 6 候选法规证据回绑的最终闭环；证据不足的候选继续 `proposed`，不以清零候选为目标。",
        "",
        "## 结论",
        "",
        f"- 基线候选：**{len(proposed_before)}** 条；已逐条生成最终处置：**{len(dispositions)} / {len(proposed_before)}**。",
        f"- 完整 Gate 后转为 `active`：**{len(promoted)}** 条。",
        f"- 因证据、对象、条件、现行数值或原文质量不足继续 `proposed`：**{len(proposed_before)-len(promoted)}** 条。",
        f"- exact current reviewed clause 候选已全部处置：**{len(reuse)}** 条。",
        "- 新纳管现行法规：**《江苏省生产经营单位安全风险管理条例》**（2024-11-01施行），建立第8、11、12、16条官方证据链。",
        "- 未修改私有 SQLite / archive；未修改任何既有 hazard 稳定 ID；未执行 PR 合并、Pages 或线上发布。",
        "",
        "## 本批转正清单",
        "",
        "| hazardId | clauseId | 核验结论 |",
        "| --- | --- | --- |",
    ]
    for x in promoted:
        lines.append(f"| `{x['hazardId']}` | `{x['clauseId']}` | {x['reason']} |")
    lines += ["", "## 继续 proposed 的主要原因", ""]
    for code, count in sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if code == "promoted_verified_direct":
            continue
        lines.append(f"- `{code}`：{count} 条。")
    lines += [
        "",
        "## 关键保守判定",
        "",
        "- GB 55037-2022 第3.4.5条现行文本为消防车道坡度不应大于10%，因此“坡度大于8%”不按该条转正；该条也没有固定“距外墙5m”阈值。",
        "- 《工贸企业粉尘防爆安全规定》第十八条是粉尘清理/废物处置义务，不能拿来支撑一般废气收集、压差监测、集气罩、选址等对象。",
        "- GB 12158-2024 第7.6条当前 knowledge 文本存在指数/截断异常，在恢复完整逐字原文前不进入正式链。",
        "- GB 50187-2012 第5.7.4条“出入口数量不宜少于2个”为推荐性措辞，不机械转成绝对违法。",
        "- 所有仅有条款 locator 相同、但对象/场景/条件没有独立证明的候选一律继续 `proposed`。",
        "",
        "## 机器明细",
        "",
        "完整 519 条处置见 `docs/phase6-final-disposition.jsonl`。",
        "",
    ]
    (DOCS / "PHASE6_FINAL_DISPOSITION.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    update_manifest(len(promoted))

    gate_after = evaluate_release_gate(KNOW)
    eligible = set(gate_after.eligible_hazards)
    missing_eligible = sorted(set(PROMOTE) - eligible)
    if missing_eligible:
        raise RuntimeError("promoted hazards did not pass release gate: " + repr(missing_eligible))
    print(json.dumps({"phase6": "DONE", "baseline": len(proposed_before), "promoted": len(promoted), "retainedProposed": len(proposed_before)-len(promoted), "allPromotedGateEligible": True, "reasonCounts": dict(reason_counts)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
