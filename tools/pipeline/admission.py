"""Reviewed staging-to-master admission and conservative hazard merges.

plan -> edit decisions -> propose -> apply. The staging database is never written
here; the master owns receipts, stable IDs and source-to-knowledge bindings.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from difflib import SequenceMatcher
import json
import mimetypes
import os
from pathlib import Path, PureWindowsPath
import sqlite3
import uuid

import exchange
import intake
from master import ROOT, dumps, digest, now, pointer

VERSION = "safety-admission-v1"
CLOSED = {"原始数据", "已失效", "merged", "rejected"}
STAGING_TABLES = ("sources", "source_locations", "import_runs", "source_rows", "parsed_rows", "candidates", "candidate_sources")


def open_db(path, *, write=False):
    conn = sqlite3.connect(Path(path).resolve().as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    return conn


def rows(conn, table):
    return exchange.table_rows(conn, table) if exchange.has_table(conn, table) else []


def snapshot(conn):
    exchange.check_integrity(conn)
    return digest(dumps({table: exchange.table_rows(conn, table) for table in STAGING_TABLES}))


def hazard(conn, ident):
    row = conn.execute("SELECT * FROM hazards WHERE id=?", (ident,)).fetchone()
    if row is None:
        raise ValueError(f"隐患不存在: {ident}")
    return dict(row)


def survivor(conn, ident):
    visited = set()
    while True:
        if ident in visited:
            raise ValueError("母库存在合并循环")
        visited.add(ident)
        row = hazard(conn, ident)
        if row["status"] != "merged":
            if row["status"] in CLOSED or row["merged_into"]:
                raise ValueError(f"目标隐患已关闭或合并状态异常: {ident}")
            return ident
        if not row["merged_into"]:
            raise ValueError(f"已合并记录缺少目标: {ident}")
        ident = row["merged_into"]


def bindings(conn):
    result = {}
    for row in rows(conn, "candidate_admissions"):
        result.setdefault(row["candidate_id"], []).append(row["hazard_id"])
    return result


def source_name(location):
    name = PureWindowsPath(location).name if "\\" in location else Path(location).name
    if not name or name in (".", ".."):
        raise ValueError("来源文件名无效")
    return name


def bundle(staging, candidate_id):
    row = staging.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
    if row is None or row["status"] != "待整理":
        raise ValueError(f"候选不存在或状态异常: {candidate_id}")
    row = dict(row)
    normalized = json.loads(row["normalized_json"])
    if not isinstance(normalized, dict) or any(not isinstance(v, str) for v in normalized.values()):
        raise ValueError("候选字段值必须是规范化文本")
    if normalized.get("recordType") != "inspection" and not normalized.get("title"):
        raise ValueError("隐患候选必须包含非空标题；检查项目用 inspection 类型保存")
    fp = digest(intake.dumps(normalized))
    if row["fingerprint"] != fp or candidate_id != "D_" + fp:
        raise ValueError("候选指纹与内容不匹配")
    origins = []
    for origin in staging.execute("SELECT * FROM candidate_sources WHERE candidate_id=? ORDER BY source_row_id,run_id", (candidate_id,)):
        source_row = dict(staging.execute("SELECT * FROM source_rows WHERE id=?", (origin["source_row_id"],)).fetchone())
        run = dict(staging.execute("SELECT * FROM import_runs WHERE id=?", (origin["run_id"],)).fetchone())
        if run["status"] != "complete" or source_row["source_id"] != run["source_id"]:
            raise ValueError("候选关联了失败批次或来源不一致")
        source = dict(staging.execute("SELECT * FROM sources WHERE id=?", (run["source_id"],)).fetchone())
        expected_row = "R_" + digest(intake.dumps([source["sha256"], source_row["sheet"], source_row["row_number"]]))
        if source["id"] != "S_" + source["sha256"] or source_row["id"] != expected_row:
            raise ValueError("来源或原始行 ID 与身份指纹不一致")
        parsed = staging.execute("SELECT raw_json FROM parsed_rows WHERE run_id=? AND source_row_id=?", (run["id"], source_row["id"])).fetchone()
        if parsed is None:
            raise ValueError("缺少对应解析批次的原始值")
        raw = json.loads(parsed[0])
        mapping = json.loads(run["mapping_json"])
        extensions = [ext for ext in intake.EXTENSIONS if "I_" + digest(intake.dumps([source["sha256"], ext, run["parser_version"], mapping])) == run["id"]]
        if len(extensions) != 1:
            raise ValueError("解析批次身份与来源/配置不一致")
        if extensions[0] == ".json":
            cleaned = intake.mapped(list(raw), list(raw.values()), mapping)
        else:
            cleaned = intake.mapped(raw["headers"], raw["values"], mapping)
        if {k: v for k, v in cleaned.items() if k != "externalId"} != normalized:
            raise ValueError("候选内容与原始行的映射结果不一致")
        locations = [r[0] for r in staging.execute("SELECT original_path FROM source_locations WHERE source_id=? ORDER BY original_path", (source["id"],))]
        if not locations:
            raise ValueError("来源缺少原始文件位置")
        origins.append({"source": source, "row": source_row, "run": run, "parsedRaw": parsed[0], "locations": locations})
    if not origins:
        raise ValueError("候选没有可追溯来源")
    return {"candidateId": candidate_id, "fingerprint": fp, "normalized": normalized, "origins": origins}


def needs_admission(master, item):
    bound = bindings(master).get(item["candidateId"])
    if bound is None:
        return True
    # Closed bindings still need a review outcome; they cannot be reactivated.
    try:
        targets = {survivor(master, ident) for ident in bound}
    except ValueError:
        return True
    for origin in item["origins"]:
        for target in targets:
            if not master.execute("SELECT 1 FROM intake_provenance WHERE entity_id=? AND candidate_id=? AND source_row_id=? AND transform_run_id=?",
                                  (target, item["candidateId"], origin["row"]["id"], origin["run"]["id"])).fetchone():
                return True
        for location in origin["locations"]:
            if not master.execute("SELECT 1 FROM intake_source_locations WHERE source_id=? AND original_path=?", (origin["source"]["id"], location)).fetchone():
                return True
    return False


def matches(normalized, choices, limit=5):
    ranked = []
    title = intake.norm(normalized["title"])
    for ident, row in choices:
        other = intake.norm(row.get("title", ""))
        score = SequenceMatcher(None, title[:240], other[:240], autojunk=False).ratio()
        if title != other and score < .55:
            continue
        ranked.append({"target": ident, "title": row["title"], "conditions": row.get("conditions", ""),
                       "measures": row.get("measures", ""), "similarity": round(score, 3),
                       "warning": "仅供召回；须核对否定词、阈值、对象、适用条件和来源，不能据相似度自动合并"})
    return sorted(ranked, key=lambda row: (-row["similarity"], row["target"]))[:limit]


def write_json(output, value):
    output = Path(output).resolve()
    exchange.check_output(output, ".json")
    exchange.install_output(output, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def seal(payload):
    sha = digest(dumps(payload))
    return {**payload, "proposalId": "A_" + sha, "proposalHash": sha}


def unseal(proposal):
    payload = {k: v for k, v in proposal.items() if k not in ("proposalId", "proposalHash")}
    if seal(payload) != proposal or payload.get("formatVersion") != VERSION:
        raise ValueError("提案格式或哈希无效")
    return payload


def plan(db, staging_db, output, *, limit=20, candidate_ids=None):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("limit 必须在 1..200 之间；按小批次审阅")
    with closing(open_db(db)) as master, closing(open_db(staging_db)) as staging:
        exchange.check_integrity(master)
        master_hash, intake_hash = exchange.state_hash(master), snapshot(staging)
        ids = sorted(set(candidate_ids)) if candidate_ids else [r[0] for r in staging.execute("SELECT id FROM candidates ORDER BY id")]
        selected = []
        for cid in ids:
            item = bundle(staging, cid)
            if needs_admission(master, item):
                selected.append(item)
            if len(selected) == limit:
                break
        choices = [(r["id"], r) for r in rows(master, "hazards") if r["status"] not in CLOSED and not r["merged_into"]]
        bound = bindings(master)
        items = []
        for item in selected:
            cid = item["candidateId"]
            inspection = item["normalized"].get("recordType") == "inspection"
            action, target, reason = "review", "", ""
            if cid in bound:
                try:
                    targets = sorted({survivor(master, ident) for ident in bound[cid]})
                    target = targets[0] if not inspection and len(targets) == 1 else ""
                    action, reason = ("attach" if target else "reuse"), "候选已绑定母库身份，本次仅补充来源"
                except ValueError:
                    pass
            peers = [("new:" + other["candidateId"], other["normalized"]) for other in selected if other["candidateId"] != cid and other["normalized"].get("title")]
            decision = {"action": action, "target": target, "reason": reason}
            if inspection and action == "review":
                decision.update(sourceReviewed=False, basis=item["normalized"].get("basis", ""),
                                quote=item["normalized"].get("quote", ""), hazards=[])
            items.append({"candidateId": cid, "normalized": item["normalized"],
                          "sources": [{"name": source_name(o["locations"][0]), "sourceId": o["source"]["id"],
                                       "sheet": o["row"]["sheet"], "row": o["row"]["row_number"], "runId": o["run"]["id"]} for o in item["origins"]],
                          "suggestedMatches": [] if inspection else matches(item["normalized"], choices + peers),
                          "preparation": "先校正依据/原文对应，再拆分通用隐患；原检查结果不变" if inspection else "核对隐患概念和适用条件",
                          "decision": decision})
        document = {"formatVersion": VERSION, "kind": "admission-review", "baseStateHash": master_hash,
                    "intakeStateHash": intake_hash, "items": items}
        write_json(output, document)
        return {"ok": True, "reviewFile": str(output), "candidateCount": len(items),
                "needsDecision": sum(x["decision"]["action"] == "review" for x in items)}


def admission_payload(master, staging, decisions):
    if not isinstance(decisions, list) or len(decisions) > 200:
        raise ValueError("decisions 必须是最多 200 项的数组")
    seen, items, operations = set(), [], []
    bound = bindings(master)
    for decision in decisions:
        base_fields = {"candidateId", "action", "target", "reason"}
        if not base_fields <= set(decision) or any(not isinstance(decision[k], str) for k in base_fields):
            raise ValueError("决定必须包含文本 candidateId/action/target/reason")
        cid = decision["candidateId"]
        if cid in seen:
            raise ValueError("候选重复")
        seen.add(cid)
        if decision["action"] not in ("create", "attach", "derive", "reuse", "defer") or not decision["reason"].strip():
            raise ValueError("每条候选必须选择 create/attach/derive/reuse/defer，并说明理由")
        item = bundle(staging, cid)
        inspection = item["normalized"].get("recordType") == "inspection"
        action, target = decision["action"], decision["target"]
        expected = base_fields | ({"sourceReviewed", "basis", "quote", "hazards"} if action == "derive" or (inspection and action == "defer" and "hazards" in decision) else set())
        if set(decision) != expected:
            raise ValueError("决定包含未知字段或缺少必填字段")
        if action != "attach" and target:
            raise ValueError("只有 attach 可以指定顶层 target")
        if inspection and action in ("create", "attach"):
            raise ValueError("检查项目不能直接作为隐患入库；先校正提取并用 derive 拆分，或 defer")
        if action == "create" and cid in bound:
            raise ValueError("已入库候选不能再次新建隐患")
        if action == "attach":
            if not target:
                raise ValueError("attach 必须指定目标")
            if not target.startswith("new:"):
                if survivor(master, target) != target:
                    raise ValueError("请直接关联合并后的存续 ID")
            if cid in bound and {survivor(master, ident) for ident in bound[cid]} != {target}:
                raise ValueError("已绑定候选不能改绑其他隐患；请使用合并提案")
        if action in ("create", "attach"):
            if item["normalized"]["title"].strip() in ("符合", "不符合", "基本符合", "等待转译", "【等待转译】", "【跳过】"):
                raise ValueError("检查结果或占位符不能当作隐患名称")
            operations.append({"candidateId": cid, "ref": "new:" + cid, "action": action,
                               "target": target, "content": item["normalized"], "reason": decision["reason"]})
        elif action == "reuse":
            if cid not in bound:
                raise ValueError("reuse 只能补充已入库候选的来源")
            for ident in sorted({survivor(master, old) for old in bound[cid]}):
                operations.append({"candidateId": cid, "ref": "reuse:" + cid + ":" + ident, "action": "attach",
                                   "target": ident, "content": {}, "reason": decision["reason"]})
        elif action == "derive":
            if not inspection or cid in bound:
                raise ValueError("derive 仅用于尚未入库的检查项目")
            if decision["sourceReviewed"] is not True or any(not isinstance(decision[k], str) or not decision[k].strip() for k in ("basis", "quote")):
                raise ValueError("先确认依据与原文的列对应，填写依据/原文并设置 sourceReviewed=true；这不代表法规终审")
            if not isinstance(decision["hazards"], list) or not 1 <= len(decision["hazards"]) <= 30:
                raise ValueError("一条检查项目拆分为 1..30 条原子隐患模板")
            refs, contents = set(), set()
            for draft in decision["hazards"]:
                if set(draft) != {"ref", "title", "conditions", "measures", "action", "target", "reason"} or any(not isinstance(v, str) for v in draft.values()):
                    raise ValueError("模板字段必须是 ref/title/conditions/measures/action/target/reason 文本")
                if any("\ufffd" in value for value in draft.values()) or any("\ufffd" in decision[field] for field in ("basis", "quote")):
                    raise ValueError("拆分材料含编码损坏的替换字符；保留原件并重新提取，不能入库")
                if not draft["ref"] or draft["ref"] in refs:
                    raise ValueError("模板 ref 不能为空或重复")
                refs.add(draft["ref"])
                if draft["action"] not in ("create", "attach") or not draft["reason"].strip():
                    raise ValueError("每个模板需选择 create/attach 并说明理由")
                if (draft["action"] == "create" and draft["target"]) or (draft["action"] == "attach" and not draft["target"]):
                    raise ValueError("模板 target 与操作不一致")
                title = draft["title"].strip()
                if not title or title in ("符合", "不符合", "基本符合", "等待转译", "【等待转译】", "【跳过】"):
                    raise ValueError("模板应填写具体隐患描述，不能填写检查结果或占位符")
                content = {k: draft[k] for k in ("title", "conditions", "measures")}
                fingerprint = dumps(content)
                if fingerprint in contents:
                    raise ValueError("同一来源重复产生相同模板")
                contents.add(fingerprint)
                operations.append({"candidateId": cid, "ref": "new:" + cid + ":" + draft["ref"],
                                   "action": draft["action"], "target": draft["target"], "content": content,
                                   "reason": draft["reason"], "derivation": {"basis": decision["basis"], "quote": decision["quote"],
                                   "sourceResult": item["normalized"].get("compliance", ""), "sourceReviewed": True}})
        items.append({**decision, "bundle": item})
    creates = {op["ref"] for op in operations if op["action"] == "create"}
    for op in operations:
        if op["action"] != "attach":
            continue
        if op["target"].startswith("new:"):
            if op["target"] not in creates:
                raise ValueError("临时引用必须指向本批次一个 create，不能指向另一个 attach")
        elif survivor(master, op["target"]) != op["target"]:
            raise ValueError("请直接关联存续 ID")
    return {"formatVersion": VERSION, "kind": "admit", "baseStateHash": exchange.state_hash(master),
            "intakeStateHash": snapshot(staging), "decisions": decisions, "items": items, "operations": operations}


def propose(db, staging_db, review_file, output):
    review = json.loads(Path(review_file).read_text(encoding="utf-8-sig"))
    if review.get("formatVersion") != VERSION or review.get("kind") != "admission-review":
        raise ValueError("不是本工具的审阅文件")
    with closing(open_db(db)) as master, closing(open_db(staging_db)) as staging:
        exchange.check_integrity(master)
        if exchange.state_hash(master) != review["baseStateHash"] or snapshot(staging) != review["intakeStateHash"]:
            raise ValueError("母库或 staging 已变化，请重新生成计划")
        decisions = []
        for item in review["items"]:
            current = bundle(staging, item["candidateId"])
            if item["normalized"] != current["normalized"]:
                raise ValueError("审阅文件的候选内容被修改；只编辑 decision，内容修订另走 Excel")
            decisions.append({"candidateId": item["candidateId"], **item["decision"]})
        payload = seal(admission_payload(master, staging, decisions))
        write_json(output, payload)
        return {"ok": True, "proposalId": payload["proposalId"], "actions": {action: sum(x["action"] == action for x in decisions) for action in ("create", "attach", "derive", "reuse", "defer")}, "hazardOperations": len(payload["operations"])}


def execute_schema(conn):
    conn.execute("PRAGMA defer_foreign_keys=ON")
    statement = ""
    for line in (ROOT / "source/schemas/admission.sql").read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""


def new_id(conn, table, prefix):
    for _ in range(10):
        ident = prefix + "_" + uuid.uuid4().hex[:26].upper()
        if conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (ident,)).fetchone() is None:
            return ident
    raise ValueError("无法分配唯一 ID")


def insert_record(conn, table, row):
    fields = list(row)
    conn.execute(f'INSERT INTO {table} ({",".join(fields)}) VALUES({",".join("?" for _ in fields)})', [row[f] for f in fields])


def keep_record(conn, table, row, keys):
    """Idempotency must not conceal a conflicting stored interpretation."""
    old = conn.execute(f'SELECT * FROM {table} WHERE ' + " AND ".join(f"{k}=?" for k in keys), [row[k] for k in keys]).fetchone()
    if old is None:
        insert_record(conn, table, row)
    elif any(old[k] != value for k, value in row.items()):
        raise ValueError(f"已有 {table} 记录与导入内容冲突")


def materialize_source(conn, origin, db, archive, stamp, source_cache):
    src = origin["source"]
    sid = src["id"]
    if sid not in source_cache:
        blob = Path(src["archive_path"]).read_bytes()
        if digest(blob) != src["sha256"] or len(blob) != src["byte_size"]:
            raise ValueError("staging 原件归档校验失败")
        existing = conn.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
        if existing:
            stored = (Path(db).parent / existing["storage_ref"]).resolve()
            if existing["sha256"] != src["sha256"] or existing["byte_size"] != len(blob) or not stored.is_file() or digest(stored.read_bytes()) != src["sha256"]:
                raise ValueError("母库已有来源或归档冲突")
        else:
            target = Path(archive).resolve() / src["sha256"] / "original"
            if target.exists():
                if digest(target.read_bytes()) != src["sha256"]:
                    raise ValueError("母库归档校验失败")
            else:
                exchange.install_output(target, blob)
            name = source_name(origin["locations"][0])
            insert_record(conn, "sources", {"id": sid, "sha256": src["sha256"], "original_name": name,
                "media_type": mimetypes.guess_type(name)[0] or "application/octet-stream", "byte_size": len(blob),
                "visibility": "private", "storage_ref": Path(os.path.relpath(target, Path(db).resolve().parent)).as_posix(),
                "source_commit": "", "created_at": stamp})
        source_cache.add(sid)
    for location in origin["locations"]:
        conn.execute("INSERT OR IGNORE INTO intake_source_locations VALUES(?,?)", (sid, location))
        # Restore paths are relative and content-addressed; source paths stay private.
        rel = f"source/imports/{src['sha256']}/{source_name(location)}"
        conn.execute("INSERT OR IGNORE INTO source_locations VALUES(?,?)", (sid, rel))
    keep_record(conn, "intake_runs", origin["run"], ("id",))
    raw = origin["row"]
    keep_record(conn, "source_rows", {"id": raw["id"], "source_id": sid, "sheet": raw["sheet"],
        "row_number": raw["row_number"], "json_pointer": pointer("@intake", raw["sheet"], raw["row_number"]),
        "raw_payload": raw["raw_json"]}, ("id",))
    keep_record(conn, "intake_parsed_rows", {"run_id": origin["run"]["id"], "source_row_id": raw["id"],
        "raw_json": origin["parsedRaw"]}, ("run_id", "source_row_id"))


def add_provenance(conn, candidate, target, origin, action_id):
    row_id, run_id = origin["row"]["id"], origin["run"]["id"]
    ident = "IP_" + digest(dumps([target, candidate, row_id, run_id]))
    conn.execute("INSERT OR IGNORE INTO intake_provenance VALUES(?,?,?,?,?,?,?,?)",
                 (ident, "hazard", target, row_id, "/", run_id, candidate, action_id))


def admit_items(conn, payload, db, archive, action_id):
    stamp, source_cache = now(), set()
    ids, changes = {}, []
    for op in payload["operations"]:
        if op["action"] != "create":
            continue
        norm = op["content"]
        ident = new_id(conn, "hazards", "H")
        record = {field: norm.get(field, "") for field in ("title", "description", "measures", "category", "conditions", "note", "mode")}
        record.update(id=ident, status="待整理", checked="", revision=1, merged_into=None, legacy_payload="{}")
        insert_record(conn, "hazards", record)
        if norm.get("place"):
            conn.execute("INSERT INTO hazard_tags VALUES(?,?,?,?)", (ident, "place", norm["place"], 0))
        ids[op["ref"]] = ident
        changes.append({"entityType": "hazard", "id": ident, "before": None, "after": record})
    decisions = []
    for item in payload["items"]:
        if item["action"] == "defer":
            decisions.append({"candidateId": item["candidateId"], "action": "defer"})
            continue
        candidate = item["candidateId"]
        data = item["bundle"]
        keep_record(conn, "intake_candidates", {"id": candidate, "fingerprint": data["fingerprint"], "normalized_json": intake.dumps(data["normalized"])}, ("id",))
        for origin in data["origins"]:
            materialize_source(conn, origin, db, archive, stamp, source_cache)
        targets = []
        for op in (o for o in payload["operations"] if o["candidateId"] == candidate):
            target = ids[op["ref"]] if op["action"] == "create" else ids.get(op["target"], op["target"])
            targets.append(target)
            conn.execute("INSERT OR IGNORE INTO candidate_admissions VALUES(?,?,?)", (candidate, target, action_id))
            for origin in data["origins"]:
                add_provenance(conn, candidate, target, origin, action_id)
            if "derivation" in op:
                derived = op["derivation"]
                conn.execute("INSERT INTO intake_derivations VALUES(?,?,?,?,?,?,?,?,?,?)", ("DERV_" + digest(dumps([candidate, op["ref"]])),
                             candidate, target, "rule_template", derived["sourceResult"], derived["basis"], derived["quote"], dumps(op["content"]), op["reason"], action_id))
        result = {"candidateId": candidate, "action": item["action"], "hazardIds": targets, "sourceRows": len(data["origins"])}
        if len(targets) == 1:
            result["hazardId"] = targets[0]
        decisions.append(result)
    return {"idMap": ids, "decisions": decisions, "entityChanges": changes}


def merge_payload(conn, source, target, reason):
    if source == target or not isinstance(reason, str) or not reason.strip():
        raise ValueError("合并必须指定不同的来源/目标，并说明理由")
    if survivor(conn, source) != source or survivor(conn, target) != target:
        raise ValueError("只能合并两个未关闭的存续隐患")
    original, retained = hazard(conn, source), hazard(conn, target)
    links_from = [dict(r) for r in conn.execute("SELECT * FROM links WHERE hazard_id=? ORDER BY id", (source,))]
    links_to = [dict(r) for r in conn.execute("SELECT * FROM links WHERE hazard_id=? ORDER BY id", (target,))]
    by_clause = {r["clause_id"]: r for r in links_to}
    conflicts = [{"sourceLinkId": r["id"], "targetLinkId": by_clause[r["clause_id"]]["id"],
                  "differentFields": [field for field in ("role", "priority", "applicability", "jurisdiction_code", "status") if r[field] != by_clause[r["clause_id"]][field]]}
                 for r in links_from if r["clause_id"] in by_clause and r["status"] != "已失效"]
    return {"formatVersion": VERSION, "kind": "merge", "baseStateHash": exchange.state_hash(conn),
            "sourceId": source, "targetId": target, "reason": reason,
            "source": original, "target": retained, "sourceLinks": links_from, "targetLinks": links_to,
            "linkConflicts": [c for c in conflicts if c["differentFields"]],
            "effect": "保留两条原记录及旧关联；来源标记 merged，目标保留内容并退回待核验；迁入启用关联须重新核验。重复条款关系保留旧差异供复核。"}


def propose_merge(db, source, target, reason, output):
    with closing(open_db(db)) as conn:
        exchange.check_integrity(conn)
        result = seal(merge_payload(conn, source, target, reason))
        write_json(output, result)
        return {"ok": True, "proposalId": result["proposalId"], "sourceId": source, "targetId": target,
                "sourceLinkCount": len(result["sourceLinks"])}


def merge_hazards(conn, payload, action_id):
    source, target = payload["sourceId"], payload["targetId"]
    changes = []
    for before, status, merged_into in ((payload["source"], "merged", target), (payload["target"], "待核验", None)):
        after = {**before, "status": status, "merged_into": merged_into, "checked": "", "revision": before["revision"] + 1}
        conn.execute("UPDATE hazards SET status=?,merged_into=?,checked='',revision=? WHERE id=?",
                     (status, merged_into, after["revision"], before["id"]))
        changes.append({"entityType": "hazard", "id": before["id"], "before": before, "after": after})
    active = {r["clause_id"]: r for r in payload["targetLinks"]}
    affected = {r["id"]: r for r in payload["targetLinks"] if r["status"] != "已失效"}
    for row in payload["sourceLinks"]:
        if row["status"] == "已失效":
            continue
        if row["clause_id"] in active:
            affected[active[row["clause_id"]]["id"]] = active[row["clause_id"]]
        else:
            after = {**row, "id": new_id(conn, "links", "K"), "hazard_id": target, "status": "待核验", "revision": 1, "legacy_payload": "{}"}
            insert_record(conn, "links", after)
            changes.append({"entityType": "link", "id": after["id"], "before": None, "after": after})
    for before in affected.values():
        # Even a previously disabled target link is reopened only as pending when
        # an active source link requires that same clause; no passed state is copied.
        after = {**before, "status": "待核验", "revision": before["revision"] + 1}
        conn.execute("UPDATE links SET status='待核验',revision=? WHERE id=?", (after["revision"], before["id"]))
        changes.append({"entityType": "link", "id": before["id"], "before": before, "after": after})
    existing_tags = {(r["kind"], r["value"]) for r in conn.execute("SELECT * FROM hazard_tags WHERE hazard_id=?", (target,))}
    for tag in conn.execute("SELECT * FROM hazard_tags WHERE hazard_id=? ORDER BY kind,ordinal", (source,)).fetchall():
        key = (tag["kind"], tag["value"])
        if key not in existing_tags:
            ordinal = conn.execute("SELECT COALESCE(MAX(ordinal),-1)+1 FROM hazard_tags WHERE hazard_id=? AND kind=?", (target, tag["kind"])).fetchone()[0]
            conn.execute("INSERT INTO hazard_tags VALUES(?,?,?,?)", (target, tag["kind"], tag["value"], ordinal))
            existing_tags.add(key)
    for row in conn.execute("SELECT * FROM provenance WHERE entity_type='hazard' AND entity_id=?", (source,)).fetchall():
        ident = "P_" + digest(dumps(["merge", target, row["source_row_id"], row["field_path"]]))
        conn.execute("INSERT OR IGNORE INTO provenance VALUES(?,?,?,?,?,?)", (ident, "hazard", target, row["source_row_id"], row["field_path"], row["transform_run_id"]))
    for row in conn.execute("SELECT * FROM intake_provenance WHERE entity_id=?", (source,)).fetchall():
        add_provenance(conn, row["candidate_id"], target, {"row": {"id": row["source_row_id"]}, "run": {"id": row["transform_run_id"]}}, action_id)
    conn.execute("INSERT INTO merge_decisions VALUES(?,?,?,?,?,?)", (action_id, source, target, payload["reason"], payload["source"]["revision"], payload["target"]["revision"]))
    return {"sourceId": source, "targetId": target, "entityChanges": changes}


def apply(db, proposal_file, actor, *, staging_db=None, archive=None):
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("actor 不能为空")
    proposal = json.loads(Path(proposal_file).read_text(encoding="utf-8-sig"))
    payload = unseal(proposal)
    action_id = proposal["proposalId"]
    with closing(open_db(db, write=True)) as conn:
        try:
            if exchange.has_table(conn, "master_actions"):
                old = conn.execute("SELECT * FROM master_actions WHERE id=?", (action_id,)).fetchone()
                if old:
                    if old["proposal_hash"] != proposal["proposalHash"]:
                        raise ValueError("提案 ID 冲突")
                    return {**json.loads(old["result_json"]), "status": "already_applied"}
            exchange.check_integrity(conn)
            if exchange.state_hash(conn) != payload["baseStateHash"]:
                raise ValueError("母库已变化，拒绝过期提案")
            if payload["kind"] == "admit":
                if staging_db is None:
                    raise ValueError("入库提交必须提供 staging 数据库")
                with closing(open_db(staging_db)) as staging:
                    rebuilt = admission_payload(conn, staging, payload["decisions"])
                if dumps(rebuilt) != dumps(payload):
                    raise ValueError("staging 或提案内容不匹配，拒绝提交")
                if not payload["items"]:
                    return {"ok": True, "status": "no_changes", "proposalId": action_id}
                execute_schema(conn)
                result = admit_items(conn, payload, db, archive or Path(db).resolve().parent / "archive", action_id)
            elif payload["kind"] == "merge":
                rebuilt = merge_payload(conn, payload["sourceId"], payload["targetId"], payload["reason"])
                if dumps(rebuilt) != dumps(payload):
                    raise ValueError("合并提案不符合母库当前内容或规则")
                execute_schema(conn)
                result = merge_hazards(conn, payload, action_id)
            else:
                raise ValueError("未知提案类型")
            result.update(ok=True, status="applied", proposalId=action_id, actor=actor.strip(), appliedAt=now())
            result_hash = exchange.state_hash(conn)
            conn.execute("INSERT INTO master_actions VALUES(?,?,?,?,?,?,?,?,?)", (action_id, payload["kind"], proposal["proposalHash"],
                payload["baseStateHash"], result_hash, actor.strip(), result["appliedAt"], dumps(proposal), dumps(result)))
            exchange.check_integrity(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "source/master/safety.sqlite3")
    parser.add_argument("--staging", type=Path, default=ROOT / "source/staging/intake.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("plan")
    cmd.add_argument("--limit", type=int, default=20)
    cmd.add_argument("--candidate", action="append")
    cmd.add_argument("--output", type=Path, required=True)
    cmd = sub.add_parser("propose")
    cmd.add_argument("--review", type=Path, required=True)
    cmd.add_argument("--output", type=Path, required=True)
    cmd = sub.add_parser("merge")
    cmd.add_argument("--source", required=True)
    cmd.add_argument("--target", required=True)
    cmd.add_argument("--reason", required=True)
    cmd.add_argument("--output", type=Path, required=True)
    cmd = sub.add_parser("apply")
    cmd.add_argument("--proposal", type=Path, required=True)
    cmd.add_argument("--actor", required=True)
    cmd.add_argument("--archive", type=Path, default=ROOT / "source/archive")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            result = plan(args.db, args.staging, args.output, limit=args.limit, candidate_ids=args.candidate)
        elif args.command == "propose":
            result = propose(args.db, args.staging, args.review, args.output)
        elif args.command == "merge":
            result = propose_merge(args.db, args.source, args.target, args.reason, args.output)
        else:
            result = apply(args.db, args.proposal, args.actor, staging_db=args.staging, archive=args.archive)
        # Full before/after values remain in the immutable receipt, not a large CLI dump.
        print(json.dumps({k: v for k, v in result.items() if k != "entityChanges"}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
