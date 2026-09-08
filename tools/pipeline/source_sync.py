"""Archive every successfully parsed source row without creating knowledge.

The source ledger is separate from hazard admission. Law registers may be
ingested into their own staging file and copied here as private provenance.
"""
from contextlib import closing
import argparse
import json
from pathlib import Path

import admission
import exchange
import master


def sync(db, staging_db, archive):
    with closing(admission.open_db(staging_db)) as stage, closing(admission.open_db(db, write=True)) as conn:
        try:
            exchange.check_integrity(stage)
            exchange.check_integrity(conn)
            fingerprint = admission.snapshot(stage)
            exists = exchange.has_table(conn, "source_sync_actions")
            if exists:
                previous = conn.execute("SELECT result_json FROM source_sync_actions WHERE id=?", (fingerprint,)).fetchone()
                if previous:
                    # An old receipt does not excuse a missing or damaged archive.
                    for row in conn.execute("SELECT storage_ref,sha256 FROM sources"):
                        path = Path(db).resolve().parent / row["storage_ref"]
                        if not path.is_file() or exchange.sha256_bytes(path.read_bytes()) != row["sha256"]:
                            raise ValueError("母库来源归档缺失或损坏")
                    conn.rollback()
                    return {**json.loads(previous[0]), "status": "already_synced"}
            before = exchange.state_hash(conn)
            admission.execute_schema(conn)
            conn.execute("CREATE TABLE IF NOT EXISTS source_sync_actions(id TEXT PRIMARY KEY,base_state_hash TEXT NOT NULL,"
                         "result_state_hash TEXT NOT NULL,created_at TEXT NOT NULL,result_json TEXT NOT NULL)")
            conn.execute("CREATE TRIGGER IF NOT EXISTS source_sync_no_update BEFORE UPDATE ON source_sync_actions "
                         "BEGIN SELECT RAISE(ABORT,'source sync actions are append-only'); END")
            conn.execute("CREATE TRIGGER IF NOT EXISTS source_sync_no_delete BEFORE DELETE ON source_sync_actions "
                         "BEGIN SELECT RAISE(ABORT,'source sync actions are append-only'); END")
            stamp, cached, count = master.now(), set(), 0
            for item in stage.execute("SELECT p.run_id,p.source_row_id,p.raw_json FROM parsed_rows p "
                                      "JOIN import_runs i ON p.run_id=i.id WHERE i.status='complete' "
                                      "ORDER BY p.run_id,p.source_row_id"):
                row = dict(stage.execute("SELECT * FROM source_rows WHERE id=?", (item["source_row_id"],)).fetchone())
                run = dict(stage.execute("SELECT * FROM import_runs WHERE id=?", (item["run_id"],)).fetchone())
                source = dict(stage.execute("SELECT * FROM sources WHERE id=?", (run["source_id"],)).fetchone())
                if row["source_id"] != source["id"]:
                    raise ValueError("来源行与导入批次不一致")
                locations = [r[0] for r in stage.execute("SELECT original_path FROM source_locations WHERE source_id=? ORDER BY original_path",
                                                       (source["id"],))]
                admission.materialize_source(conn, {"source": source, "row": row, "run": run,
                    "parsedRaw": item["raw_json"], "locations": locations}, db, archive, stamp, cached)
                count += 1
            result = {"ok": True, "status": "synced", "stagingFingerprint": fingerprint,
                      "sourceFiles": len(cached), "parsedRows": count, "knowledgeCreated": 0}
            conn.execute("INSERT INTO source_sync_actions VALUES(?,?,?,?,?)",
                         (fingerprint, before, exchange.state_hash(conn), stamp, master.dumps(result)))
            exchange.check_integrity(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(sync(args.db, args.staging, args.archive), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
