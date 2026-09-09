"""Shared, deterministic verification rules for the private master and releases.

Only explicitly projected public fields enter a release. A passed state label is
insufficient: proofs bind the current record, dependencies, evidence and dates.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from master import dumps


TABLES = {"law": "laws", "law_version": "law_versions", "clause": "clauses",
          "hazard": "hazards", "link": "links"}
CHECKS = {"law": "identity", "law_version": "version", "clause": "text",
          "hazard": "content", "link": "applicability"}
FIELDS = {
    "law": "id revision canonical_name issuer jurisdiction_code document_kind identity_status status",
    "law_version": "id revision law_id document_number official_name level scope effective_date end_date validity_status review_status source_url",
    "clause": "id revision law_version_id article_path quote source_url status identity_status",
    "hazard": "id revision title description measures category conditions mode status merged_into",
    "link": "id revision hazard_id clause_id role priority applicability jurisdiction_code status",
}
EXTRAS = {"law": {"aliases"}, "hazard": {"aliases", "places", "keywords", "active_link_ids", "inactive_links"}}
REVIEW_FIELDS = {"status", "review_status", "identity_status"}
PROOF_FIELDS = {"id", "entity_type", "entity_id", "entity_revision", "dependency_hash", "check_type",
                "result", "reviewer", "model", "checked_at", "review_due_at", "evidence_id", "locator", "public_fields_reviewed"}
EVIDENCE_FIELDS = {"id", "official_url", "retrieved_at", "sha256"}
BUSINESS_TIMEZONE = dt.timezone(dt.timedelta(hours=8))


def digest(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("日期必须为 YYYY-MM-DD")
    return dt.date.fromisoformat(value)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("时间必须带时区")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("时间必须带时区")
    return parsed


def business_date(value):
    return (timestamp(value) if isinstance(value, str) else value).astimezone(BUSINESS_TIMEZONE).date()


def official_url(value):
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in ("http", "https") and not parsed.username and not parsed.password
                and (host == "gov.cn" or host.endswith(".gov.cn")) and parsed.port in (None, 80, 443))
    except (TypeError, ValueError):
        return False


def graph_from_db(conn):
    graph = {}
    for kind, table in TABLES.items():
        fields = FIELDS[kind].split()
        graph[table] = [dict(zip(fields, row)) for row in conn.execute(
            f'SELECT {",".join(fields)} FROM {table} ORDER BY id')]
    for law in graph["laws"]:
        law["aliases"] = [r[0] for r in conn.execute("SELECT alias FROM law_aliases WHERE law_id=? ORDER BY ordinal", (law["id"],))]
    for hazard in graph["hazards"]:
        for public, stored in (("aliases", "aliase"), ("places", "place"), ("keywords", "keyword")):
            hazard[public] = [r[0] for r in conn.execute(
                "SELECT value FROM hazard_tags WHERE hazard_id=? AND kind=? ORDER BY ordinal", (hazard["id"], stored))]
        refs = [r for r in graph["links"] if r["hazard_id"] == hazard["id"]]
        hazard["active_link_ids"] = sorted(r["id"] for r in refs if r["status"] != "已失效")
        # Retiring a pending link also changes the hazard's verification material.
        hazard["inactive_links"] = [{k: r[k] for k in ("id", "clause_id", "revision")}
                                    for r in refs if r["status"] == "已失效"]
    return graph


def maps(graph):
    return {kind: {row["id"]: row for row in graph[table]} for kind, table in TABLES.items()}


def validate_graph(graph):
    if not isinstance(graph, dict) or set(graph) != set(TABLES.values()):
        raise ValueError("发布实体表不完整或包含额外数据")
    seen = {}
    for kind, table in TABLES.items():
        if not isinstance(graph[table], list):
            raise ValueError("实体必须为数组")
        seen[kind] = set()
        allowed = set(FIELDS[kind].split()) | EXTRAS.get(kind, set())
        for row in graph[table]:
            if not isinstance(row, dict) or set(row) != allowed:
                raise ValueError(f"{kind}: 发布字段不符合白名单")
            ident = row["id"]
            if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,79}", ident) or ident in seen[kind]:
                raise ValueError(f"{kind}: ID 无效或重复")
            seen[kind].add(ident)
            if type(row["revision"]) is not int or row["revision"] < 1:
                raise ValueError("revision 无效")
            for field in set(FIELDS[kind].split()) - {"revision", "priority", "merged_into"}:
                if not isinstance(row[field], str):
                    raise ValueError(f"{kind}.{field}: 必须为文本")
            if kind == "link" and (type(row["priority"]) is not int or row["priority"] < 0):
                raise ValueError("关联 priority 无效")
            if kind == "hazard" and row["merged_into"] is not None and not isinstance(row["merged_into"], str):
                raise ValueError("merged_into 无效")
            for field in EXTRAS.get(kind, set()) - {"inactive_links"}:
                if not isinstance(row[field], list) or any(not isinstance(v, str) for v in row[field]):
                    raise ValueError(f"{field} 必须为文本数组")
    index = maps(graph)
    for kind, field, parent in (("law_version", "law_id", "law"), ("clause", "law_version_id", "law_version"),
                                ("link", "hazard_id", "hazard"), ("link", "clause_id", "clause")):
        for row in index[kind].values():
            if row[field] not in index[parent]:
                raise ValueError(f"{kind}:{row['id']} 外键断链")
    link_pairs = [(r["hazard_id"], r["clause_id"]) for r in graph["links"]]
    if len(set(link_pairs)) != len(link_pairs):
        raise ValueError("隐患与条款关联重复")
    for h in graph["hazards"]:
        expected = sorted(r["id"] for r in graph["links"] if r["hazard_id"] == h["id"] and r["status"] != "已失效")
        if h["active_link_ids"] != expected:
            raise ValueError("启用关联集合不一致")
        if not isinstance(h["inactive_links"], list):
            raise ValueError("停用关联摘要无效")
        retired = set()
        for row in h["inactive_links"]:
            if (not isinstance(row, dict) or set(row) != {"id", "clause_id", "revision"}
                    or not isinstance(row["id"], str) or not isinstance(row["clause_id"], str)
                    or type(row["revision"]) is not int or row["revision"] < 1
                    or row["id"] in retired or row["id"] in h["active_link_ids"]):
                raise ValueError("停用关联摘要无效")
            retired.add(row["id"])


def material(graph, kind, ident):
    index = maps(graph)
    def own(k, i):
        return {f: v for f, v in index[k][i].items() if f not in REVIEW_FIELDS}
    def law_version(i):
        r = index["law_version"][i]
        return {"record": own("law_version", i), "law": own("law", r["law_id"])}
    def clause(i):
        r = index["clause"][i]
        return {"record": own("clause", i), "version": law_version(r["law_version_id"])}
    def link(i):
        r = index["link"][i]
        return {"record": own("link", i), "hazard": own("hazard", r["hazard_id"]), "clause": clause(r["clause_id"])}
    if kind == "law":
        return own(kind, ident)
    if kind == "law_version":
        return law_version(ident)
    if kind == "clause":
        return clause(ident)
    if kind == "link":
        return link(ident)
    if kind == "hazard":
        return {"record": own(kind, ident), "links": [link(i) for i in index[kind][ident]["active_link_ids"]]}
    raise ValueError("未知核验实体")


def dependency_hash(graph, kind, ident):
    return digest(material(graph, kind, ident))


def preparation_errors(graph, kind, ident):
    row = maps(graph)[kind][ident]
    required = {
        "law": ("canonical_name", "issuer", "jurisdiction_code", "document_kind"),
        "law_version": ("official_name", "level", "scope", "effective_date", "source_url"),
        "clause": ("article_path", "quote", "source_url"),
        "hazard": ("title", "description", "measures", "category", "conditions", "mode"),
        "link": ("role", "applicability", "jurisdiction_code"),
    }[kind]
    errors = ["缺少 " + field for field in required if not row[field].strip()]
    errors += ["文本编码损坏 " + field for field in required if "\ufffd" in row[field]]
    if row.get("status") in ("已失效", "merged", "rejected") or row.get("review_status") == "已失效" or row.get("merged_into"):
        errors.append("记录已关闭，不能以核验操作重新启用")
    if kind in ("law_version", "clause") and not official_url(row["source_url"]):
        errors.append("缺少政府官方来源 URL")
    if kind == "law_version":
        try:
            effective = date(row["effective_date"])
            if row["end_date"] and date(row["end_date"]) <= effective:
                errors.append("失效日期必须晚于生效日期")
        except ValueError:
            errors.append("生效或失效日期无效")
        if row["validity_status"] not in ("现行有效", "即将生效", "已废止"):
            errors.append("法规效力尚未确认")
    if kind == "clause":
        if row["identity_status"] == "unresolved":
            errors.append("条款定位存在未解决迁移冲突")
        peers = [r for r in graph["clauses"] if r["law_version_id"] == row["law_version_id"] and r["article_path"] == row["article_path"]]
        if len(peers) != 1:
            errors.append("同版本条款定位重复，需先解决身份冲突")
    if kind == "law" and row["identity_status"] == "merged":
        errors.append("法规身份已合并")
    if kind == "law":
        key = tuple(row[field].strip() for field in ("canonical_name", "issuer", "jurisdiction_code", "document_kind"))
        if any(other["id"] != ident and other["identity_status"] == "confirmed"
               and tuple(other[field].strip() for field in ("canonical_name", "issuer", "jurisdiction_code", "document_kind")) == key
               for other in graph["laws"]):
            errors.append("已有相同的已确认法规身份，需先合并")
    if kind == "hazard":
        if row["mode"] not in ("直接适用", "条件适用", "上位法兜底"):
            errors.append("适用模式无效")
        for field in ("places", "keywords"):
            if not row[field] or any(not v.strip() for v in row[field]):
                errors.append("缺少 " + field)
        if not row["active_link_ids"]:
            errors.append("没有启用的依据关联")
    return errors


def load_proofs(conn):
    # Insertion order matters: a later failed/pending review supersedes a pass.
    details = {}
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='verification_details'").fetchone():
        details = {r[0]: {"locator": r[1], "public_fields_reviewed": bool(r[2])}
                   for r in conn.execute("SELECT verification_id,locator,public_fields_reviewed FROM verification_details")}
    result = {}
    columns = [r[1] for r in conn.execute("PRAGMA table_info(verification)")]
    for values in conn.execute("SELECT * FROM verification ORDER BY rowid"):
        row = dict(zip(columns, values))
        if row["check_type"] != CHECKS.get(row["entity_type"]):
            continue
        proof = {f: row[f] for f in PROOF_FIELDS - {"locator", "public_fields_reviewed"}}
        proof.update(details.get(row["id"], {"locator": "", "public_fields_reviewed": False}))
        result[(row["entity_type"], row["entity_id"])] = proof
    return result


def load_evidence(conn, db=None):
    result = {}
    columns = [r[1] for r in conn.execute("PRAGMA table_info(evidence)")]
    for values in conn.execute("SELECT * FROM evidence ORDER BY id"):
        row = dict(zip(columns, values))
        item = {f: row[f] for f in EVIDENCE_FIELDS}
        if db is not None:
            path = Path(db).parent / row["snapshot_ref"]
            item["archive_ok"] = bool(row["snapshot_ref"] and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"])
        result[row["id"]] = item
    return result


def own_errors(graph, kind, ident, proofs, evidence, as_of, *, allow_upcoming=False):
    errors = preparation_errors(graph, kind, ident)
    row = maps(graph)[kind][ident]
    if row.get("review_status", row.get("status")) != "已核验":
        errors.append("当前状态未核验")
    if kind == "law" and row["identity_status"] != "confirmed":
        errors.append("法规身份未确认")
    if kind == "clause" and row["identity_status"] != "confirmed_locator":
        errors.append("条款定位未确认")
    if kind == "law_version":
        upcoming = allow_upcoming and row["validity_status"] == "即将生效"
        if row["validity_status"] != "现行有效" and not upcoming:
            errors.append("非现行有效版本")
        try:
            effective = date(row["effective_date"])
            if (effective > as_of and not upcoming) or (row["end_date"] and date(row["end_date"]) <= as_of):
                errors.append("发布日不在有效期间内")
            if upcoming and effective <= as_of:
                errors.append("尚未实施版本已到实施日，需复核效力状态")
        except ValueError:
            pass
    proof = proofs.get((kind, ident))
    if not proof or proof["result"] != "passed":
        return errors + ["没有最新通过记录"]
    if proof["entity_revision"] != row["revision"] or proof["dependency_hash"] != dependency_hash(graph, kind, ident):
        errors.append("核验记录与当前内容或依赖版本不符")
    if not proof["reviewer"].strip() or not proof["locator"].strip():
        errors.append("核验人或证据定位缺失")
    if kind == "hazard" and proof["public_fields_reviewed"] is not True:
        errors.append("公开字段尚未审阅")
    document = evidence.get(proof["evidence_id"])
    if not document:
        return errors + ["核验证据缺失"]
    if not official_url(document["official_url"]) or not re.fullmatch(r"[0-9a-f]{64}", document["sha256"]):
        errors.append("官方证据 URL 或哈希无效")
    if document.get("archive_ok") is False:
        errors.append("证据原件缺失或哈希不匹配")
    try:
        checked = timestamp(proof["checked_at"])
        retrieved = timestamp(document["retrieved_at"])
        if retrieved > checked or business_date(checked) > as_of:
            errors.append("证据获取或核验时间晚于适用时间")
        if proof["review_due_at"] and date(proof["review_due_at"]) <= as_of:
            errors.append("核验已到复核日期")
    except (ValueError, TypeError):
        errors.append("核验或证据日期无效")
    return errors


def gate(graph, proofs, evidence, as_of):
    validate_graph(graph)
    as_of = date(as_of) if isinstance(as_of, str) else as_of
    index = maps(graph)
    reasons = {(kind, ident): own_errors(graph, kind, ident, proofs, evidence, as_of)
               for kind in TABLES for ident in index[kind]}
    def chain(kind, ident):
        result = [f"{kind}:{ident}: {reason}" for reason in reasons[(kind, ident)]]
        row = index[kind][ident]
        if kind == "law_version":
            result += chain("law", row["law_id"])
        elif kind == "clause":
            result += chain("law_version", row["law_version_id"])
        elif kind == "link":
            result += chain("clause", row["clause_id"])
        return result
    hazards = {}
    for ident, row in index["hazard"].items():
        messages = chain("hazard", ident)
        for link_id in row["active_link_ids"]:
            messages += chain("link", link_id)
        hazards[ident] = sorted(set(messages))
    # The independent catalogue includes verified, published upcoming editions.
    # Hazard chains above still require a currently effective legal basis.
    versions = {ident: sorted(set(
        [f"law_version:{ident}: {reason}" for reason in
         own_errors(graph, "law_version", ident, proofs, evidence, as_of, allow_upcoming=True)]
        + chain("law", row["law_id"]))) for ident, row in index["law_version"].items()}
    return {"hazards": hazards, "lawVersions": versions}
