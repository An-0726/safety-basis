from io import BytesIO
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/pipeline"))
import legal_text


class LegalTextTests(unittest.TestCase):
    def docx(self, paragraphs):
        out = BytesIO()
        body = "".join("<w:p>" + "".join(f"<w:r><w:t>{part}</w:t></w:r>" for part in parts) + "</w:p>"
                       for parts in paragraphs)
        with ZipFile(out, "w") as z:
            z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                       + body + "</w:body></w:document>")
        return out.getvalue()

    def test_docx_runs_are_joined_and_chapter_is_not_part_of_clause(self):
        blob = self.docx([["测试法"], ["第一章 总则"], ["第一", "条", " 设施应完好。"],
                          ["（一）保持通道畅通；"], ["（二）保持标志清晰。"], ["第二章 管理"], ["第二条 记录应存档。"]])
        result = legal_text.directory(blob)
        self.assertEqual(result["articleCount"], 2)
        self.assertEqual(result["extractionIssues"], [])
        clause = result["articles"][0]
        self.assertNotIn("第二章", clause["quote"])
        self.assertEqual(len(clause["subitemCandidates"]), 2)
        first = clause["subitemCandidates"][0]
        self.assertIn("保持通道畅通", clause["quote"][first["textStart"]:first["textEnd"]])
        self.assertEqual(result["legalVerification"], "待核验")

    def test_missing_and_duplicate_articles_are_not_silently_accepted(self):
        data = legal_text.directory(self.docx([["第一条 文本。"], ["第三条 文本。"], ["第三条 不同文本。"]]))
        self.assertEqual(len(data["extractionIssues"]), 2)

    def test_numbers_and_nonstatutory_layout(self):
        self.assertEqual(legal_text.chinese_number("一百二十三"), 123)
        self.assertEqual(legal_text.chinese_number("十"), 10)
        data = legal_text.directory(b"3.1 Requirement; 3.2 Another requirement.")
        self.assertEqual(data["articleCount"], 0)
        self.assertTrue(data["extractionIssues"])


if __name__ == "__main__":
    unittest.main()
