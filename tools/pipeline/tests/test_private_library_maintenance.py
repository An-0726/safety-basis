"""Synthetic tests for the private full-text maintenance helper."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/v4"))
import private_library_maintenance as maintenance


class PrivateLibraryMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "fulltext.sqlite3"
        self.backups = self.root / "backups"
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE fulltext_meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            INSERT INTO fulltext_meta(key,value) VALUES
              ('schemaVersion','1'), ('format','safety-fulltext-v1');
            CREATE TABLE documents (
              document_key TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              title TEXT NOT NULL,
              version TEXT NOT NULL,
              official_url TEXT NOT NULL,
              as_of TEXT NOT NULL,
              current_status TEXT NOT NULL,
              review_status TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              text_sha256 TEXT NOT NULL,
              paragraph_count INTEGER NOT NULL,
              archive_ref TEXT NOT NULL,
              imported_at TEXT NOT NULL,
              UNIQUE(document_id, version)
            );
            CREATE VIRTUAL TABLE fulltext_fts USING fts5(
              document_key UNINDEXED,
              paragraph_no UNINDEXED,
              title,
              version,
              content,
              tokenize='trigram'
            );
            """
        )
        key = "FIXTURE-LAW\x1f2026"
        conn.execute(
            "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                key, "FIXTURE-LAW", "Synthetic safety rule", "2026",
                "https://fixture.gov.cn/law", "2026-09-14", "现行有效", "待核验",
                "a" * 64, "b" * 64, 2, "archive/fixture/original",
                "2026-09-14T00:00:00Z",
            ),
        )
        conn.executemany(
            "INSERT INTO fulltext_fts(document_key,paragraph_no,title,version,content) VALUES(?,?,?,?,?)",
            [
                (key, 1, "Synthetic safety rule", "2026", "第一条 synthetic safety text"),
                (key, 2, "Synthetic safety rule", "2026", "第二条 another searchable paragraph"),
            ],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_reports_strong_content_invariants(self):
        result = maintenance.audit(self.db, include_file_sha=False)
        self.assertEqual(result["integrity"], ["ok"])
        self.assertEqual(result["documents"], 1)
        self.assertEqual(result["ftsRows"], 2)
        self.assertEqual(result["paragraphCountSum"], 2)
        self.assertEqual(result["perDocumentParagraphMismatches"], [])
        self.assertEqual(len(result["ftsContentSha256"]), 64)

    def test_rebuild_creates_backup_and_preserves_content(self):
        result = maintenance.rebuild_fts(self.db, self.backups)
        self.assertTrue(result["ok"])
        self.assertEqual(result["invariantErrors"], [])
        self.assertFalse(result["manualRestoreRequired"])
        self.assertTrue(Path(result["backup"]).is_file())
        self.assertEqual(result["before"]["documents"], result["after"]["documents"])
        self.assertEqual(result["before"]["ftsRows"], result["after"]["ftsRows"])
        self.assertEqual(
            result["before"]["ftsContentSha256"],
            result["after"]["ftsContentSha256"],
        )
        self.assertEqual(result["after"]["integrity"], ["ok"])

    def test_rejects_unrelated_sqlite_file(self):
        other = self.root / "other.sqlite3"
        conn = sqlite3.connect(other)
        conn.execute("CREATE TABLE something_else(id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(ValueError, "不是 safety fulltext 数据库"):
            maintenance.audit(other)


if __name__ == "__main__":
    unittest.main()
