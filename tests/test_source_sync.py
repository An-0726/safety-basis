from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import intake
import source_sync


class SourceSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db, self.stage, self.archive = self.root / "master.sqlite3", self.root / "intake.sqlite3", self.root / "master-archive"
        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript((REPO / "source/schemas/master.sql").read_text(encoding="utf-8"))
        mapping = {"fields": {"title": ["title"]}, "required": ["title"], "version": 1}
        for i in (1, 2):
            file = self.root / f"source{i}.csv"
            file.write_text(f"title\n原始要求{i}\n", encoding="utf-8")
            with closing(intake.connect(self.stage)) as conn:
                intake.ingest(conn, file, mapping, self.root / "raw")

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_ledger_is_idempotent_without_creating_hazards(self):
        first = source_sync.sync(self.db, self.stage, self.archive)
        self.assertEqual((first["sourceFiles"], first["parsedRows"], first["knowledgeCreated"]), (2, 2, 0))
        self.assertEqual(source_sync.sync(self.db, self.stage, self.archive)["status"], "already_synced")
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM source_rows").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM hazards").fetchone()[0], 0)
            ref = conn.execute("SELECT storage_ref FROM sources LIMIT 1").fetchone()[0]
        (self.db.parent / ref).write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "归档"):
            source_sync.sync(self.db, self.stage, self.archive)

    def test_corrupt_staging_archive_rolls_back_the_master(self):
        with closing(sqlite3.connect(self.stage)) as conn:
            path = conn.execute("SELECT archive_path FROM sources ORDER BY id DESC LIMIT 1").fetchone()[0]
        Path(path).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "归档"):
            source_sync.sync(self.db, self.stage, self.archive)
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
