import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import master  # noqa: E402


class MasterMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO / "content", self.root / "content")
        self.db = self.root / "source/master/safety.sqlite3"
        self.archive = self.root / "source/archive"

    def tearDown(self):
        self.tmp.cleanup()

    def run_migration(self):
        return master.migrate(self.root, self.db, self.archive)

    def test_full_migration_counts_conflicts_and_idempotence(self):
        result = self.run_migration()
        self.assertEqual(result["counts"], {"hazards": 81, "laws": 29, "clauses": 80, "links": 93})
        report = master.verify(self.db, self.root)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(len(report["conflicts"]), 2)
        self.assertEqual({x["key"] for x in report["conflicts"]}, {"L010|第9条", "L001|第二十一条"})
        before = self.db.read_bytes()
        repeated = self.run_migration()
        self.assertEqual(repeated["status"], "already_migrated")
        self.assertEqual(before, self.db.read_bytes())

    def test_semantic_column_damage_is_detected(self):
        self.run_migration()
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE hazards SET title='被篡改' WHERE id='H001'")
        conn.commit(); conn.close()
        report = master.verify(self.db, self.root)
        self.assertFalse(report["ok"])
        self.assertTrue(any(x["table"] == "hazards" and x["field"] == "title" for x in report["semanticMismatches"]))

    def test_changed_input_never_overwrites_existing_master(self):
        self.run_migration()
        before = self.db.read_bytes()
        path = self.root / 'content/hazards.json'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'refusing update'):
            self.run_migration()
        self.assertEqual(before, self.db.read_bytes())

    def test_corrupt_existing_master_is_not_reported_as_idempotent_success(self):
        self.run_migration()
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE hazards SET title='wrong' WHERE id='H001'")
        conn.close()
        before = self.db.read_bytes()
        with self.assertRaisesRegex(ValueError, 'failed reconciliation'):
            self.run_migration()
        self.assertEqual(before, self.db.read_bytes())

    def test_install_cannot_replace_a_concurrent_destination(self):
        install = master.os.link
        def race(source, destination):
            Path(destination).write_bytes(b'other writer')
            return install(source, destination)
        with patch.object(master.os, 'link', side_effect=race):
            with self.assertRaises(FileExistsError):
                self.run_migration()
        self.assertEqual(self.db.read_bytes(), b'other writer')

    def test_master_and_archive_backup_is_portable(self):
        self.run_migration()
        backup = self.root / 'portable'
        shutil.copytree(self.root / 'source', backup / 'source')
        result = master.restore(backup / 'source/master/safety.sqlite3', backup / 'restored')
        self.assertGreater(result['count'], 0)
        for path in self.root.joinpath('content').rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (backup/'restored'/path.relative_to(self.root)).read_bytes())

    def test_unknown_field_is_retained_in_legacy_payload(self):
        path = self.root / "content/hazards.json"
        values = json.loads(path.read_text(encoding="utf-8"))
        values[0]["futureField"] = {"keep": True}
        path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
        self.run_migration()
        conn = sqlite3.connect(self.db)
        raw = json.loads(conn.execute("SELECT legacy_payload FROM hazards WHERE id='H001'").fetchone()[0])
        conn.close()
        self.assertEqual(raw["futureField"], {"keep": True})

    def test_duplicate_id_and_broken_fk_leave_no_master(self):
        batch = self.root / "content/batches/2026-09-08-batch-003e.json"
        doc = json.loads(batch.read_text(encoding="utf-8"))
        doc["hazards"][0]["id"] = "H001"
        batch.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError): self.run_migration()
        self.assertFalse(self.db.exists())

        # Restore the fixture, then introduce an FK break. The schema transaction
        # must roll back the temporary database as a whole.
        shutil.rmtree(self.root / "content")
        shutil.copytree(REPO / "content", self.root / "content")
        links = self.root / "content/links.json"
        values = json.loads(links.read_text(encoding="utf-8"))
        values[0]["clauseId"] = "C_DOES_NOT_EXIST"
        links.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(sqlite3.IntegrityError): self.run_migration()
        self.assertFalse(self.db.exists())

    def test_restore_reproduces_archived_json(self):
        self.run_migration()
        output = self.root / "restored"
        result = master.restore(self.db, output)
        originals = [p for p in (self.root / "content").rglob("*") if p.is_file()]
        self.assertEqual(result["count"], len(originals))
        for original in originals:
            restored = output / "content" / original.relative_to(self.root / "content")
            self.assertEqual(original.read_bytes(), restored.read_bytes())


if __name__ == "__main__":
    unittest.main()
