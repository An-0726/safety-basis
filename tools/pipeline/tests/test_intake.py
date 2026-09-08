import json
import io
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PIPELINE = Path(__file__).resolve().parents[1]
REPO = PIPELINE.parents[1]
sys.path.insert(0, str(PIPELINE))

import intake  # noqa: E402


MAPPING = json.loads(
    (REPO / "source" / "mappings" / "default.json").read_text(encoding="utf-8")
)


def inline_string_cell(ref, value):
    value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'


def formula_cell(ref, formula):
    return f'<c r="{ref}"><f>{formula}</f><v></v></c>'


def worksheet(rows):
    body = []
    for row_no, values in enumerate(rows, 1):
        cells = []
        for col_no, value in enumerate(values, 1):
            ref = f"{chr(64 + col_no)}{row_no}"
            cells.append(
                formula_cell(ref, value[1]) if isinstance(value, tuple) else inline_string_cell(ref, value)
            )
        body.append(f'<row r="{row_no}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(body)}</sheetData></worksheet>'
    )


def xlsx_bytes(sheets):
    sheet_entries = []
    rel_entries = []
    content_entries = []
    for number, (name, rows) in enumerate(sheets, 1):
        sheet_entries.append(
            f'<sheet name="{name}" sheetId="{number}" '
            f'r:id="rId{number}" />'
        )
        rel_entries.append(
            f'<Relationship Id="rId{number}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{number}.xml" />'
        )
        content_entries.append(
            f'<Override PartName="/xl/worksheets/sheet{number}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml" />'
        )
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
            '<Default Extension="xml" ContentType="application/xml" />'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml" />'
            f'{"".join(content_entries)}</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml" /></Relationships>'
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(sheet_entries)}</sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{"".join(rel_entries)}</Relationships>'
        ),
    }
    for number, (_, rows) in enumerate(sheets, 1):
        files[f"xl/worksheets/sheet{number}.xml"] = worksheet(rows)
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    output.seek(0)
    return output.read()


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.db_path = root / "staging" / "intake.sqlite3"
        self.archive = root / "archive"
        self.input_dir = root / "inputs"
        self.input_dir.mkdir()
        self.conn = intake.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def write(self, name, content):
        path = self.input_dir / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_csv_ingest_is_idempotent(self):
        path = self.write("one.csv", "隐患名称,场所\n灭火器失压,车间\n")
        first = intake.ingest(self.conn, path, MAPPING, self.archive)
        second = intake.ingest(self.conn, path, MAPPING, self.archive)

        self.assertEqual(first["status"], "complete")
        self.assertFalse(first["repeated"])
        self.assertTrue(second["repeated"])
        self.assertEqual(second["status"], "complete")
        self.assertEqual(self.count("sources"), 1)
        self.assertEqual(self.count("import_runs"), 1)
        self.assertEqual(self.count("source_rows"), 1)
        self.assertEqual(self.count("candidates"), 1)
        self.assertEqual(self.count("candidate_sources"), 1)

    def test_numeric_zero_and_false_are_preserved(self):
        path = self.write('zero.json', json.dumps([
            {'title': '数值条件', 'conditions': 0},
            {'title': '数值条件', 'conditions': None},
            {'title': '数值条件', 'conditions': False}
        ], ensure_ascii=False))
        result = intake.ingest(self.conn, path, MAPPING, self.archive)
        self.assertEqual(result['status'], 'complete')
        values = {json.loads(row[0])['conditions'] for row in self.conn.execute('SELECT normalized_json FROM candidates')}
        self.assertEqual(values, {'0', '', 'False'})

    def test_corrupt_xlsx_records_rejected_run(self):
        path = self.write('broken.xlsx', b'not a zip')
        result = intake.ingest(self.conn, path, MAPPING, self.archive)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(self.count('sources'), 1)
        self.assertEqual(self.count('import_runs'), 1)
        self.assertEqual(self.count('candidates'), 0)

    def test_renamed_file_keeps_source_alias_without_new_candidate(self):
        content = '隐患名称\n测试隐患\n'
        first = self.write('first.csv', content)
        second = self.write('second.csv', content)
        intake.ingest(self.conn, first, MAPPING, self.archive)
        result = intake.ingest(self.conn, second, MAPPING, self.archive)
        self.assertTrue(result['repeated'])
        self.assertEqual(self.count('sources'), 1)
        self.assertEqual(self.count('source_locations'), 2)
        self.assertEqual(self.count('candidates'), 1)

    def test_json_ingest_is_idempotent(self):
        path = self.write(
            "one.json",
            json.dumps([{"title": "配电箱门未闭合", "place": "车间"}], ensure_ascii=False),
        )
        first = intake.ingest(self.conn, path, MAPPING, self.archive)
        second = intake.ingest(self.conn, path, MAPPING, self.archive)
        self.assertEqual(first["status"], "complete")
        self.assertTrue(second["repeated"])
        self.assertEqual(self.count("import_runs"), 1)
        self.assertEqual(self.count("candidates"), 1)

    def test_same_candidate_merges_across_sources_and_keeps_traceability(self):
        first_path = self.write("first.csv", "隐患名称,场所,原始编号\n配电箱门未闭合,车间,A-1\n")
        second_path = self.write("second.csv", "隐患名称,场所,原始编号\n配电箱门未闭合,车间,B-9\n")
        first = intake.ingest(self.conn, first_path, MAPPING, self.archive)
        second = intake.ingest(self.conn, second_path, MAPPING, self.archive)

        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(self.count("sources"), 2)
        self.assertEqual(self.count("source_rows"), 2)
        self.assertEqual(self.count("candidates"), 1)
        self.assertEqual(self.count("candidate_sources"), 2)

    def test_conditions_and_units_do_not_merge(self):
        path = self.write(
            "different.csv",
            "隐患名称,适用条件\n"
            "软管长度 5 m,常温\n"
            "软管长度 5 m,高温\n"
            "软管长度 10 m,常温\n",
        )
        result = intake.ingest(self.conn, path, MAPPING, self.archive)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.count("source_rows"), 3)
        self.assertEqual(self.count("candidates"), 3)

    def test_missing_required_field_rejects_whole_file_but_retains_original_and_rows(self):
        content = "场所,整改措施\n车间,修复线路\n".encode("utf-8")
        path = self.write("missing-title.csv", content)
        result = intake.ingest(self.conn, path, MAPPING, self.archive)
        sha = intake.digest(content)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["rows"], 1)
        self.assertTrue(any("missing fields" in error for error in result["errors"]))
        archived = self.archive / sha / "original"
        self.assertEqual(archived.read_bytes(), content)
        self.assertEqual(self.count("source_rows"), 1)
        self.assertEqual(self.count("candidates"), 0)
        self.assertEqual(self.conn.execute("SELECT status FROM import_runs").fetchone()[0], "rejected")

    def test_mapping_change_retries_same_source(self):
        path = self.write("renamed.csv", "Name\n配电箱门未闭合\n")
        bad_mapping = {"fields": {"title": ["title"]}, "required": ["title"]}
        good_mapping = {"fields": {"title": ["Name"]}, "required": ["title"]}
        first = intake.ingest(self.conn, path, bad_mapping, self.archive)
        second = intake.ingest(self.conn, path, good_mapping, self.archive)

        self.assertEqual(first["status"], "rejected")
        self.assertEqual(second["status"], "complete")
        self.assertFalse(second["repeated"])
        self.assertEqual(self.count("import_runs"), 2)
        self.assertEqual(self.count("source_rows"), 1)
        self.assertEqual(self.count("candidates"), 1)
        self.assertEqual(self.count("candidate_sources"), 1)

    def test_duplicate_header_rejects_file(self):
        content = "隐患名称,隐患名称\n第一条,第二条\n".encode("utf-8")
        path = self.write("duplicate-header.csv", content)
        result = intake.ingest(self.conn, path, MAPPING, self.archive)

        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any("duplicate header" in error for error in result["errors"]))
        self.assertEqual(self.count("source_rows"), 1)
        self.assertEqual(self.count("candidates"), 0)

    def test_xlsx_reads_all_sheets(self):
        content = xlsx_bytes(
            [
                ("检查表", [["隐患名称", "场所"], ["灭火器失压", "车间"]]),
                ("复核", [["隐患名称", "场所"], ["配电箱门未闭合", "仓库"]]),
            ]
        )
        path = self.write("multi-sheet.xlsx", content)
        result = intake.ingest(self.conn, path, MAPPING, self.archive)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["rows"], 2)
        self.assertEqual(self.count("source_rows"), 2)
        self.assertEqual(
            {row[0] for row in self.conn.execute("SELECT sheet FROM source_rows")},
            {"检查表", "复核"},
        )
        self.assertEqual(self.count("candidates"), 2)

    def test_xlsx_formula_rejects_file_and_retains_row(self):
        content = xlsx_bytes(
            [("检查表", [["隐患名称", "整改措施"], [("formula", "1+1"), "人工复核"]])]
        )
        path = self.write("formula.xlsx", content)
        result = intake.ingest(self.conn, path, MAPPING, self.archive)

        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any("formula cell" in error for error in result["errors"]))
        self.assertEqual(self.count("source_rows"), 1)
        self.assertEqual(self.count("candidates"), 0)


if __name__ == "__main__":
    unittest.main()
