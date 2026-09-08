"""Build and audit the SQLite safety master from the immutable legacy JSON.

The migration is deliberately one way and conservative: source bytes are archived,
every legacy object is retained with a JSON Pointer, and an existing master may only
be opened with the exact same content manifest.  A changed source requires a later
change-set workflow and can never overwrite this database.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "source/schemas/master.sql"
PARSER_VERSION = "master-migration-v1"


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def source_files(repo: Path) -> list[Path]:
    """The manifest covers all content and derived JSON, while entities come from content."""
    files = sorted(x for x in (repo / "content").rglob("*") if x.is_file())
    files += sorted(x for x in (repo / "data").rglob("*") if x.is_file()) if (repo / "data").exists() else []
    required = {"content/hazards.json", "content/laws.json", "content/clauses.json", "content/links.json"}
    found = {x.relative_to(repo).as_posix() for x in files}
    missing = sorted(required - found)
    if missing:
        raise ValueError("missing required legacy files: " + ", ".join(missing))
    return files


def file_manifest(repo: Path, files: list[Path], blobs: dict[Path, bytes] | None = None) -> tuple[list[dict[str, Any]], str]:
    rows = []
    for path in files:
        blob = blobs[path] if blobs is not None else path.read_bytes()
        rows.append({"path": path.relative_to(repo).as_posix(), "sha256": digest(blob), "bytes": len(blob)})
    return rows, digest(dumps(rows))


def source_commit(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def archived_path(db_path: Path, storage_ref: str) -> Path:
    ref = Path(storage_ref)
    return ref if ref.is_absolute() else (db_path.parent / ref).resolve()


def archive_one(path: Path, repo: Path, archive: Path, blob: bytes | None = None) -> tuple[str, Path]:
    blob = path.read_bytes() if blob is None else blob
    sha = digest(blob)
    target = archive / sha / "original"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest(target.read_bytes()) != sha:
            raise ValueError(f"archive checksum mismatch: {target}")
    else:
        # xb prevents a concurrent migration from silently replacing evidence.
        with target.open("xb") as stream:
            stream.write(blob)
    return sha, target


def pointer(*parts: str | int) -> str:
    out = ""
    for part in parts:
        value = str(part).replace("~", "~0").replace("/", "~1")
        out += "/" + value
    return out or "/"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_json_blob(blob: bytes) -> Any:
    return json.loads(blob.decode("utf-8-sig"))


def canonical_entities(repo: Path, blobs: dict[Path, bytes] | None = None) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Read base tables plus every batch and reject duplicate/conflicting source IDs."""
    entities = {kind: [] for kind in ("hazards", "laws", "clauses", "links")}
    records = []
    base = {k: repo / "content" / f"{k}.json" for k in entities}
    paths = [(p, None) for p in base.values()]
    for p in sorted((repo / "content/batches").glob("*.json")):
        batch_doc = load_json_blob(blobs[p]) if blobs is not None else load_json(p)
        paths.append((p, (batch_doc.get("batchId") or "legacy:" + p.stem) if isinstance(batch_doc, dict) else "legacy:" + p.stem))
    seen: dict[str, set[str]] = {k: set() for k in entities}
    for path, batch_id in paths:
        doc = load_json_blob(blobs[path]) if blobs is not None else load_json(path)
        for kind in entities:
            values = (doc.get(kind, []) if isinstance(doc, dict) else (doc if path.name == f"{kind}.json" else []))
            if not isinstance(values, list):
                raise ValueError(f"{path}: {kind} must be an array")
            for index, raw in enumerate(values):
                if not isinstance(raw, dict):
                    raise ValueError(f"{path}:{kind}{index}: entity must be an object")
                if kind == "links":
                    ident = f"{raw.get('hazardId')}|{raw.get('clauseId')}"
                else:
                    ident = str(raw.get("id", ""))
                if not ident or ident == "None":
                    raise ValueError(f"{path}:{kind}{index}: missing ID/reference")
                if ident in seen[kind]:
                    raise ValueError(f"duplicate {kind} identity {ident}; migration aborted")
                seen[kind].add(ident)
                item_pointer = pointer(kind, index) if isinstance(doc, dict) else pointer(index)
                item = {"raw": raw, "path": path, "pointer": item_pointer, "batch": batch_id}
                entities[kind].append(item)
                records.append(item)
    return entities, records


