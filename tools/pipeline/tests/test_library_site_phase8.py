import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "v4" / "library_site.py"
spec = importlib.util.spec_from_file_location("library_site_phase8", MODULE_PATH)
library_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library_site)


class LibrarySitePhase8Test(unittest.TestCase):
    def _make_db(self, root: Path):
        db = root / "fulltext.sqlite3"
        conn = sqlite3.connect(db)
        try:
            conn.execute("""
                CREATE TABLE documents(
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
                    imported_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE TABLE fulltext_fts(document_key TEXT, paragraph_no INTEGER, content TEXT)")
            conn.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("legacy\x1f2022", "legacy", "消防设施通用规范", "legacy", "https://example.test/official",
                 "2026-09-16", "现行有效", "已核验", "a" * 64, "b" * 64, 1,
                 "archive/" + "c" * 64 + "/original", "2026-09-16T00:00:00Z"),
            )
            conn.execute("INSERT INTO fulltext_fts VALUES (?,?,?)", ("legacy\x1f2022", 1, "消防设施应保持完好有效。"))
            conn.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("legacy-evidence\x1f2012", "legacy-evidence", "历史证据记录", "2012", "",
                 "2026-09-16", "历史", "待核验", "d" * 64, "e" * 64, 1,
                 "evidence/legacy.fulltext.pdf", "2026-09-16T00:00:00Z"),
            )
            conn.execute("INSERT INTO fulltext_fts VALUES (?,?,?)", ("legacy-evidence\x1f2012", 1, "历史证据文本。"))
            conn.commit()
        finally:
            conn.close()
        return db

    def test_alias_policy_is_display_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "document-aliases.json").write_text(json.dumps({
                "policy": {"formalAuthority": "knowledge", "databaseMutation": False, "archiveMutation": False},
                "groups": [{"canonicalVersionId": "L007", "title": "消防设施通用规范",
                            "memberDocumentKeys": ["legacy\x1f2022"]}],
            }, ensure_ascii=False), encoding="utf-8")
            mapping = library_site.load_alias_map(str(root))
            self.assertEqual(mapping["legacy\x1f2022"]["canonicalVersionId"], "L007")

            payload = json.loads((root / "document-aliases.json").read_text(encoding="utf-8"))
            payload["policy"]["databaseMutation"] = True
            (root / "document-aliases.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "不得授权"):
                library_site.load_alias_map(str(root))

    def test_local_site_uses_canonical_label_and_never_emits_missing_original_link(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = self._make_db(root)
            archive = root / "archive" / ("c" * 64)
            archive.mkdir(parents=True)
            (archive / "original").write_bytes(b"%PDF-1.7\nphase8-test")
            (root / "document-aliases.json").write_text(json.dumps({
                "policy": {"purpose": "local_display_grouping_only", "formalAuthority": "knowledge",
                           "databaseMutation": False, "archiveMutation": False},
                "groups": [{"canonicalVersionId": "L007", "title": "消防设施通用规范",
                            "memberDocumentKeys": ["legacy\x1f2022"]}],
            }, ensure_ascii=False), encoding="utf-8")
            out = root / "site"
            old_argv = sys.argv
            try:
                sys.argv = [str(MODULE_PATH), "--library", str(db), "--output", str(out)]
                self.assertEqual(library_site.main(), 0)
            finally:
                sys.argv = old_argv

            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("GB 55036-2022", index)
            self.assertIn("canonical L007", index)
            pages = list((out / "laws").glob("*.html"))
            self.assertEqual(len(pages), 2)
            canonical_page = next(p for p in pages if "消防设施通用规范" in p.name)
            self.assertIn("打开原始文件", canonical_page.read_text(encoding="utf-8"))
            legacy_page = next(p for p in pages if "历史证据记录" in p.name)
            self.assertNotIn("打开原始文件", legacy_page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
