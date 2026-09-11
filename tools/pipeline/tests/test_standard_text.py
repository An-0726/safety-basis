import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import standard_text


class StandardTextTests(unittest.TestCase):
    def test_decimal_clauses_and_tables_are_separate(self):
        rows = [
            "4 安全要求……………………4", "4.1 通则……………………4",
            "4 安全要求", "4.1 通则", "4.1.1 应设置防护装置。",
            "表 1 一般要求", "序号 安全要求", "1 防护装置", "4.1.1", "5 表内分组",
            "4.2 专项要求", "该节适用。", "表 2 专项要求", "序号 安全要求", "1 联锁",
            "5 验证", "5.1 验证方法", "5.1.1 采用功能试验。",
            "附 录 B", "(规范性)", "验证清单", "表 B.1 验证清单",
            "序号 安全要求", "1 应设置防护装置", "4.1.1", "参 考 文 献", "GB/T 1",
        ]
        with patch.object(standard_text.legal_text, "paragraphs", return_value=rows):
            result = standard_text.directory(b"snapshot")
        clauses = [x["locator"] for x in result["nodes"] if x["nodeType"] == "clause_candidate"]
        tables = [x for x in result["nodes"] if x["nodeType"] == "table"]
        self.assertEqual(clauses, ["4.1", "4.1.1", "4.2", "5.1", "5.1.1"])
        self.assertEqual([x["locator"] for x in tables], ["表 1", "表 2", "表 B.1"])
        self.assertIn("4.1.1", tables[0]["rawText"])
        self.assertIn("5 表内分组", tables[0]["rawText"])
        self.assertNotIn("GB/T 1", tables[-1]["rawText"])
        self.assertEqual(result["legalVerification"], "待核验")
        self.assertEqual(result["catalogImportStatus"], "未生成")


if __name__ == "__main__":
    unittest.main()
