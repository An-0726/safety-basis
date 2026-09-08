"""Evidence-backed review proposals. Agents draft; one transaction applies.

This records a reviewer's conclusions, never infers legal validity from a URL.
The official document snapshot and the exact reviewed revisions are mandatory.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sqlite3

import exchange
from master import ROOT, connect_readonly, dumps
import verification as v

FORMAT = "safety-review-v1"


def write_json(path, value):
    path = Path(path)
    exchange.check_output(path, ".json")
    exchange.install_output(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def schema(conn):
    statement = ""
    for line in (ROOT / "source/schemas/review.sql").read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""


def writable(db):
    conn = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def snapshot_text(blob):
    if blob.startswith(b"PK"):
        from io import BytesIO
        from zipfile import ZipFile
        from xml.etree import ElementTree
        with ZipFile(BytesIO(blob)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("当前 ZIP 文档证据仅支持 DOCX")
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        return "\n".join(node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
    if blob.startswith(b"%PDF"):
        from io import BytesIO
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(blob)).pages)
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = blob.decode("gb18030")
    parser = TextParser()
    parser.feed(text)
    return "\n".join(parser.parts)


def normalized_text(value):
    # Keep punctuation, negations, numbers, units and version identifiers.
    return re.sub(r"\s+", "", value)


def register_evidence(db, snapshot, url, retrieved_at, *, archive=None):
    db = Path(db).resolve()
    if not v.official_url(url):
        raise ValueError("当前证据登记仅接受政府官方 http(s) URL")
    if v.timestamp(retrieved_at) > dt.datetime.now(dt.timezone.utc):
        raise ValueError("证据获取时间不能在未来")
    blob = Path(snapshot).read_bytes()
    if not blob or not snapshot_text(blob).strip():
        raise ValueError("原件为空或无法提取文本；扫描件需先提供经核对的文本适配器")
    sha = exchange.sha256_bytes(blob)
    ident = "E_" + v.digest([url, sha, retrieved_at])
    destination = (Path(archive) if archive else db.parent.parent / "archive") / "evidence" / sha / "original"
    with closing(writable(db)) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            schema(conn)
            exchange.check_integrity(conn)
            if destination.exists():
                if exchange.sha256_bytes(destination.read_bytes()) != sha:
                    raise ValueError("既有证据归档损坏，拒绝覆盖")
            else:
                exchange.install_output(destination, blob)
            existing = conn.execute("SELECT * FROM evidence WHERE id=?", (ident,)).fetchone()
            if existing:
                old_path = db.parent / existing["snapshot_ref"]
                if not old_path.is_file() or exchange.sha256_bytes(old_path.read_bytes()) != sha:
                    raise ValueError("原登记证据归档缺失或损坏")
            else:
                conn.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?)", (
                    ident, url, retrieved_at, os.path.relpath(destination.resolve(), db.parent).replace("\\", "/"), sha, "", "全文"))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"ok": True, "evidenceId": ident, "sha256": sha, "alreadyRegistered": bool(existing)}


def plan(db, targets, output):
    if not 1 <= len(targets) <= 100 or len(set(targets)) != len(targets):
        raise ValueError("每批需 1..100 个不重复目标")
    with closing(connect_readonly(Path(db).resolve())) as conn:
        conn.execute("BEGIN")
        exchange.check_integrity(conn)
        graph = v.graph_from_db(conn)
        v.validate_graph(graph)
        index = v.maps(graph)
        items = []
        for target in targets:
            kind, ident = target.split(":", 1)
            if kind not in v.TABLES or ident not in index[kind]:
                raise ValueError("核验目标不存在: " + target)
            items.append({"entityType": kind, "entityId": ident, "entityRevision": index[kind][ident]["revision"],
                          "dependencyHash": v.dependency_hash(graph, kind, ident), "material": v.material(graph, kind, ident),
                          "preparationErrors": v.preparation_errors(graph, kind, ident),
                          "decision": {"result": "pending", "evidenceId": "", "locator": "", "reason": "",
                                       "reviewDueAt": "", "publicFieldsReviewed": False}})
        document = {"formatVersion": FORMAT, "kind": "review-draft", "baseStateHash": exchange.state_hash(conn), "items": items}
        write_json(output, document)
    return {"ok": True, "reviewFile": str(output), "targetCount": len(items)}


def checked_items(conn, db, items, checked_at):
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("核验 items 数量无效")
    graph, seen = v.graph_from_db(conn), set()
    v.validate_graph(graph)
    index, documents = v.maps(graph), v.load_evidence(conn, db)
    checked = v.timestamp(checked_at)
    if checked > dt.datetime.now(dt.timezone.utc):
        raise ValueError("核验时间不能在未来")
    for item in items:
        if set(item) != {"entityType", "entityId", "entityRevision", "dependencyHash", "material", "preparationErrors", "decision"}:
            raise ValueError("核验项字段不完整或含未知字段")
        kind, ident = item["entityType"], item["entityId"]
        if kind not in index or ident not in index[kind] or (kind, ident) in seen:
            raise ValueError("核验目标不存在或重复")
        seen.add((kind, ident))
        row = index[kind][ident]
        if (type(item["entityRevision"]) is not int or row["revision"] != item["entityRevision"]
                or item["dependencyHash"] != v.dependency_hash(graph, kind, ident)
                or item["material"] != v.material(graph, kind, ident)):
            raise ValueError("核验内容或依赖已经改变")
        decision = item["decision"]
        if not isinstance(decision, dict) or set(decision) != {"result", "evidenceId", "locator", "reason", "reviewDueAt", "publicFieldsReviewed"}:
            raise ValueError("核验决定字段无效")
        if any(not isinstance(decision[f], str) for f in set(decision) - {"publicFieldsReviewed"}) or type(decision["publicFieldsReviewed"]) is not bool:
            raise ValueError("核验决定字段类型无效")
        if decision["result"] not in ("passed", "failed", "pending", "not_applicable") or not decision["reason"].strip():
            raise ValueError("必须填写核验结论及理由")
        if decision["reviewDueAt"] and v.date(decision["reviewDueAt"]) <= v.business_date(checked):
            raise ValueError("复核日期必须晚于核验日期")
        if decision["result"] != "passed":
            if decision["evidenceId"] and decision["evidenceId"] not in documents:
                raise ValueError("证据 ID 不存在")
            continue
        errors = v.preparation_errors(graph, kind, ident)
        if errors:
            raise ValueError(f"{kind}:{ident}: " + "; ".join(errors))
        if kind == "hazard" and not decision["publicFieldsReviewed"]:
            raise ValueError("隐患公开字段必须完成审阅")
        evidence = documents.get(decision["evidenceId"])
        if not evidence or not evidence["archive_ok"] or not v.official_url(evidence["official_url"]) or not decision["locator"].strip():
            raise ValueError("通过记录需要官方证据原件及精确定位")
        if v.timestamp(evidence["retrieved_at"]) > checked:
            raise ValueError("证据获取时间晚于核验时间")
        if kind == "clause":
            ref = conn.execute("SELECT snapshot_ref FROM evidence WHERE id=?", (evidence["id"],)).fetchone()[0]
            text = snapshot_text((Path(db).resolve().parent / ref).read_bytes())
            if normalized_text(row["quote"]) not in normalized_text(text):
                raise ValueError("条款原文未在证据原件中完整匹配；不能只改条号或标准号")
        if kind == "law":
            # Subsequent items must also see identities confirmed in this batch.
            # Review-only state is excluded from material/dependency hashes.
            row["identity_status"] = "confirmed"
    return graph


def propose(db, draft_file, output, reviewer, model=""):
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(model, str):
        raise ValueError("核验人不能为空，model 必须为文本")
    draft = json.loads(Path(draft_file).read_text(encoding="utf-8"))
    if set(draft) != {"formatVersion", "kind", "baseStateHash", "items"} or draft["formatVersion"] != FORMAT or draft["kind"] != "review-draft":
        raise ValueError("核验草稿格式无效")
    checked_at = exchange.utc_now()
    with closing(connect_readonly(Path(db).resolve())) as conn:
        conn.execute("BEGIN")
        if exchange.state_hash(conn) != draft["baseStateHash"]:
            raise ValueError("母库已变化，拒绝过期核验草稿")
        checked_items(conn, db, draft["items"], checked_at)
    payload = {**draft, "kind": "review-proposal", "reviewer": reviewer.strip(), "model": model, "checkedAt": checked_at}
    sha = v.digest(payload)
    sealed = {**payload, "proposalId": "VR_" + sha[:26], "proposalHash": sha}
    write_json(output, sealed)
    return {"ok": True, "proposalId": sealed["proposalId"], "proposal": str(output), "targetCount": len(payload["items"])}


def apply(db, proposal_file, actor):
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("actor 不能为空")
    proposal = json.loads(Path(proposal_file).read_text(encoding="utf-8"))
    payload = {k: val for k, val in proposal.items() if k not in ("proposalId", "proposalHash")}
    if (set(payload) != {"formatVersion", "kind", "baseStateHash", "items", "reviewer", "model", "checkedAt"}
            or payload["formatVersion"] != FORMAT or payload["kind"] != "review-proposal"
            or not isinstance(payload["reviewer"], str) or not payload["reviewer"].strip() or not isinstance(payload["model"], str)
            or proposal.get("proposalHash") != v.digest(payload) or proposal.get("proposalId") != "VR_" + v.digest(payload)[:26]):
        raise ValueError("核验提案格式或哈希无效")
    with closing(writable(db)) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            schema(conn)
            existing = conn.execute("SELECT result_json FROM review_actions WHERE id=?", (proposal["proposalId"],)).fetchone()
            if existing:
                conn.rollback()
                return {**json.loads(existing[0]), "status": "already_applied"}
            exchange.check_integrity(conn)
            if exchange.state_hash(conn) != payload["baseStateHash"]:
                raise ValueError("母库已变化，拒绝提交过期核验提案")
            checked_items(conn, db, payload["items"], payload["checkedAt"])
            previous = v.load_proofs(conn)
            result = {"ok": True, "status": "applied", "proposalId": proposal["proposalId"], "reviews": []}
            # Defer only the audit FK while writing its immutable details.
            conn.execute("PRAGMA defer_foreign_keys=ON")
            for ordinal, item in enumerate(payload["items"]):
                kind, ident, decision = item["entityType"], item["entityId"], item["decision"]
                review_id = proposal["proposalId"] + "_" + str(ordinal)
                prior = previous.get((kind, ident), {})
                conn.execute("INSERT INTO verification VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    review_id, kind, ident, item["entityRevision"], item["dependencyHash"], v.CHECKS[kind], decision["result"],
                    payload["reviewer"], payload["model"], payload["checkedAt"], decision["reviewDueAt"], decision["evidenceId"] or None,
                    decision["reason"], prior.get("id")))
                conn.execute("INSERT INTO verification_details VALUES(?,?,?,?)", (
                    review_id, decision["locator"], int(decision["publicFieldsReviewed"]), proposal["proposalId"]))
                table = v.TABLES[kind]
                column = "review_status" if kind == "law_version" else "status"
                current = conn.execute(f"SELECT {column} FROM {table} WHERE id=?", (ident,)).fetchone()[0]
                if current not in ("已失效", "merged", "rejected"):
                    status = "已核验" if decision["result"] == "passed" else "待核验"
                    conn.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (status, ident))
                    if kind != "link":
                        conn.execute(f"UPDATE {table} SET checked=? WHERE id=?", (v.business_date(payload["checkedAt"]).isoformat() if status == "已核验" else "", ident))
                    if decision["result"] == "passed" and kind in ("law", "clause"):
                        conn.execute(f"UPDATE {table} SET identity_status=? WHERE id=?", ("confirmed" if kind == "law" else "confirmed_locator", ident))
                result["reviews"].append({"id": review_id, "entityType": kind, "entityId": ident, "result": decision["result"]})
            result["resultStateHash"] = exchange.state_hash(conn)
            conn.execute("INSERT INTO review_actions VALUES(?,?,?,?,?,?,?,?)", (
                proposal["proposalId"], proposal["proposalHash"], payload["baseStateHash"], result["resultStateHash"],
                actor.strip(), exchange.utc_now(), dumps(proposal), dumps(result)))
            exchange.check_integrity(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "source/master/safety.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    evidence = sub.add_parser("evidence")
    evidence.add_argument("--snapshot", type=Path, required=True)
    evidence.add_argument("--url", required=True)
    evidence.add_argument("--retrieved-at", required=True)
    draft = sub.add_parser("plan")
    draft.add_argument("--targets", nargs="+", required=True)
    draft.add_argument("--output", type=Path, required=True)
    proposal = sub.add_parser("propose")
    proposal.add_argument("--review", type=Path, required=True)
    proposal.add_argument("--output", type=Path, required=True)
    proposal.add_argument("--reviewer", required=True)
    proposal.add_argument("--model", default="")
    commit = sub.add_parser("apply")
    commit.add_argument("--proposal", type=Path, required=True)
    commit.add_argument("--actor", required=True)
    args = parser.parse_args()
    try:
        if args.command == "evidence":
            result = register_evidence(args.db, args.snapshot, args.url, args.retrieved_at)
        elif args.command == "plan":
            result = plan(args.db, args.targets, args.output)
        elif args.command == "propose":
            result = propose(args.db, args.review, args.output, args.reviewer, args.model)
        else:
            result = apply(args.db, args.proposal, args.actor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