def identity_hash(entity_type: str, row: dict[str, Any]) -> str:
    return digest(dumps([entity_type, row]))


def known_payload(raw: dict[str, Any], keys: set[str]) -> str:
    return dumps({k: raw.get(k) for k in sorted(keys)})


def migrate(repo: Path = ROOT, db_path: Path | None = None, archive: Path | None = None) -> dict[str, Any]:
    repo, db_path = Path(repo).resolve(), Path(db_path or repo / "source/master/safety.sqlite3").resolve()
    archive = Path(archive or repo / "source/archive").resolve()
    files = source_files(repo)
    blobs = {p: p.read_bytes() for p in files}
    manifest, dataset_hash = file_manifest(repo, files, blobs)
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT dataset_hash FROM migration_runs ORDER BY rowid LIMIT 1").fetchone()
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"existing master is unreadable; refusing to modify: {exc}") from exc
        finally:
            conn.close()
        if row and row[0] == dataset_hash:
            report = verify(db_path, repo)
            if not report['ok']:
                raise ValueError('existing master failed reconciliation; refusing to modify: ' + '; '.join(report['errors']))
            return {"status": "already_migrated", "datasetHash": dataset_hash, "db": str(db_path)}
        raise ValueError("existing master contains different source content; refusing update; use a later change-set workflow")

    # Parse and validate before opening the final path. Archives are immutable and may
    # remain after an interrupted run; the master itself is only installed atomically.
    entities, records = canonical_entities(repo, blobs)
    all_files: dict[str, tuple[str, Path]] = {}
    for path in files:
        all_files[path.relative_to(repo).as_posix()] = archive_one(path, repo, archive, blobs[path])

    db_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="safety-master-", suffix=".sqlite3.tmp", dir=db_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    run_id = "M_" + dataset_hash
    stamp = now()
    commit = source_commit(repo)
    try:
        conn = connect(temp_path)
        with conn:
            conn.execute("INSERT INTO migration_runs VALUES(?,?,?,?,?)",
                         (run_id, dataset_hash, commit, stamp, dumps(manifest)))
            conn.executemany("INSERT INTO db_meta VALUES(?,?)", [("schemaVersion", "3"),
                             ("datasetHash", dataset_hash), ("sourceCommit", commit), ("parserVersion", PARSER_VERSION)])
            for path in files:
                rel = path.relative_to(repo).as_posix()
                sha, stored = all_files[rel]
                sid = "S_" + sha
                media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                conn.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?,?,?)",
                             (sid, sha, path.name, media_type, len(blobs[path]), "private", Path(os.path.relpath(stored, db_path.parent)).as_posix(), commit, stamp))
                conn.execute("INSERT OR IGNORE INTO source_locations VALUES(?,?)", (sid, rel))

            # Batch metadata is stored as the complete original document.
            for item in records:
                if item["batch"]:
                    rel = item["path"].relative_to(repo).as_posix()
                    sid = "S_" + all_files[rel][0]
                    if not conn.execute("SELECT 1 FROM batches WHERE id=?", (item["batch"],)).fetchone():
                        doc = load_json_blob(blobs[item["path"]])
                        conn.execute("INSERT INTO batches VALUES(?,?,?,?,?)", (item["batch"], sid, "/", dumps(doc), dumps(doc.get("ingestionSummary"))))

            # Every entity gets an independent raw payload row and a source row.
            for kind, values in entities.items():
                for item in values:
                    raw, path, ptr, batch_id = item["raw"], item["path"], item["pointer"], item["batch"]
                    rel = path.relative_to(repo).as_posix(); sid = "S_" + all_files[rel][0]
                    etype = {"hazards":"hazard", "laws":"law_version", "clauses":"clause", "links":"link"}[kind]
                    eid = (raw.get("id") if kind != "links" else "K_" + digest(dumps([raw.get("hazardId"), raw.get("clauseId"), raw.get("role", ""), raw.get("priority", 0)]))[:26])
                    payload_id = "P_" + digest(dumps([sid, ptr]))
                    payload = dumps(raw)
                    conn.execute("INSERT INTO source_rows VALUES(?,?,?,?,?,?)", (payload_id, sid, kind, int(ptr.rsplit('/',1)[-1]) + 1, ptr, payload))
                    conn.execute("INSERT INTO legacy_payloads VALUES(?,?,?,?,?,?,?,?)",
                                 (payload_id, etype, str(eid), sid, ptr, payload, digest(payload), batch_id))
                    conn.execute("INSERT INTO provenance VALUES(?,?,?,?,?,?)",
                                 ("P_" + digest(dumps([etype, eid, payload_id])), etype, str(eid), payload_id, "/", run_id))

            # Normalized entities keep every known field and put all other keys in the raw payload.
            for item in entities["hazards"]:
                r=item["raw"]; conn.execute("INSERT INTO hazards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r["id"], r.get("title", ""), r.get("description", ""), r.get("measures", ""), r.get("category", ""), r.get("conditions", ""), r.get("note", ""), r.get("mode", ""), r.get("status", ""), r.get("checked", ""), 1, r.get("mergedInto"), dumps(r)))
                for field in ("aliases", "places", "keywords"):
                    for ordinal, value in enumerate(r.get(field, []) or []):
                        conn.execute("INSERT INTO hazard_tags VALUES(?,?,?,?)", (r["id"], field[:-1] if field.endswith('s') else field, str(value), ordinal))
            for item in entities["laws"]:
                r=item["raw"]; lid="LF_" + r["id"]
                conn.execute("INSERT INTO laws VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (lid, r.get("name", ""), "", r.get("scope", ""), r.get("level", ""), "legacy:"+r["id"], "provisional", r.get("status", ""), r.get("checked", ""), 1, dumps(r)))
                for ordinal, alias in enumerate(r.get("aliases", []) or []): conn.execute("INSERT INTO law_aliases VALUES(?,?,?)", (lid, str(alias), ordinal))
                conn.execute("INSERT INTO law_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r["id"], lid, r["id"], "", r.get("name", ""), r.get("level", ""), r.get("scope", ""), r.get("effectiveDate", ""), "", r.get("status", ""), "legacy_inherited", r.get("sourceUrl", ""), r.get("checked", ""), 1, dumps(r)))
            for item in entities["clauses"]:
                r=item["raw"]; conn.execute("INSERT INTO clauses VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (r["id"], r["lawId"], r.get("article", ""), r.get("quote", ""), r.get("sourceUrl", ""), r.get("status", ""), r.get("checked", ""), "legacy_unreviewed", 1, dumps(r)))
            # Preserve explicitly supplied replacement relationships.  They are
            # provenance facts, not an instruction to merge identities.
            for item in entities["laws"]:
                r=item["raw"]
                for target in r.get("replacedBy", []) or []:
                    if target in {x["raw"].get("id") for x in entities["laws"]}:
                        conn.execute("INSERT INTO law_successions VALUES(?,?,?,?,?,?)", (r["id"], target, "replaced_by", r.get("scope", ""), r.get("effectiveDate", ""), None))
                for target in r.get("replaces", []) or []:
                    if target in {x["raw"].get("id") for x in entities["laws"]}:
                        conn.execute("INSERT OR IGNORE INTO law_successions VALUES(?,?,?,?,?,?)", (target, r["id"], "replaces", r.get("scope", ""), r.get("effectiveDate", ""), None))
            for item in entities["links"]:
                r=item["raw"]; kid="K_" + digest(dumps([r.get("hazardId"),r.get("clauseId"),r.get("role", ""),r.get("priority", 0)]))[:26]
                conn.execute("INSERT INTO links VALUES(?,?,?,?,?,?,?,?,?,?)", (kid, r["hazardId"], r["clauseId"], r.get("role", ""), int(r.get("priority",0) or 0), r.get("applicability", ""), r.get("jurisdictionCode", ""), r.get("status", "待核验"), 1, dumps(r)))

            # Explicitly record article locator collisions without losing either clause.
            collisions = conn.execute("SELECT law_version_id,article_path,COUNT(*) FROM clauses GROUP BY law_version_id,article_path HAVING COUNT(*)>1").fetchall()
            for law_id, article, count in collisions:
                ids=[x[0] for x in conn.execute("SELECT id FROM clauses WHERE law_version_id=? AND article_path=? ORDER BY id",(law_id,article))]
                conn.execute("UPDATE clauses SET identity_status='unresolved' WHERE law_version_id=? AND article_path=?",(law_id,article))
                cid="MC_"+digest(dumps(["clause_locator",law_id,article]))
                conn.execute("INSERT INTO migration_conflicts VALUES(?,?,?,?,?)", (cid,"clause_locator",law_id+"|"+article,"unresolved",dumps({"lawVersionId":law_id,"articlePath":article,"clauseIds":ids})))

            # Legacy states are evidence only; no synthetic passed record is created.
            for kind, values in entities.items():
                etype={"hazards":"hazard","laws":"law_version","clauses":"clause","links":"link"}[kind]
                for item in values:
                    r=item["raw"]; eid=(r.get("id") if kind != "links" else "K_" + digest(dumps([r.get("hazardId"),r.get("clauseId"),r.get("role", ""),r.get("priority",0)]))[:26])
                    original = r.get("status","")
                    if original:
                        dep=identity_hash(etype,r)
                        conn.execute("INSERT INTO verification VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("V_"+digest(dumps([etype,eid,"legacy_status"])),etype,str(eid),1,dep,"legacy_status","legacy_inherited","","",r.get("checked", ""),"",None,"legacy status retained; no new verification evidence",None))
        conn.close()
        report = verify(temp_path, repo)
        if not report['ok']:
            raise ValueError('migration reconciliation failed: ' + '; '.join(report['errors']))
        # Same-directory hard link installs atomically and fails if another writer
        # created the destination. Unlike replace(), it can never overwrite a DB.
        os.link(temp_path, db_path)
        temp_path.unlink()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        if temp_path.exists(): temp_path.unlink()
        raise
    return {"status":"migrated","datasetHash":dataset_hash,"sourceCommit":commit,"db":str(db_path),"counts":{k:len(v) for k,v in entities.items()}}


def _expected(repo: Path) -> tuple[list[dict[str, Any]], str, dict[str, list[dict[str, Any]]]]:
    files=source_files(repo); blobs={p:p.read_bytes() for p in files}; manifest,h=file_manifest(repo,files,blobs); entities,_=canonical_entities(repo,blobs); return manifest,h,entities


def verify(db_path: Path, repo: Path = ROOT) -> dict[str, Any]:
    db_path, repo = Path(db_path).resolve(), Path(repo).resolve()
    conn=connect_readonly(db_path)
    errors=[]
    try:
        manifest, expected_hash, entities = _expected(repo)
        actual_hash=conn.execute("SELECT value FROM db_meta WHERE key='datasetHash'").fetchone()
        if not actual_hash or actual_hash[0] != expected_hash: errors.append("dataset manifest hash mismatch")
        # SQLite's own checks and FK checks are part of the public report.
        integrity=conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk=conn.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok": errors.append("sqlite integrity_check failed: "+integrity)
        if fk: errors.append(f"foreign_key_check found {len(fk)} violations")
        counts={t:conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("hazards","laws","law_versions","clauses","links","sources","batches","legacy_payloads","provenance","verification")}
        expected_counts={"hazards":len(entities["hazards"]),"laws":len(entities["laws"]),"law_versions":len(entities["laws"]),"clauses":len(entities["clauses"]),"links":len(entities["links"])}
        if any(counts[k] != v for k,v in expected_counts.items()): errors.append("normalized entity counts mismatch")
        id_sets={}
        for kind, vals in entities.items():
            if kind=="links": expected={"K_"+digest(dumps([x["raw"].get("hazardId"),x["raw"].get("clauseId"),x["raw"].get("role", ""),x["raw"].get("priority",0)]))[:26] for x in vals}; actual={x[0] for x in conn.execute("SELECT id FROM links")}
            elif kind=="laws": expected={x["raw"]["id"] for x in vals}; actual={x[0] for x in conn.execute("SELECT id FROM law_versions")}
            else: expected={x["raw"]["id"] for x in vals}; actual={x[0] for x in conn.execute(f"SELECT id FROM {kind}")}
            id_sets[kind]={"expected":len(expected),"actual":len(actual),"missing":sorted(expected-actual),"extra":sorted(actual-expected)}
            if expected != actual: errors.append(f"{kind} ID set mismatch")
        # Compare normalized semantic fields with the preserved raw payload, catching
        # a damaged column even when the backup JSON payload was left untouched.
        checks={"hazards": {"title":"title","description":"description","measures":"measures","category":"category","conditions":"conditions","note":"note","mode":"mode","status":"status","checked":"checked"},
                "laws":{"canonical_name":"name","jurisdiction_code":"scope","document_kind":"level","status":"status","checked":"checked"},
                "law_versions":{"official_name":"name","level":"level","scope":"scope","effective_date":"effectiveDate","validity_status":"status","source_url":"sourceUrl","checked":"checked"},
                "clauses":{"article_path":"article","quote":"quote","source_url":"sourceUrl","status":"status","checked":"checked"},
                "links":{"hazard_id":"hazardId","clause_id":"clauseId","role":"role","priority":"priority"}}
        semantic_mismatches=[]
        expected_rows = {}
        for kind, values in entities.items():
            table = 'law_versions' if kind == 'laws' else kind
            expected_rows[table] = {}
            for item in values:
                raw = item['raw']
                eid = raw.get('id') if kind != 'links' else 'K_' + digest(dumps([
                    raw.get('hazardId'), raw.get('clauseId'), raw.get('role', ''), raw.get('priority', 0)]))[:26]
                expected_rows[table][eid] = raw
        expected_rows['laws'] = {'LF_' + key: value for key, value in expected_rows['law_versions'].items()}
        for table, mapping in checks.items():
            for row in conn.execute(f"SELECT id,legacy_payload,{','.join(mapping)} FROM {table}"):
                raw=expected_rows[table].get(row[0])
                if raw is None:
                    semantic_mismatches.append({'table':table,'id':row[0],'field':'unexpected_id'})
                    continue
                if json.loads(row[1]) != raw:
                    semantic_mismatches.append({'table':table,'id':row[0],'field':'legacy_payload'})
                for index,(column,source_key) in enumerate(mapping.items(),2):
                    if row[index] != (raw.get(source_key, "") if raw.get(source_key) is not None else ""):
                        semantic_mismatches.append({"table":table,"id":row[0],"field":column})
        for item in entities["clauses"]:
            raw=item["raw"]; actual=conn.execute("SELECT law_version_id FROM clauses WHERE id=?",(raw["id"],)).fetchone()
            if not actual or actual[0] != raw.get("lawId", ""):
                semantic_mismatches.append({"table":"clauses","id":raw["id"],"field":"law_version_id"})
        for item in entities["laws"]:
            raw=item["raw"]; actual=conn.execute("SELECT law_id FROM law_versions WHERE id=?",(raw["id"],)).fetchone()
            if not actual or actual[0] != "LF_"+raw["id"]:
                semantic_mismatches.append({"table":"law_versions","id":raw["id"],"field":"law_id"})
        # Ordered tag/alias collections are formal data; compare their ordinals too.
        for item in entities["hazards"]:
            rid=item["raw"]["id"]
            actual=[]; expected=[]
            for field in ("aliases","places","keywords"):
                kind=field[:-1]
                actual.extend((kind,v) for v, in conn.execute("SELECT value FROM hazard_tags WHERE hazard_id=? AND kind=? ORDER BY ordinal",(rid,kind)))
                expected.extend((kind,str(value)) for value in item["raw"].get(field,[]) or [])
            if actual != expected: semantic_mismatches.append({"table":"hazard_tags","id":rid,"field":"ordered_values"})
        for item in entities["laws"]:
            rid="LF_"+item["raw"]["id"]
            actual=[x[0] for x in conn.execute("SELECT alias FROM law_aliases WHERE law_id=? ORDER BY ordinal",(rid,))]
            expected=[str(x) for x in item["raw"].get("aliases",[]) or []]
            if actual != expected: semantic_mismatches.append({"table":"law_aliases","id":rid,"field":"ordered_values"})
        if semantic_mismatches: errors.append(f"semantic field mismatch ({len(semantic_mismatches)})")
        # Verify every archive and every raw entity pointer against the current source bytes.
        file_checks=[]
        for row in conn.execute("SELECT s.sha256,s.storage_ref,sl.relative_path FROM sources s JOIN source_locations sl ON sl.source_id=s.id"):
            p=repo/row[2]; archived=archived_path(db_path,row[1]); ok=p.exists() and digest(p.read_bytes())==row[0] and archived.exists() and digest(archived.read_bytes())==row[0]
            file_checks.append({"path":row[2],"sha256":row[0],"ok":ok})
            if not ok: errors.append("source/archive mismatch: "+row[2])
        if {r['path'] for r in file_checks} != {r['path'] for r in manifest}:
            errors.append('source file coverage mismatch')
        raw_checks=[]
        def resolve(doc, ptr):
            if ptr == "/": return doc
            value=doc
            for token in ptr.lstrip("/").split("/"):
                token=token.replace("~1","/").replace("~0","~")
                value=value[int(token)] if isinstance(value,list) else value[token]
            return value
        for row in conn.execute("SELECT lp.entity_type,lp.entity_id,lp.payload_sha256,lp.raw_payload,lp.json_pointer,sl.relative_path FROM legacy_payloads lp JOIN source_locations sl ON sl.source_id=lp.source_id"):
            try:
                doc=load_json(repo/row[5]); source_value=dumps(resolve(doc,row[4])); pointer_ok=source_value==row[3]
            except (OSError,ValueError,KeyError,IndexError,TypeError,json.JSONDecodeError): pointer_ok=False
            ok=digest(row[3])==row[2] and pointer_ok
            raw_checks.append({"entityType":row[0],"entityId":row[1],"path":row[5],"jsonPointer":row[4],"ok":ok})
            if not ok: errors.append(f"raw payload/pointer mismatch: {row[0]} {row[1]}")
        expected_entity_count = sum(len(rows) for rows in entities.values())
        for table in ('legacy_payloads', 'source_rows', 'provenance'):
            if conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] != expected_entity_count:
                errors.append(table + ' coverage mismatch')
        entity_tables = {'hazard':'hazards','law':'laws','law_version':'law_versions','clause':'clauses','link':'links'}
        for entity_type, entity_id in conn.execute('SELECT entity_type,entity_id FROM provenance'):
            table = entity_tables.get(entity_type)
            if not table or not conn.execute('SELECT 1 FROM '+table+' WHERE id=?',(entity_id,)).fetchone():
                errors.append('provenance target missing: '+entity_type+'/'+entity_id)
        if conn.execute("SELECT COUNT(*) FROM verification WHERE result != 'legacy_inherited'").fetchone()[0]:
            errors.append('migration must not create new verification conclusions')
        statuses={}
        for t in ("hazards","laws","law_versions","clauses","links"):
            col="validity_status" if t=="law_versions" else "status"
            statuses[t]={str(k if k is not None else ""):v for k,v in conn.execute(f"SELECT {col},COUNT(*) FROM {t} GROUP BY {col}")}
        expected_successions=set()
        for item in entities["laws"]:
            raw=item["raw"]
            expected_successions.update((raw["id"], target) for target in raw.get("replacedBy",[]) or [])
            expected_successions.update((target, raw["id"]) for target in raw.get("replaces",[]) or [])
        actual_successions={(a,b) for a,b in conn.execute("SELECT old_version_id,new_version_id FROM law_successions")}
        succession_report={"expected":len(expected_successions),"actual":len(actual_successions),"missing":sorted(expected_successions-actual_successions),"extra":sorted(actual_successions-expected_successions)}
        if expected_successions != actual_successions: errors.append("law succession reconciliation mismatch")
        return {"ok":not errors,"errors":errors,"counts":counts,"expectedCounts":expected_counts,"idSets":id_sets,"statusDistribution":statuses,"integrityCheck":integrity,"foreignKeyViolations":fk,"fileReconciliation":file_checks,"entityReconciliation":raw_checks,"semanticMismatches":semantic_mismatches,"successionReconciliation":succession_report,"conflicts":[dict(zip(("id","type","key","status","details"),r)) for r in conn.execute("SELECT id,conflict_type,identity_key,status,details_json FROM migration_conflicts")],"datasetHash":expected_hash}
    finally: conn.close()


def restore(db_path: Path, output: Path) -> dict[str, Any]:
    """Restore every archived source file into a new, empty directory."""
    db_path, output = Path(db_path).resolve(), Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("restore destination must be empty; refusing to overwrite existing files")
    output.mkdir(parents=True, exist_ok=True)
    conn = connect_readonly(db_path)
    restored = []
    try:
        rows = conn.execute("SELECT s.storage_ref,sl.relative_path,s.sha256 FROM sources s JOIN source_locations sl ON sl.source_id=s.id ORDER BY sl.relative_path").fetchall()
        for storage, rel, sha in rows:
            src = archived_path(db_path, storage)
            if not src.exists() or digest(src.read_bytes()) != sha:
                raise ValueError("archived source checksum mismatch: " + rel)
            dest = output / Path(rel)
            try:
                dest.resolve().relative_to(output.resolve())
            except ValueError as exc:
                raise ValueError("unsafe restore path: " + rel) from exc
            if dest.exists():
                raise ValueError("restore would overwrite: " + rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            if digest(dest.read_bytes()) != sha:
                raise ValueError("restored source checksum mismatch: " + rel)
            restored.append({"path":rel,"sha256":sha})
    except Exception:
        # A partial restore is never presented as successful; callers can remove
        # the explicitly supplied destination and retry.
        raise
    finally: conn.close()
    return {"status":"restored","files":restored,"count":len(restored),"output":str(output)}


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest="command",required=True)
    m=sub.add_parser("migrate"); m.add_argument("--repo",type=Path,default=ROOT); m.add_argument("--db",type=Path); m.add_argument("--archive",type=Path)
    v=sub.add_parser("verify"); v.add_argument("--repo",type=Path,default=ROOT); v.add_argument("--db",type=Path,required=True)
    r=sub.add_parser("restore"); r.add_argument("--db",type=Path,required=True); r.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.command=="migrate": result=migrate(args.repo,args.db,args.archive)
        elif args.command=="verify": result=verify(args.db,args.repo)
        else: result=restore(args.db,args.output)
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
        return 0 if result.get("ok",True) else 1
    except Exception as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False,indent=2))
        return 1


if __name__=="__main__": raise SystemExit(main())
