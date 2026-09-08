import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools/pipeline"))
import master  # noqa: E402


class MasterAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Include both source tables and derived JSON because the migration
        # manifest intentionally covers both trees.
        shutil.copytree(REPO / "content", self.root / "content")
        shutil.copytree(REPO / "data", self.root / "data")
        self.db = self.root / "source/master/safety.sqlite3"
        self.archive = self.root / "source/archive"

    def tearDown(self):
        self.tmp.cleanup()

    def migrate(self):
        result = master.migrate(self.root, self.db, self.archive)
        self.assertEqual(result["status"], "migrated")

    def mutate_and_reject(self, statement, parameters=()):
        self.migrate()
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(statement, parameters)
            conn.commit()
        finally:
            conn.close()
        report = master.verify(self.db, self.root)
        self.assertFalse(report["ok"], report)

    def test_link_role_mutation_is_rejected(self):
        self.mutate_and_reject(
            "UPDATE links SET role='篡改依据角色' WHERE hazard_id='H001' AND clause_id='C012'"
        )

    def test_link_priority_mutation_is_rejected(self):
        self.mutate_and_reject(
            "UPDATE links SET priority=999 WHERE hazard_id='H001' AND clause_id='C012'"
        )

    def test_clause_law_version_mutation_is_rejected(self):
        self.mutate_and_reject(
            "UPDATE clauses SET law_version_id='L002' WHERE id='C001'"
        )

    def test_version_law_id_mutation_is_rejected(self):
        self.mutate_and_reject(
            "UPDATE law_versions SET law_id='LF_L002' WHERE id='L001'"
        )

    def test_tag_order_mutation_is_rejected(self):
        self.migrate()
        conn = sqlite3.connect(self.db)
        try:
            # Use a temporary ordinal so the two primary keys can be swapped.
            conn.execute(
                "UPDATE hazard_tags SET ordinal=999 "
                "WHERE hazard_id='H001' AND kind='place' AND ordinal=0"
            )
            conn.execute(
                "UPDATE hazard_tags SET ordinal=0 "
                "WHERE hazard_id='H001' AND kind='place' AND ordinal=1"
            )
            conn.execute(
                "UPDATE hazard_tags SET ordinal=1 "
                "WHERE hazard_id='H001' AND kind='place' AND ordinal=999"
            )
            conn.commit()
        finally:
            conn.close()
        report = master.verify(self.db, self.root)
        self.assertFalse(report["ok"], report)

    def test_deleting_law_succession_is_rejected(self):
        self.mutate_and_reject(
            "DELETE FROM law_successions WHERE old_version_id='L010' AND new_version_id='L011'"
        )

    def test_changing_title_and_matching_legacy_payload_is_rejected(self):
        self.migrate()
        conn = sqlite3.connect(self.db)
        try:
            raw = json.loads(
                conn.execute(
                    "SELECT legacy_payload FROM hazards WHERE id='H001'"
                ).fetchone()[0]
            )
            raw["title"] = "同时篡改标题"
            conn.execute(
                "UPDATE hazards SET title=?, legacy_payload=? WHERE id='H001'",
                (raw["title"], json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
            )
            conn.commit()
        finally:
            conn.close()
        report = master.verify(self.db, self.root)
        self.assertFalse(report["ok"], report)

    def test_restore_reproduces_every_source_file_byte_for_byte(self):
        self.migrate()
        output = self.root / "restored"
        result = master.restore(self.db, output)
        originals = [
            path
            for tree in (self.root / "content", self.root / "data")
            for path in sorted(tree.rglob("*"))
            if path.is_file()
        ]
        self.assertEqual(result["count"], len(originals))
        for original in originals:
            relative = original.relative_to(self.root)
            restored = output / relative
            self.assertTrue(restored.exists(), relative)
            self.assertEqual(original.read_bytes(), restored.read_bytes(), relative)

    def test_restore_rejects_parent_path_without_writing_outside_output(self):
        self.migrate()
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                "UPDATE source_locations SET relative_path='../escape.json' "
                "WHERE relative_path='content/hazards.json'"
            )
            conn.commit()
        finally:
            conn.close()

        output = self.root / "restored"
        escaped = self.root / "escape.json"
        try:
            with self.assertRaises(ValueError):
                master.restore(self.db, output)
            self.assertFalse(escaped.exists())
            self.assertFalse(any(output.rglob("*")) if output.exists() else False)
        finally:
            # Keep the temporary fixture clean even when this adversarial test
            # exposes an implementation that writes the escaped file.
            escaped.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
