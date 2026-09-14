"""Tests for non-destructive private fulltext display grouping."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "v4"))
import library_site


class LibrarySiteAliasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_aliases(self, groups):
        path = self.root / library_site.ALIASES_FILE
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": library_site.ALIASES_SCHEMA,
                    "groups": groups,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def doc(key, title, version, label=None):
        return {
            "key": key,
            "id": key.split("\x1f")[0],
            "title": title,
            "version": version,
            "paras": 1,
            "current": "现行有效",
            "review": "已核验",
            "url": "",
            "archive_ref": "",
            "label": label or version,
            "file": key.replace("\x1f", "-")
        }

    def test_alias_group_collapses_display_only(self):
        self.write_aliases(
            [
                {
                    "groupId": "LV_CANON",
                    "title": "同一法规",
                    "classification": "same_real_version",
                    "canonicalVersionId": "LV_CANON",
                    "memberDocumentKeys": ["OLD\x1f2022", "NEW\x1fGB 1-2022"],
                }
            ]
        )
        aliases = library_site.load_alias_groups(str(self.root))
        docs = [
            self.doc("OLD\x1f2022", "同一法规", "2022"),
            self.doc("NEW\x1fGB 1-2022", "同一法规", "GB 1-2022"),
            self.doc("V1\x1f2017", "另一法规", "2017"),
            self.doc("V2\x1f2026", "另一法规", "2026"),
        ]
        knowledge = {
            "LV_CANON": {
                "id": "LV_CANON",
                "officialName": "同一法规",
                "documentNumber": "GB 1-2022",
            }
        }
        groups = library_site.group_documents(docs, aliases, knowledge)
        self.assertEqual(len(groups), 3)
        grouped = next(g for g in groups if g["group_id"] == "LV_CANON")
        self.assertEqual(len(grouped["members"]), 2)
        self.assertEqual(grouped["label"], "GB 1-2022")
        # 同标题但未声明 alias 的真实不同版本仍各自保留。
        self.assertEqual(sum(g["title"] == "另一法规" for g in groups), 2)
        # 底层 docs 没被修改/删除。
        self.assertEqual(len(docs), 4)

    def test_missing_member_fails_safe_to_singletons(self):
        self.write_aliases(
            [
                {
                    "groupId": "LV_CANON",
                    "title": "同一法规",
                    "classification": "same_real_version",
                    "canonicalVersionId": "LV_CANON",
                    "memberDocumentKeys": ["OLD\x1f2022", "MISSING\x1f2022"],
                }
            ]
        )
        aliases = library_site.load_alias_groups(str(self.root))
        docs = [self.doc("OLD\x1f2022", "同一法规", "2022")]
        groups = library_site.group_documents(docs, aliases, {})
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]["group_id"].startswith("DOC:"))

    def test_duplicate_document_membership_is_rejected(self):
        self.write_aliases(
            [
                {
                    "groupId": "A",
                    "title": "A",
                    "classification": "same_real_version",
                    "memberDocumentKeys": ["X\x1f1", "Y\x1f1"],
                },
                {
                    "groupId": "B",
                    "title": "B",
                    "classification": "same_real_version",
                    "memberDocumentKeys": ["X\x1f1", "Z\x1f1"],
                },
            ]
        )
        with self.assertRaisesRegex(ValueError, "同时属于多个组"):
            library_site.load_alias_groups(str(self.root))


if __name__ == "__main__":
    unittest.main()
