from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/pipeline"))
import planning


class CitationExtractionTests(unittest.TestCase):
    def test_standard_versions_and_recommended_prefix_remain_distinct(self):
        refs = planning.extract_references("GB 50016—2014；GB/T 50016-2014；GB50016-2006")
        self.assertEqual([r["key"] for r in refs["documents"]],
                         ["GB 50016-2014", "GB/T 50016-2014", "GB 50016-2006"])

    def test_adjacent_standard_name_is_not_an_extra_law(self):
        refs = planning.extract_references("《危险化学品使用安全专项治理导则》（DB32/T 4293—2022）8.2")
        self.assertEqual(len(refs["documents"]), 1)
        self.assertEqual(refs["documents"][0]["key"], "DB32/T 4293-2022")
        self.assertEqual(refs["documents"][0]["nameHint"], "危险化学品使用安全专项治理导则")

    def test_multi_document_clause_attribution_stays_a_hint(self):
        refs = planning.extract_references("《中华人民共和国消防法》第二十八条；《建筑防火通用规范》（GB55037-2022）")
        self.assertEqual(len(refs["documents"]), 2)
        self.assertTrue(refs["hasMultipleDocuments"])
        self.assertEqual(refs["articleHints"], ["第二十八条"])

    def test_missing_version_and_unparseable_text_are_visible(self):
        ref = planning.extract_references("GB 50016")["documents"][0]
        self.assertEqual(ref["citedVersion"], "")
        self.assertTrue(planning.extract_references("安全生产有关文件")["unparsed"])
        self.assertEqual(planning.extract_references("符合")["documents"], [])


if __name__ == "__main__":
    unittest.main()
