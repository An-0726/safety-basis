# -*- coding: utf-8 -*-
"""V4 发布门禁共享链式判定核心（Single Source of Truth）。

设计依据 docs/GATE_V4.md。三个脚本（strict_release_audit / build_release /
gate_v4）都只 import 本模块，不再各自复制一套略有漂移的判断逻辑。

判定链（§11）：
    link -> clause -> lawVersion -> law
同时 link review 的 contextHashes 绑定 hazard + clause。

对外主入口：
    evaluate_release_gate(knowledge_dir, as_of) -> GateResult

GateResult 同时给出：
- 每个实体的 gate 判定（ok / reasons）；
- eligible_links / eligible_hazards（真正可进公开发布投影的集合）；
- 供审计做 releaseBlockers / inventoryWarnings / excludedEntities 分类所需的全部原始信号。
"""
import glob
import io
import json
import os
import re
from datetime import date
from types import SimpleNamespace

from canonical import content_hash

# ---- 常量（与 GATE_V4.md 对齐）-------------------------------------------

DEFAULT_AS_OF = date(2026, 9, 10)

# §7 LawVersion 效力状态
ALLOWED_VALIDITY = {"active", "upcoming", "repealed", "unknown"}

# §10/§11 link role 字典
SUPPORTED_ROLES = {"direct", "fallback", "supporting"}
# §9 qualifying role：direct / fallback 才能单独支撑一个 hazard
QUALIFYING_ROLES = {"direct", "fallback"}

# 全国性管辖代码的等价写法（数据里 link 用 "全国"/"CN"，law 用 "CN"/"CN-32"...）
NATIONAL_CODES = {"CN", "全国"}

# §14 隐私泄漏：本地绝对路径 / home 目录
PRIVATE_PATH_RE = re.compile(r"[A-Za-z]:\\|/(?:home|Users|mnt)/")


