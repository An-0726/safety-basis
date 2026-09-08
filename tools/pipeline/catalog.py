"""Controlled proposals for laws, versions, clauses, links and tags.

The catalog workflow is deliberately small and conservative:

    request -> propose -> apply

``propose`` reads the master and seals a reviewable proposal.  ``apply`` does
not trust the seal: it re-checks the base state, rebuilds the proposal from the
request while holding a write lock, and applies all operations in one
transaction.  New records are always pending and no source/evidence row is
created by this module.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = Path(__file__).resolve().parent
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

import exchange  # noqa: E402
from master import dumps  # noqa: E402


VERSION = "catalog-v1"
KIND = "catalog"
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,79}\Z")
TEMP_PREFIXES = ("tmp:", "new:", "ref:")

CORE = {
    "law": {
        "table": "laws", "sheet": "法规库", "entity_type": "law",
        "required": ("canonical_name",),
        "fields": ("canonical_name", "issuer", "jurisdiction_code", "document_kind"),
        "prefix": "LF_",
    },
    "law_version": {
        "table": "law_versions", "sheet": "法规版本", "entity_type": "law_version",
        "required": ("official_name",),
        "fields": ("law_id", "version_key", "document_number", "official_name", "level",
                    "scope", "effective_date", "end_date", "validity_status", "source_url"),
        "prefix": "LV_",
    },
    "clause": {
        "table": "clauses", "sheet": "条款库", "entity_type": "clause",
        "required": ("article_path", "quote"),
        "fields": ("law_version_id", "article_path", "quote", "source_url"),
        "prefix": "C_",
    },
    "link": {
        "table": "links", "sheet": "依据关联", "entity_type": "link",
        "required": (),
        "fields": ("hazard_id", "clause_id", "role", "priority", "applicability", "jurisdiction_code"),
        "prefix": "K_",
    },
}
ALIASES = {
    "law": "law", "laws": "law",
    "law_version": "law_version", "law_versions": "law_version", "version": "law_version",
    "clause": "clause", "clauses": "clause",
    "link": "link", "links": "link",
    "hazard_tag": "hazard_tag", "hazard_tags": "hazard_tag", "tag": "hazard_tag",
    "law_alias": "law_alias", "law_aliases": "law_alias", "alias": "law_alias",
    "hazard": "hazard", "hazards": "hazard",
}
TABLE_FOR_TAG = {"hazard_tag": "hazard_tags", "law_alias": "law_aliases"}
CORE_TABLES = {kind: spec["table"] for kind, spec in CORE.items()}
UPDATE_SHEETS = {kind: spec["sheet"] for kind, spec in CORE.items()}
UPDATE_FIELDS = {
    "law": {"canonical_name", "issuer", "jurisdiction_code", "document_kind"},
    "law_version": {"document_number", "official_name", "level", "scope", "effective_date",
                     "end_date", "validity_status", "source_url"},
    "clause": {"article_path", "quote", "source_url"},
    "link": {"role", "priority", "applicability", "jurisdiction_code"},
    "hazard": {"title", "description", "measures", "category", "conditions", "note", "mode"},
}
OP_KEYS = {
    "op", "action", "operation", "entity", "type", "id", "ref", "targetId", "target",
    "match", "values", "data", "source", "sourceId", "sourceRowId", "jsonPointer",
    "evidenceId", "tags", "alias", "parentId", "hazardId", "lawId", "kind", "value",
    "ordinal",
}
REQUEST_KEYS = {"formatVersion", "kind", "requestId", "baseStateHash", "actor", "source", "operations", "metadata"}
SOURCE_KEYS = {"sourceId", "sourceRowId", "jsonPointer", "evidenceId", "raw"}
CLOSED = {"已失效", "merged", "rejected", "已废止"}


def _sha(value: Any) -> str:
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    sha = _sha(payload)
    return {**payload, "proposalId": "CAT_" + sha[:26], "proposalHash": sha}


def _open(path: Path, *, write: bool) -> sqlite3.Connection:
    path = Path(path).resolve()
    uri = path.as_uri() + ("?mode=rw" if write else "?mode=ro")
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _install_schema(conn: sqlite3.Connection) -> None:
    statement = ""
    schema = ROOT / "source/schemas/catalog.sql"
    for line in schema.read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("catalog schema contains an incomplete SQL statement")


def _text(value: Any, field: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须为文本")
    if "\ufffd" in value:
        raise ValueError(f"{field} 含编码损坏的替换字符；请从 UTF-8 原件重新提取")
    if not allow_empty and not value.strip():
        raise ValueError(f"{field} 不能为空")
    return value


def _key_text(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def _identity_key(values: dict[str, Any]) -> str:
    return "|".join(_key_text(values.get(field, ""))
                     for field in ("canonical_name", "issuer", "jurisdiction_code", "document_kind"))


def _id(value: Any, field: str = "id") -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError(f"{field} 无效")
    return value


def _is_temp(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(TEMP_PREFIXES)


def _copy_json(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("请求必须是可序列化 JSON") from exc
    return copy.deepcopy(value)


def _normal_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("request 必须为对象")
    extra = set(request) - REQUEST_KEYS
    if extra:
        raise ValueError("请求包含非法字段: " + ",".join(sorted(extra)))
    result = _copy_json(request)
    if result.get("formatVersion", VERSION) != VERSION:
        raise ValueError("请求格式版本不受支持")
    if result.get("kind", KIND) != KIND:
        raise ValueError("请求 kind 必须为 catalog")
    if "operations" not in result or not isinstance(result["operations"], list):
        raise ValueError("operations 必须为数组")
    if len(result["operations"]) > 200:
        raise ValueError("单个提案最多 200 个操作")
    if "requestId" in result:
        if not isinstance(result["requestId"], str) or not result["requestId"].strip():
            raise ValueError("requestId 必须为非空文本")
    if "baseStateHash" in result and (not isinstance(result["baseStateHash"], str)
                                       or not re.fullmatch(r"[0-9a-f]{64}", result["baseStateHash"])):
        raise ValueError("baseStateHash 必须为 SHA-256")
    if "actor" in result:
        _text(result["actor"], "actor", allow_empty=False)
    if "source" in result:
        _normal_source(result["source"])
    for operation in result["operations"]:
        if not isinstance(operation, dict):
            raise ValueError("每个 operation 必须为对象")
        extra = set(operation) - OP_KEYS
        if extra:
            raise ValueError("操作包含非法字段: " + ",".join(sorted(extra)))
    result.setdefault("formatVersion", VERSION)
    result.setdefault("kind", KIND)
    return result


def _normal_source(source: Any) -> dict[str, Any]:
    if source is None:
        return {}
    if not isinstance(source, dict):
        raise ValueError("source 必须为对象")
    extra = set(source) - SOURCE_KEYS
    if extra:
        raise ValueError("source 包含非法字段: " + ",".join(sorted(extra)))
    result = _copy_json(source)
    for field in ("sourceId", "sourceRowId", "jsonPointer", "evidenceId"):
        if field in result:
            _text(result[field], f"source.{field}", allow_empty=False)
    if "raw" in result and not isinstance(result["raw"], (dict, list, str, int, float, bool, type(None))):
        raise ValueError("source.raw 必须为 JSON 值")
    return result


def _operation_parts(operation: dict[str, Any]) -> tuple[str, str, str | None, dict[str, Any], dict[str, Any]]:
    op = operation.get("op", operation.get("action", operation.get("operation", "create")))
    if not isinstance(op, str) or op not in {"create", "reuse", "update"}:
        raise ValueError("操作类型必须是 create/reuse/update")
    entity = operation.get("entity", operation.get("type"))
    if not isinstance(entity, str) or entity not in ALIASES:
        raise ValueError("实体类型无效")
    entity = ALIASES[entity]
    raw_id = operation.get("id", operation.get("targetId", operation.get("target")))
    if raw_id is not None:
        _text(raw_id, "operation.id", allow_empty=False)
    ref = operation.get("ref")
    if ref is not None:
        _text(ref, "operation.ref", allow_empty=False)
    values = operation.get("values", operation.get("data", {}))
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ValueError("values 必须为对象")
    values = _copy_json(values)
    # Compact forms are accepted for tag/alias operations while still being
    # normalized to one auditable values object.
    if entity == "hazard_tag":
        for field, source in (("hazard_id", "hazardId"), ("kind", "kind"),
                              ("value", "value"), ("ordinal", "ordinal")):
            if source in operation:
                values.setdefault(field, operation[source])
        if "parentId" in operation:
            values.setdefault("hazard_id", operation["parentId"])
    elif entity == "law_alias":
        for field, source in (("law_id", "lawId"), ("alias", "alias"), ("ordinal", "ordinal")):
            if source in operation:
                values.setdefault(field, operation[source])
        if "parentId" in operation:
            values.setdefault("law_id", operation["parentId"])
    source = operation.get("source")
    if source is None:
        source = {}
        for field in ("sourceId", "sourceRowId", "jsonPointer", "evidenceId"):
            if field in operation:
                source[field] = operation[field]
    source = _normal_source(source)
    return op, entity, raw_id or ref, values, source


def _merge_source(top: dict[str, Any], own: dict[str, Any]) -> dict[str, Any]:
    parent = _normal_source(top.get("source", {}))
    result = dict(parent)
    for key, value in own.items():
        if key in result and result[key] != value:
            raise ValueError(f"同一操作的来源引用冲突: {key}")
        result[key] = value
    return _normal_source(result)


def _check_refs(conn: sqlite3.Connection, source: dict[str, Any]) -> None:
    sid, srid, eid = source.get("sourceId"), source.get("sourceRowId"), source.get("evidenceId")
    if sid is not None and conn.execute("SELECT 1 FROM sources WHERE id=?", (sid,)).fetchone() is None:
        raise ValueError(f"sourceId 不存在: {sid}")
    row = None
    if srid is not None:
        row = conn.execute("SELECT * FROM source_rows WHERE id=?", (srid,)).fetchone()
        if row is None:
            raise ValueError(f"sourceRowId 不存在: {srid}")
        if sid is None or row["source_id"] != sid:
            raise ValueError("sourceRowId 与 sourceId 不匹配")
        if "jsonPointer" in source and source["jsonPointer"] != row["json_pointer"]:
            raise ValueError("jsonPointer 与已有来源定位不匹配")
    if eid is not None and conn.execute("SELECT 1 FROM evidence WHERE id=?", (eid,)).fetchone() is None:
        raise ValueError(f"evidenceId 不存在: {eid}")


def _resolve(value: Any, refs: dict[str, str], field: str) -> str:
    if isinstance(value, dict):
        if set(value) != {"ref"}:
            raise ValueError(f"{field} 临时引用格式无效")
        value = value["ref"]
    _text(value, field, allow_empty=False)
    if value in refs:
        return refs[value]
    return value


def _row(conn: sqlite3.Connection, table: str, ident: str) -> dict[str, Any] | None:
    row = conn.execute(f'SELECT * FROM "{table}" WHERE id=?', (ident,)).fetchone()
    return dict(row) if row is not None else None


def _semantic(kind: str, row: dict[str, Any]) -> tuple[Any, ...]:
    if kind == "law":
        return (row.get("identity_key") or _identity_key(row),)
    if kind == "law_version":
        return (row["law_id"], _key_text(row["version_key"]))
    if kind == "clause":
        return (row["law_version_id"], _key_text(row["article_path"]))
    if kind == "link":
        return (row["hazard_id"], row["clause_id"])
    raise ValueError(f"不支持的实体: {kind}")


def _user_values(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    if kind not in CORE:
        return dict(row)
    return {field: row.get(field, "") for field in CORE[kind]["fields"]}


def _validate_create_values(kind: str, values: dict[str, Any]) -> None:
    if kind not in CORE:
        return
    allowed = set(CORE[kind]["fields"])
    extra = set(values) - allowed
    if extra:
        raise ValueError(f"{kind} 新增字段非法或包含受保护状态: " + ",".join(sorted(extra)))
    for field, value in values.items():
        if field == "priority":
            if type(value) is not int or value < 0:
                raise ValueError("priority 必须为非负整数")
        else:
            _text(value, field)
    for field in CORE[kind]["required"]:
        if not str(values.get(field, "")).strip():
            raise ValueError(f"{field} 不能为空")
    if kind == "law_version":
        validity = values.get("validity_status", "")
        if validity not in ("", "待核验", "现行有效", "即将生效", "已废止"):
            raise ValueError("validity_status 非法；核验状态仍由 review_status 控制")
        for field in ("effective_date", "end_date"):
            value = values.get(field, "")
            if value:
                try:
                    if dt.date.fromisoformat(value).isoformat() != value:
                        raise ValueError
                except ValueError as exc:
                    raise ValueError(f"{field} 必须为 YYYY-MM-DD") from exc
        if values.get("effective_date") and values.get("end_date") and values["end_date"] <= values["effective_date"]:
            raise ValueError("失效日期必须晚于生效日期")


def _semantic_matches(conn: sqlite3.Connection, kind: str, candidate: dict[str, Any]) -> list[dict[str, Any]]:
    table = CORE[kind]["table"]
    key = _semantic(kind, candidate)
    result = []
    for row in exchange.table_rows(conn, table):
        if _semantic(kind, row) == key:
            result.append(row)
    return result


def _find_by_match(conn: sqlite3.Connection, kind: str, match: dict[str, Any], refs: dict[str, str]) -> dict[str, Any]:
    if not isinstance(match, dict) or not match:
        raise ValueError("reuse 必须提供 id 或非空 match")
    match = _copy_json(match)
    if kind == "law":
        if "identity_key" in match:
            key = _text(match["identity_key"], "match.identity_key", allow_empty=False)
            rows = [r for r in exchange.table_rows(conn, "laws") if r["identity_key"] == key]
        else:
            fields = ("canonical_name", "issuer", "jurisdiction_code", "document_kind")
            if not set(fields) <= set(match):
                raise ValueError("law match 需要 identity_key 或完整身份字段")
            key = _identity_key(match)
            rows = [r for r in exchange.table_rows(conn, "laws") if r["identity_key"] == key]
    else:
        fields = {"law_version": ("law_id", "version_key"), "clause": ("law_version_id", "article_path"),
                  "link": ("hazard_id", "clause_id")} [kind]
        if not set(fields) <= set(match):
            raise ValueError(f"{kind} match 缺少语义键")
        resolved = {field: _resolve(match[field], refs, f"match.{field}") for field in fields}
        key = _semantic(kind, resolved)
        rows = [r for r in exchange.table_rows(conn, CORE[kind]["table"]) if _semantic(kind, r) == key]
    if len(rows) != 1:
        raise ValueError(f"reuse 未唯一匹配 {kind}: {len(rows)} 条")
    return rows[0]


def _stable_id(prefix: str, semantic: Any) -> str:
    return prefix + _sha(semantic)[:26].upper()


def _new_core_row(kind: str, ident: str, values: dict[str, Any], raw_operation: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    defaults = {field: "" for field in CORE[kind]["fields"]}
    defaults.update(values)
    defaults["id"] = ident
    defaults["revision"] = 1
    if kind != "link":
        defaults["checked"] = ""
    # The complete immutable request belongs in catalog_actions once. Copying
    # a batch into every business row makes both storage and proposal checking
    # quadratic in batch size, and repeats unrelated regulatory text.
    defaults["legacy_payload"] = dumps({"catalogRequestId": request["requestId"],
                                        "operation": raw_operation})
    if kind == "law":
        defaults.update(identity_key=_identity_key(values), identity_status="provisional", status="待整理")
    elif kind == "law_version":
        defaults.setdefault("validity_status", "")
        defaults.update(review_status="待整理")
    elif kind == "clause":
        defaults.update(status="待整理", identity_status="legacy_unreviewed")
    elif kind == "link":
        defaults.update(status="待核验")
    return defaults


def _check_new_id(conn: sqlite3.Connection, kind: str, ident: str) -> None:
    _id(ident)
    if conn.execute(f'SELECT 1 FROM "{CORE[kind]["table"]}" WHERE id=?', (ident,)).fetchone():
        raise ValueError(f"指定 ID 已存在: {ident}；请显式 reuse")


def _resolve_existing_id(raw: Any, refs: dict[str, str], field: str) -> str:
    if raw is None:
        raise ValueError(f"{field} 不能为空")
    return _resolve(raw, refs, field)


def _tag_parts(kind: str, values: dict[str, Any], refs: dict[str, str]) -> tuple[str, str, str, int | None]:
    allowed = {"hazard_id", "kind", "value", "ordinal"} if kind == "hazard_tag" else {"law_id", "alias", "ordinal"}
    extra = set(values) - allowed
    if extra:
        raise ValueError("标签/别名字段非法: " + ",".join(sorted(extra)))
    parent_field, value_field = (("hazard_id", "value") if kind == "hazard_tag" else ("law_id", "alias"))
    parent = _resolve_existing_id(values.get(parent_field), refs, parent_field)
    value = _text(values.get(value_field), value_field, allow_empty=False)
    ordinal = values.get("ordinal")
    if ordinal is not None and (type(ordinal) is not int or ordinal < 0):
        raise ValueError("ordinal 必须为非负整数")
    if kind == "hazard_tag":
        tag_kind = _text(values.get("kind"), "kind", allow_empty=False)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", tag_kind):
            raise ValueError("标签 kind 无效")
        return parent, tag_kind, value, ordinal
    return parent, "alias", value, ordinal


def _tag_existing(conn: sqlite3.Connection, kind: str, parent: str, value: str, tag_kind: str, ordinal: int | None) -> dict[str, Any] | None:
    if kind == "hazard_tag":
        rows = [dict(r) for r in conn.execute("SELECT * FROM hazard_tags WHERE hazard_id=? AND kind=? AND value=?", (parent, tag_kind, value))]
        if rows:
            if ordinal is not None and rows[0]["ordinal"] != ordinal:
                raise ValueError("相同标签语义键的 ordinal 不同；请复用已有标签")
            return rows[0]
        if ordinal is not None and conn.execute("SELECT 1 FROM hazard_tags WHERE hazard_id=? AND kind=? AND ordinal=?", (parent, tag_kind, ordinal)).fetchone():
            raise ValueError("标签 ordinal 已被其他值占用")
        return None
    rows = [dict(r) for r in conn.execute("SELECT * FROM law_aliases WHERE law_id=? AND alias=?", (parent, value))]
    if rows:
        if ordinal is not None and rows[0]["ordinal"] != ordinal:
            raise ValueError("相同别名语义键的 ordinal 不同；请复用已有别名")
        return rows[0]
    if ordinal is not None and conn.execute("SELECT 1 FROM law_aliases WHERE law_id=? AND ordinal=?", (parent, ordinal)).fetchone():
        raise ValueError("别名 ordinal 已被其他值占用")
    return None


def _next_ordinal(conn: sqlite3.Connection, kind: str, parent: str, tag_kind: str) -> int:
    if kind == "hazard_tag":
        return conn.execute("SELECT COALESCE(MAX(ordinal),-1)+1 FROM hazard_tags WHERE hazard_id=? AND kind=?", (parent, tag_kind)).fetchone()[0]
    return conn.execute("SELECT COALESCE(MAX(ordinal),-1)+1 FROM law_aliases WHERE law_id=?", (parent,)).fetchone()[0]


def _prepare_update(conn: sqlite3.Connection, kind: str, ident: str, values: dict[str, Any]) -> dict[str, Any]:
    if kind not in CORE and kind != "hazard":
        raise ValueError("标签/别名只支持 create 或 reuse")
    table = "hazards" if kind == "hazard" else CORE[kind]["table"]
    sheet = "隐患库" if kind == "hazard" else CORE[kind]["sheet"]
    before = _row(conn, table, ident)
    if before is None:
        raise ValueError(f"实体不存在: {ident}")
    if not isinstance(values, dict) or not values or set(values) - UPDATE_FIELDS[kind]:
        raise ValueError(f"{kind} update 字段不允许")
    change = exchange.make_change(sheet, before, values)
    after = change["after"]
    if kind == "clause":
        peers = conn.execute("SELECT id FROM clauses WHERE law_version_id=? AND article_path=? AND id<>?", (after["law_version_id"], after["article_path"], ident)).fetchone()
        if peers:
            raise ValueError("同一法规版本的条款定位已存在")
    return {"before": before, "after": after, "changedFields": change["changedFields"]}


def _prepare(conn: sqlite3.Connection, request: dict[str, Any], *, check_base: bool = True) -> dict[str, Any]:
    request = _normal_request(request)
    current_hash = exchange.state_hash(conn)
    if check_base and request.get("baseStateHash") and request["baseStateHash"] != current_hash:
        raise ValueError("母库已变化，拒绝过期请求")
    request_id = request.get("requestId") or "REQ_" + _sha(request)[:26]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,79}", request_id):
        raise ValueError("requestId 无效")
    request["requestId"] = request_id
    refs: dict[str, str] = {}
    used_ids: set[str] = set()
    operations: list[dict[str, Any]] = []
    planned_core: dict[str, dict[str, Any]] = {}
    planned_semantics: dict[tuple[str, tuple[Any, ...]], dict[str, Any]] = {}
    pending_tags: dict[tuple[Any, ...], dict[str, Any]] = {}
    pending_aliases: dict[tuple[Any, ...], dict[str, Any]] = {}

    for ordinal, raw in enumerate(request["operations"]):
        op, kind, raw_id, values, own_source = _operation_parts(raw)
        source = _merge_source(request, own_source)
        _check_refs(conn, source)
        if kind == "hazard":
            if op != "update":
                raise ValueError("hazard 只支持已有内容 update")
            if raw_id is None:
                raise ValueError("hazard update 必须指定 id")
            ident = _resolve_existing_id(raw_id, refs, "hazard.id")
            item = _prepare_update(conn, kind, ident, values)
            prepared = {"ordinal": ordinal, "operation": op, "entity": kind, "id": ident,
                        "ref": raw.get("ref"), "values": values, "source": source, **item}
            operations.append(prepared)
            continue
        if kind in CORE:
            if op == "update":
                if raw_id is None:
                    raise ValueError(f"{kind} update 必须指定 id")
                ident = _resolve_existing_id(raw_id, refs, f"{kind}.id")
                item = _prepare_update(conn, kind, ident, values)
                prepared = {"ordinal": ordinal, "operation": op, "entity": kind, "id": ident,
                            "ref": raw.get("ref"), "values": values, "source": source, **item}
                operations.append(prepared)
                continue
            if op == "reuse":
                if raw_id is not None and not _is_temp(raw_id):
                    ident = _resolve_existing_id(raw_id, refs, f"{kind}.id")
                    before = _row(conn, CORE[kind]["table"], ident)
                    if before is None:
                        raise ValueError(f"reuse 目标不存在: {ident}")
                elif raw_id is not None and raw_id in refs:
                    ident = refs[raw_id]
                    before = _row(conn, CORE[kind]["table"], ident)
                    if before is None:
                        raise ValueError(f"reuse 临时目标不存在: {raw_id}")
                else:
                    match = raw.get("match")
                    before = _find_by_match(conn, kind, match, refs)
                    ident = before["id"]
                if values:
                    if kind == "law" and "identity_key" in values:
                        raise ValueError("identity_key 是受保护字段")
                    for field, value in values.items():
                        if field not in CORE[kind]["fields"] or before.get(field) != value:
                            raise ValueError("reuse 的 values 与已有记录不一致")
                if raw.get("ref"):
                    if raw["ref"] in refs and refs[raw["ref"]] != ident:
                        raise ValueError("临时引用重复")
                    refs[raw["ref"]] = ident
                operations.append({"ordinal": ordinal, "operation": op, "entity": kind, "id": ident,
                                   "ref": raw.get("ref"), "values": values, "source": source,
                                   "before": before, "after": before, "changedFields": []})
                continue
            # create
            _validate_create_values(kind, values)
            normalized = dict(values)
            if kind == "law_version":
                normalized["law_id"] = _resolve_existing_id(normalized.get("law_id"), refs, "law_id")
                if _row(conn, "laws", normalized["law_id"]) is None and normalized["law_id"] not in planned_core:
                    raise ValueError(f"law 外键不存在: {normalized['law_id']}")
            elif kind == "clause":
                normalized["law_version_id"] = _resolve_existing_id(normalized.get("law_version_id"), refs, "law_version_id")
                if _row(conn, "law_versions", normalized["law_version_id"]) is None and normalized["law_version_id"] not in planned_core:
                    raise ValueError(f"law_version 外键不存在: {normalized['law_version_id']}")
            elif kind == "link":
                normalized["hazard_id"] = _resolve_existing_id(normalized.get("hazard_id"), refs, "hazard_id")
                normalized["clause_id"] = _resolve_existing_id(normalized.get("clause_id"), refs, "clause_id")
                if _row(conn, "hazards", normalized["hazard_id"]) is None:
                    raise ValueError(f"hazard 外键不存在: {normalized['hazard_id']}")
                if _row(conn, "clauses", normalized["clause_id"]) is None and normalized["clause_id"] not in planned_core:
                    raise ValueError(f"clause 外键不存在: {normalized['clause_id']}")
            if kind == "law":
                normalized.setdefault("issuer", "")
                normalized.setdefault("jurisdiction_code", "")
                normalized.setdefault("document_kind", "")
            candidate = _new_core_row(kind, "PENDING", normalized, raw, request)
            matches = _semantic_matches(conn, kind, candidate)
            planned_match = planned_semantics.get((kind, _semantic(kind, candidate)))
            if planned_match is not None:
                matches = [planned_match]
            if matches:
                existing = matches[0]
                if _user_values(kind, existing) != _user_values(kind, candidate):
                    raise ValueError(f"{kind} 语义键已存在但内容不同；请显式 reuse {existing['id']}")
                if raw_id and not _is_temp(raw_id) and raw_id != existing["id"]:
                    raise ValueError(f"{kind} 指定 ID 与已有语义记录不同；请显式 reuse {existing['id']}")
                ident = existing["id"]
                result_op = "reuse"
                before, after = existing, existing
                changed = []
            else:
                requested = raw_id if raw_id and not _is_temp(raw_id) else None
                ident = requested or _stable_id(CORE[kind]["prefix"], _semantic(kind, candidate))
                _check_new_id(conn, kind, ident)
                if ident in used_ids:
                    raise ValueError(f"提案内重复 ID: {ident}")
                before, after = None, _new_core_row(kind, ident, normalized, raw, request)
                result_op, changed = "create", list(after)
                used_ids.add(ident)
                planned_core[ident] = after
                planned_semantics[(kind, _semantic(kind, after))] = after
            if raw.get("ref") or (raw_id and _is_temp(raw_id)):
                ref = raw.get("ref") or raw_id
                if ref in refs and refs[ref] != ident:
                    raise ValueError("临时引用重复")
                refs[ref] = ident
            operations.append({"ordinal": ordinal, "operation": result_op, "entity": kind, "id": ident,
                               "ref": raw.get("ref") or (raw_id if _is_temp(raw_id) else None),
                               "values": normalized, "source": source, "before": before, "after": after,
                               "changedFields": changed})
            continue
        # Tags and aliases are append-only child rows.  Updating a tag's value
        # would erase source meaning, so callers must add a new value instead.
        if kind not in TABLE_FOR_TAG:
            raise ValueError("实体类型不支持")
        if op not in {"create", "reuse"}:
            raise ValueError("标签/别名只支持 create 或 reuse")
        if kind == "hazard_tag":
            parent, tag_kind, value, ordinal_value = _tag_parts(kind, values, refs)
            if _row(conn, "hazards", parent) is None:
                raise ValueError(f"hazard 不存在: {parent}")
            key = (parent, tag_kind, value)
            existing = _tag_existing(conn, kind, parent, value, tag_kind, ordinal_value)
            if existing is None and key in pending_tags:
                existing = pending_tags[key]
            if existing is not None:
                if op == "create" and raw.get("ref"):
                    refs[raw["ref"]] = f"{parent}:{tag_kind}:{value}"
                operations.append({"ordinal": ordinal, "operation": "reuse", "entity": kind,
                                   "id": f"{parent}:{tag_kind}:{value}", "ref": raw.get("ref"),
                                   "values": {"hazard_id": parent, "kind": tag_kind, "value": value, "ordinal": existing["ordinal"]},
                                   "source": source, "before": existing, "after": existing, "changedFields": []})
                continue
            occupied = {row['ordinal'] for row in pending_tags.values()
                        if row['hazard_id'] == parent and row['kind'] == tag_kind}
            if ordinal_value is None:
                ordinal_value = max(_next_ordinal(conn, kind, parent, tag_kind), max(occupied, default=-1) + 1)
            elif ordinal_value in occupied:
                raise ValueError('提案内同一标签位置已被其他值占用')
            after = {"hazard_id": parent, "kind": tag_kind, "value": value, "ordinal": ordinal_value}
            pending_tags[key] = after
            operations.append({"ordinal": ordinal, "operation": "create", "entity": kind,
                               "id": f"{parent}:{tag_kind}:{value}", "ref": raw.get("ref"),
                               "values": after, "source": source, "before": None, "after": after,
                               "changedFields": list(after)})
        else:
            parent, _, alias, ordinal_value = _tag_parts(kind, values, refs)
            if _row(conn, "laws", parent) is None and parent not in planned_core:
                raise ValueError(f"law 不存在: {parent}")
            key = (parent, alias)
            existing = _tag_existing(conn, kind, parent, alias, "alias", ordinal_value)
            if existing is None and key in pending_aliases:
                existing = pending_aliases[key]
            if existing is not None:
                operations.append({"ordinal": ordinal, "operation": "reuse", "entity": kind,
                                   "id": f"{parent}:{alias}", "ref": raw.get("ref"),
                                   "values": {"law_id": parent, "alias": alias, "ordinal": existing["ordinal"]},
                                   "source": source, "before": existing, "after": existing, "changedFields": []})
                continue
            occupied = {row['ordinal'] for row in pending_aliases.values() if row['law_id'] == parent}
            if ordinal_value is None:
                ordinal_value = max(_next_ordinal(conn, kind, parent, "alias"), max(occupied, default=-1) + 1)
            elif ordinal_value in occupied:
                raise ValueError('提案内同一别名位置已被其他值占用')
            after = {"law_id": parent, "alias": alias, "ordinal": ordinal_value}
            pending_aliases[key] = after
            operations.append({"ordinal": ordinal, "operation": "create", "entity": kind,
                               "id": f"{parent}:{alias}", "ref": raw.get("ref"),
                               "values": after, "source": source, "before": None, "after": after,
                               "changedFields": list(after)})
    return {"request": request, "requestId": request_id, "baseStateHash": current_hash, "operations": operations}


def _payload_from_request(conn: sqlite3.Connection, request: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare(conn, request)
    payload = {"formatVersion": VERSION, "kind": KIND, "requestId": prepared["requestId"],
               "baseStateHash": prepared["baseStateHash"], "request": prepared["request"],
               "operations": prepared["operations"]}
    return _seal(payload)


def request_catalog(db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    """Validate a request and return its sealed proposal without writing it."""
    conn = _open(Path(db_path), write=False)
    try:
        conn.execute("BEGIN")
        exchange.check_integrity(conn)
        return _payload_from_request(conn, request)
    finally:
        conn.close()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    exchange.check_output(Path(path), ".json")
    exchange.install_output(Path(path), (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def propose_catalog(db_path: Path, request: dict[str, Any] | Path, output: Path | None = None) -> dict[str, Any]:
    if isinstance(request, (str, Path)):
        request = json.loads(Path(request).read_text(encoding="utf-8-sig"))
    proposal = request_catalog(Path(db_path), request)
    result = {"ok": True, "proposalId": proposal["proposalId"], "proposalHash": proposal["proposalHash"],
              "requestId": proposal["requestId"], "operationCount": len(proposal["operations"]),
              "proposal": proposal}
    if output is not None:
        _write_json(Path(output), proposal)
        result["proposalPath"] = str(Path(output).resolve())
    return result


def _load_proposal(proposal: dict[str, Any] | Path) -> dict[str, Any]:
    if isinstance(proposal, (str, Path)):
        proposal = json.loads(Path(proposal).read_text(encoding="utf-8-sig"))
    if not isinstance(proposal, dict):
        raise ValueError("proposal 必须为对象")
    payload = {key: value for key, value in proposal.items() if key not in {"proposalId", "proposalHash"}}
    if proposal.get("proposalHash") != _sha(payload) or proposal.get("proposalId") != "CAT_" + _sha(payload)[:26]:
        raise ValueError("提案哈希无效；重封哈希不能替代业务校验")
    if payload.get("formatVersion") != VERSION or payload.get("kind") != KIND:
        raise ValueError("提案格式版本不受支持")
    if not isinstance(payload.get("request"), dict) or not isinstance(payload.get("operations"), list):
        raise ValueError("提案结构不完整")
    return proposal


def _row_update(conn: sqlite3.Connection, table: str, before: dict[str, Any], after: dict[str, Any]) -> None:
    fields = [field for field in after if field in before and after[field] != before[field]]
    if not fields:
        raise ValueError("update 没有实际变化")
    assignments = ",".join(f'"{field}"=?' for field in fields)
    params = [after[field] for field in fields] + [before["id"], before["revision"]]
    result = conn.execute(f'UPDATE "{table}" SET {assignments} WHERE id=? AND revision=?', params)
    if result.rowcount != 1:
        raise ValueError(f"实体版本已变化: {before['id']}")


def _tag_parent(conn: sqlite3.Connection, entity: str, parent: str, content_changed: set[tuple[str, str]]) -> dict[str, Any] | None:
    table, field = (("hazards", "hazard_id") if entity == "hazard_tag" else ("laws", "law_id"))
    key = (table, parent)
    if key in content_changed:
        # The content update already increments revision and demotes status.
        return None
    row = conn.execute(f'SELECT * FROM "{table}" WHERE id=?', (parent,)).fetchone()
    if row is None:
        raise ValueError(f"标签父实体不存在: {parent}")
    status = row["status"]
    if status not in CLOSED:
        status = "待核验"
    before = dict(row)
    conn.execute(f'UPDATE "{table}" SET revision=?,checked=?,status=? WHERE id=? AND revision=?',
                 (row["revision"] + 1, "", status, parent, row["revision"]))
    after = dict(before)
    after.update(revision=before["revision"] + 1, checked="", status=status)
    return {"entityType": "hazard" if entity == "hazard_tag" else "law", "id": parent,
            "operation": "tag-revision", "before": before, "after": after}


def _apply_operations(conn: sqlite3.Connection, operations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    content_changed: set[tuple[str, str]] = set()
    # Apply core updates/creates first so tag parent revision changes can be
    # coalesced with a content revision in the same proposal.
    ordered = sorted(operations, key=lambda item: (item["entity"] not in CORE, item["ordinal"]))
    for item in ordered:
        entity, op, before, after = item["entity"], item["operation"], item.get("before"), item["after"]
        if entity in CORE or entity == "hazard":
            table = CORE[entity]["table"] if entity in CORE else "hazards"
            if op == "create":
                fields = list(after)
                conn.execute(f'INSERT INTO "{table}" ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})', [after[field] for field in fields])
                result = {"entityType": entity, "id": after["id"], "operation": op, "before": None, "after": after}
                changes.append(result)
                content_changed.add((table, after["id"]))
            elif op == "update":
                _row_update(conn, table, before, after)
                result = {"entityType": entity, "id": after["id"], "operation": op, "before": before, "after": after}
                changes.append(result)
                content_changed.add((table, after["id"]))
            else:
                result = {"entityType": entity, "id": after["id"], "operation": "reuse", "before": before, "after": after}
            events.append({"entityType": entity, "id": after["id"], "operation": result["operation"],
                           "source": item["source"], "before": before, "after": after})
            continue
        if op == "reuse":
            events.append({"entityType": entity, "id": item["id"], "operation": op,
                           "source": item["source"], "before": before, "after": after})
            continue
        if entity == "hazard_tag":
            parent = after["hazard_id"]
            parent_change = _tag_parent(conn, entity, parent, content_changed)
            if parent_change is not None:
                changes.append(parent_change)
            conn.execute("INSERT INTO hazard_tags(hazard_id,kind,value,ordinal) VALUES(?,?,?,?)",
                         (parent, after["kind"], after["value"], after["ordinal"]))
            changes.append({"entityType": entity, "id": item["id"], "operation": op, "before": None, "after": after})
        elif entity == "law_alias":
            parent = after["law_id"]
            parent_change = _tag_parent(conn, entity, parent, content_changed)
            if parent_change is not None:
                changes.append(parent_change)
            conn.execute("INSERT INTO law_aliases(law_id,alias,ordinal) VALUES(?,?,?)",
                         (parent, after["alias"], after["ordinal"]))
            changes.append({"entityType": entity, "id": item["id"], "operation": op, "before": None, "after": after})
        events.append({"entityType": entity, "id": item["id"], "operation": op,
                       "source": item["source"], "before": None, "after": after})
    return changes, events


def apply_catalog(db_path: Path, proposal: dict[str, Any] | Path, actor: str | None = None) -> dict[str, Any]:
    proposal = _load_proposal(proposal)
    payload = {key: value for key, value in proposal.items() if key not in {"proposalId", "proposalHash"}}
    supplied_actor = actor if actor is not None else payload["request"].get("actor", "")
    if not isinstance(supplied_actor, str) or not supplied_actor.strip():
        raise ValueError("actor 不能为空")
    conn = _open(Path(db_path), write=True)
    try:
        conn.execute("BEGIN IMMEDIATE")
        _install_schema(conn)
        old = conn.execute("SELECT * FROM catalog_actions WHERE id=?", (proposal["proposalId"],)).fetchone()
        if old is not None:
            if old["proposal_hash"] != proposal["proposalHash"]:
                raise ValueError("提案 ID 冲突")
            return {**json.loads(old["receipt_json"]), "status": "already_applied"}
        old_request = conn.execute("SELECT * FROM catalog_actions WHERE request_id=?", (payload["requestId"],)).fetchone()
        if old_request is not None:
            raise ValueError("requestId 已提交但 proposalId 不同")
        exchange.check_integrity(conn)
        if exchange.state_hash(conn) != payload["baseStateHash"]:
            raise ValueError("母库已变化，拒绝提交过期提案")
        rebuilt = _payload_from_request(conn, payload["request"])
        # The exact operation list (including before/after snapshots and source
        # references) is part of the seal.  A recomputed seal cannot change it
        # without also passing every business rule above.
        if rebuilt["baseStateHash"] != payload["baseStateHash"] or dumps(rebuilt["operations"]) != dumps(payload["operations"]):
            raise ValueError("提案与当前母库或请求重建结果不一致")
        if not payload["operations"]:
            conn.rollback()
            return {"ok": True, "status": "no_changes", "proposalId": proposal["proposalId"],
                    "requestId": payload["requestId"]}
        changes, events = _apply_operations(conn, payload["operations"])
        exchange.check_integrity(conn)
        result_hash = exchange.state_hash(conn)
        applied_at = _now()
        receipt = {"ok": True, "status": "applied", "proposalId": proposal["proposalId"],
                   "requestId": payload["requestId"], "actor": supplied_actor.strip(),
                   "baseStateHash": payload["baseStateHash"], "resultStateHash": result_hash,
                   "appliedAt": applied_at, "assignments": [
                        {"ordinal": item["ordinal"], "entity": item["entity"], "id": item["id"],
                        "operation": item["operation"], "ref": item.get("ref")}
                       for item in payload["operations"]],
                   "sourceEvidence": [item["source"] for item in payload["operations"] if item.get("source")],
                   "entityChanges": changes}
        conn.execute("INSERT INTO catalog_actions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                     (proposal["proposalId"], payload["requestId"], proposal["proposalHash"], payload["baseStateHash"],
                      result_hash, supplied_actor.strip(), "applied", _now(), applied_at,
                      dumps(payload["request"]), dumps(proposal), dumps(receipt)))
        for ordinal, event in enumerate(events):
            conn.execute("INSERT INTO catalog_events VALUES(?,?,?,?,?,?,?,?)",
                         (proposal["proposalId"], ordinal, event["entityType"], event["id"], event["operation"],
                          dumps(event["source"]), None if event["before"] is None else dumps(event["before"]), dumps(event["after"])))
        conn.commit()
        return receipt
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Short aliases keep the three-stage API convenient for callers and tests.
request = request_catalog
propose = propose_catalog
apply = apply_catalog
create_proposal = propose_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "source/master/safety.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    req = sub.add_parser("request")
    req.add_argument("--input", type=Path, required=True)
    req.add_argument("--output", type=Path)
    prop = sub.add_parser("propose")
    prop.add_argument("--request", type=Path, required=True)
    prop.add_argument("--output", type=Path, required=True)
    app = sub.add_parser("apply")
    app.add_argument("--proposal", type=Path, required=True)
    app.add_argument("--actor", required=True)
    args = parser.parse_args()
    try:
        if args.command == "request":
            result = propose_catalog(args.db, args.input, args.output)
        elif args.command == "propose":
            result = propose_catalog(args.db, args.request, args.output)
        else:
            result = apply_catalog(args.db, args.proposal, args.actor)
        print(json.dumps({k: v for k, v in result.items() if k != "proposal"}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