# ---- 工具 -----------------------------------------------------------------
def load_dir(root, rel):
    """读取 knowledge/<rel>/*.json，普通实体按自身 id 建索引。"""
    out = {}
    for f in glob.glob(os.path.join(root, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("id") or d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def load_reviews(root, rel):
    """读取 review sidecar，按其被审核实体 entityId 建索引。

    review 自身可带独立的 RV_* id；发布门禁查找 review 时必须使用实体 id，
    否则新式 review 会被误判为缺失。旧 sidecar 若无 entityId，则以文件名兜底。
    """
    out = {}
    for f in glob.glob(os.path.join(root, rel, "*.json")):
        with io.open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        key = d.get("entityId") or os.path.splitext(os.path.basename(f))[0]
        out[key] = d
    return out


def parse_date(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v))
    except Exception:
        return None


def _region(code):
    """把管辖代码归一化为比较用区域：全国性一律归为 'CN'。"""
    if not code:
        return None
    c = str(code).strip()
    if c in NATIONAL_CODES:
        return "CN"
    return c


def jurisdiction_conflicts(link_code, law_code):
    """§10 jurisdiction 与 hazard/法规使用场景是否明确冲突。

    仅当双方都是“具体地方区域”且不一致时才算冲突；全国性法规/链接不与
    任何具体区域冲突（全国法在地方当然适用）。
    """
    lc, kc = _region(link_code), _region(law_code)
    if not lc or not kc:
        return False
    if lc == "CN" or kc == "CN":
        return False  # 全国性一方不构成冲突
    return lc != kc


# ---- 单层 gate ------------------------------------------------------------
def _review_binding(entity, review, need_evidence):
    """通用 review 绑定检查（§2.4 / §4）。返回 (ok, reasons)。"""
    reasons = []
    if not review:
        return False, ["BLOCK_REVIEW_MISSING"]
    if review.get("decision") != "verified":
        reasons.append("BLOCK_REVIEW_NOT_VERIFIED:" + str(review.get("decision")))
    if review.get("reviewedContentHash") != content_hash(entity):
        reasons.append("BLOCK_REVIEW_STALE")
    if need_evidence and not review.get("evidenceRefs"):
        reasons.append("BLOCK_EVIDENCE_NOT_AUTHORITATIVE")
    return not reasons, reasons


def gate_law(law, review):
    """§6 Law 硬门禁：身份有效 + review verified + hash 当前 + authoritative evidence。"""
    reasons = []
    if not law.get("canonicalName"):
        reasons.append("BLOCK_LAW_IDENTITY:canonicalName_empty")
    if not law.get("issuer"):
        reasons.append("BLOCK_LAW_IDENTITY:issuer_empty")
    if not law.get("jurisdictionCode"):
        reasons.append("BLOCK_LAW_IDENTITY:jurisdictionCode_empty")
    ok, r = _review_binding(law, review, need_evidence=True)
    reasons += r
    return not reasons, reasons


def gate_law_version(lv, review, law_ok, as_of):
    """§7 LawVersion 硬门禁 + asOf 效力判定。

    返回 (ok, supports_current, reasons)：
    - ok：版本自身结构/身份/review 是否合格；
    - supports_current：在 as_of 当天能否作为“当前 hazard 的现行依据”。
    """
    reasons = []
    status = lv.get("validityStatus") or "unknown"
    eff = parse_date(lv.get("effectiveDate"))
    end = parse_date(lv.get("endDate"))

    if not lv.get("lawId"):
        reasons.append("BLOCK_FOREIGN_KEY:lawId_missing")
    if not lv.get("versionKey") and not lv.get("officialName"):
        reasons.append("BLOCK_VERSION_UNKNOWN:versionKey_and_officialName_empty")
    if not eff:
        reasons.append("BLOCK_VERSION_NOT_EFFECTIVE:effectiveDate_invalid")
    if status not in ALLOWED_VALIDITY:
        reasons.append("BLOCK_VERSION_UNKNOWN:invalid_validityStatus:" + str(status))
    ok, r = _review_binding(lv, review, need_evidence=True)
    reasons += r
    if not law_ok:
        reasons.append("BLOCK_LAW_IDENTITY:parent_law_gate_failed")

    supports_current = False
    if status == "active" and eff:
        # §7 active：effectiveDate <= asOf AND (endDate null OR asOf < endDate)
        if eff <= as_of and (not end or as_of < end):
            supports_current = True
        elif eff > as_of:
            reasons.append("BLOCK_VERSION_NOT_EFFECTIVE:active_before_effectiveDate")
        elif end and not (as_of < end):
            reasons.append("BLOCK_VERSION_EXPIRED:active_past_endDate")
    elif status == "upcoming":
        # §7 upcoming：可进法规目录，但不能支撑当前 hazard；
        # 若 effectiveDate <= asOf 仍标 upcoming，属于效力标错，需复核。
        if eff and eff <= as_of:
            reasons.append("BLOCK_VERSION_NOT_EFFECTIVE:upcoming_not_future")
    # repealed / unknown：天然不能支撑当前 hazard，不额外记硬错误（它们是 excluded）

    return not reasons, supports_current, reasons


def gate_clause(clause, review, lv_supports_current, lv_struct_ok):
    """§8 Clause 硬门禁 + 所属 LawVersion 可支撑当前日期。"""
    reasons = []
    if not clause.get("lawVersionId"):
        reasons.append("BLOCK_FOREIGN_KEY:lawVersionId_missing")
    if not clause.get("articlePath"):
        reasons.append("BLOCK_CLAUSE_LOCATOR:articlePath_missing")
    if not clause.get("quote"):
        reasons.append("BLOCK_CLAUSE_TEXT:quote_missing")
    ok, r = _review_binding(clause, review, need_evidence=True)
    reasons += r
    # 条款级效力：整部标准现行，不代表其中某条没被废止（部分替代场景）。
    # 被废止条文不得再作为现行依据，其关联会因本项不合格而无法进入发布。
    if (clause.get("lifecycle") or "active") != "active":
        # 用 EXCLUDED_ 前缀：这是"实体已被替代、不应发布"，不是数据错误。
        # strict_release_audit 据此把它归入 excludedEntities 而非 releaseBlockers。
        reasons.append("EXCLUDED_CLAUSE_NOT_CURRENT:clause_lifecycle_"
                       + str(clause.get("lifecycle")))
    if not lv_struct_ok:
        reasons.append("BLOCK_VERSION_UNKNOWN:lawVersion_gate_failed")
    elif not lv_supports_current:
        # §10：关联 upcoming/repealed/unknown version 却试图支撑当前 hazard
        reasons.append("BLOCK_VERSION_NOT_EFFECTIVE:lawVersion_not_supporting_current")
    return not reasons, reasons


def gate_hazard_content(hazard, review):
    """§9 Hazard 内容硬门禁（不含法规链）。"""
    reasons = []
    for field in ("title", "description", "measures", "category"):
        if not hazard.get(field):
            reasons.append("BLOCK_SCHEMA:hazard_%s_missing" % field)
    if (hazard.get("lifecycle") or "active") != "active":
        reasons.append("BLOCK:hazard_not_active")
    if hazard.get("mergedInto"):
        reasons.append("BLOCK:hazard_mergedInto")
    ok, r = _review_binding(hazard, review, need_evidence=False)
    reasons += r
    public_text = " ".join(str(hazard.get(x) or "") for x in ("title", "description", "measures", "note"))
    if PRIVATE_PATH_RE.search(public_text):
        reasons.append("BLOCK_PRIVATE_LEAK:absolute_path_in_public_text")
    return not reasons, reasons


def gate_link(link, review, hazard, clause, law, clause_ok):
    """§10 Link 硬门禁。"""
    reasons = []
    role = link.get("role")
    if role not in SUPPORTED_ROLES:
        reasons.append("BLOCK_LINK_ROLE:invalid_role:" + str(role))
    if (link.get("lifecycle") or "active") != "active":
        reasons.append("BLOCK_LINK_APPLICABILITY:link_not_active")
    if not link.get("applicability"):
        reasons.append("BLOCK_LINK_APPLICABILITY:applicability_empty")
    if not hazard:
        reasons.append("BLOCK_FOREIGN_KEY:hazard_missing")
    elif hazard.get("mergedInto") or (hazard.get("lifecycle") or "active") != "active":
        # §9 已合并/非 active 的 hazard 不进入公开投影；支撑它的 link 也不得计为
        # 合格关联，否则 eligible_links 会包含实际不会发布的历史追溯关联。
        reasons.append("BLOCK_LINK_HAZARD_NOT_PUBLISHABLE:"
                       + ("merged" if hazard.get("mergedInto") else str(hazard.get("lifecycle"))))
    if not clause:
        reasons.append("BLOCK_FOREIGN_KEY:clause_missing")
    ok, r = _review_binding(link, review, need_evidence=False)
    reasons += r
    if review and review.get("decision") == "verified":
        if not review.get("reason"):
            reasons.append("BLOCK_LINK_APPLICABILITY:reason_empty")
        ctx = review.get("contextHashes") or {}
        if hazard and ctx.get("hazard") != content_hash(hazard):
            reasons.append("BLOCK_REVIEW_CONTEXT_STALE:hazard_context_stale")
        if clause and ctx.get("clause") != content_hash(clause):
            reasons.append("BLOCK_REVIEW_CONTEXT_STALE:clause_context_stale")
    if law and jurisdiction_conflicts(link.get("jurisdictionCode"), law.get("jurisdictionCode")):
        reasons.append("BLOCK_LINK_APPLICABILITY:jurisdiction_conflict")
    if clause and not clause_ok:
        reasons.append("BLOCK_CLAUSE_TEXT:clause_gate_failed")
    return not reasons, reasons


# ---- 主入口 ---------------------------------------------------------------
def evaluate_release_gate(knowledge_dir=None, as_of=DEFAULT_AS_OF):
    """对 knowledge 全量做链式 gate，返回 GateResult（SimpleNamespace）。"""
    if knowledge_dir is None:
        knowledge_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "knowledge",
        )

    laws = load_dir(knowledge_dir, "laws")
    lvs = load_dir(knowledge_dir, "law-versions")
    clauses = load_dir(knowledge_dir, "clauses")
    hazards = load_dir(knowledge_dir, "hazards")
    links = load_dir(knowledge_dir, "links")
    reviews = {
        "laws": load_reviews(knowledge_dir, os.path.join("reviews", "laws")),
        "law_versions": load_reviews(knowledge_dir, os.path.join("reviews", "law-versions")),
        "clauses": load_reviews(knowledge_dir, os.path.join("reviews", "clauses")),
        "hazards": load_reviews(knowledge_dir, os.path.join("reviews", "hazards")),
        "links": load_reviews(knowledge_dir, os.path.join("reviews", "links")),
    }

    # 1) Law
    laws_v = {}
    for lid, law in laws.items():
        ok, reasons = gate_law(law, reviews["laws"].get(lid))
        laws_v[lid] = {"ok": ok, "reasons": reasons,
                       "canonicalName": law.get("canonicalName") or law.get("name") or law.get("title")}

    # 2) LawVersion
    lvs_v = {}
    for vid, lv in lvs.items():
        law_ok = laws_v.get(lv.get("lawId"), {}).get("ok", False)
        ok, supports, reasons = gate_law_version(lv, reviews["law_versions"].get(vid), law_ok, as_of)
        lvs_v[vid] = {"ok": ok, "supports_current": supports,
                      "validityStatus": lv.get("validityStatus") or "unknown",
                      "reasons": reasons}

    # 3) Clause
    clauses_v = {}
    for cid, cl in clauses.items():
        vid = cl.get("lawVersionId")
        lv = lvs_v.get(vid, {})
        ok, reasons = gate_clause(cl, reviews["clauses"].get(cid),
                                  lv.get("supports_current", False), lv.get("ok", False))
        clauses_v[cid] = {"ok": ok, "reasons": reasons, "lawVersionId": vid}

    # 4) Hazard 内容
    hazards_v = {}
    for hid, hz in hazards.items():
        ok, reasons = gate_hazard_content(hz, reviews["hazards"].get(hid))
        hazards_v[hid] = {
            "content_ok": ok, "reasons": reasons,
            "active": (hz.get("lifecycle") or "active") == "active",
            "merged": bool(hz.get("mergedInto")),
            "review_decision": (reviews["hazards"].get(hid) or {}).get("decision"),
        }

    # 5) Link（链式）
    links_v = {}
    eligible_links = set()
    lv_law = {vid: lvs[vid].get("lawId") for vid in lvs}
    for kid, lk in links.items():
        hid, cid = lk.get("hazardId"), lk.get("clauseId")
        hazard = hazards.get(hid)
        clause = clauses.get(cid)
        law = laws.get(lv_law.get(clauses.get(cid, {}).get("lawVersionId"))) if clause else None
        clause_ok = clauses_v.get(cid, {}).get("ok", False)
        review = reviews["links"].get(kid)
        ok, reasons = gate_link(lk, review, hazard, clause, law, clause_ok)
        links_v[kid] = {
            "ok": ok, "reasons": reasons,
            "role": lk.get("role"),
            "qualifying": lk.get("role") in QUALIFYING_ROLES,
            "decision": (review or {}).get("decision") or "missing",
            "hazardId": hid, "clauseId": cid,
        }
        if ok:
            eligible_links.add(kid)

    # 6) Hazard 可发布 = 内容合格 + 至少一条合格 qualifying link
    qualifying_links_by_hazard = {}
    eligible_hazards = set()
    for kid in eligible_links:
        hv = links_v[kid]
        if hv["qualifying"]:
            qualifying_links_by_hazard.setdefault(hv["hazardId"], []).append(kid)
    for hid, hv in hazards_v.items():
        if hv["content_ok"] and qualifying_links_by_hazard.get(hid):
            eligible_hazards.add(hid)

    return SimpleNamespace(
        as_of=as_of.isoformat(),
        counts={"laws": len(laws), "lawVersions": len(lvs), "clauses": len(clauses),
                "hazards": len(hazards), "links": len(links)},
        laws=laws_v, law_versions=lvs_v, clauses=clauses_v,
        hazards=hazards_v, links=links_v,
        eligible_links=eligible_links, eligible_hazards=eligible_hazards,
        qualifying_links_by_hazard=qualifying_links_by_hazard,
    )
