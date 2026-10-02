"""Archived input guards are tested without executing any legacy business code."""
import argparse
import ast
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "tools/archive/maintenance_legacy"
ENV_INPUTS = [
    ("analyze_new_hazard_candidates.py", "BOOK", "SAFETY_BASIS_WORKBOOK_20260913", "file"),
    ("build_excel_backfill_proposal.py", "BOOK", "SAFETY_BASIS_WORKBOOK_20260913", "file"),
    *[(name + ".py", "EXCEL_PATH", "SAFETY_BASIS_WORKBOOK_20260914", "file") for name in (
        "compare_excel_dups", "disposition_engine_434", "match_434_clauses",
        "read_excel_proposed_details", "review_434_backlog_full")],
    ("promote_revised_workbook_exact_clauses.py", "XLSX", "SAFETY_BASIS_WORKBOOK_20260914", "file"),
    ("remediate_from_audit_workbook.py", "REPO_ROOT", "SAFETY_BASIS_REPO_ROOT", "dir"),
    ("remediate_from_audit_workbook.py", "SCRATCH", "SAFETY_BASIS_AUDIT_SCRATCH", "dir"),
]
CLI_INPUTS = {
    "apply_workbook_revised_20260914.py": "--xlsx",
    "reconcile_hazard_target_set.py": "--xlsx",
    "select_phase6_reuse_candidates.py": "--xlsx",
    "classify_local_law_folder.py": "--source",
}


def guard_code(filename, variable):
    tree = ast.parse((LEGACY / filename).read_text(encoding="utf-8"))
    start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == variable + "_INPUT" for t in n.targets))
    nodes = tree.body[start:start + 4]
    assert [type(n) for n in nodes] == [ast.Assign, ast.If, ast.Assign, ast.If]
    return compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec")


class LegacyPrivateInputTests(unittest.TestCase):
    def test_all_affected_scripts_compile_without_execution(self):
        names = {x[0] for x in ENV_INPUTS} | set(CLI_INPUTS) | {"verify_private_local_acceptance.py"}
        for name in names:
            with self.subTest(name=name):
                compile((LEGACY / name).read_text(encoding="utf-8"), name, "exec")

    def test_environment_inputs_missing_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            for name, variable, env, _ in ENV_INPUTS:
                with self.subTest(name=name, variable=variable), self.assertRaisesRegex(SystemExit, env):
                    exec(guard_code(name, variable), {"os": os, "Path": Path})

    def test_environment_inputs_blank_fail_closed(self):
        for name, variable, env, _ in ENV_INPUTS:
            with self.subTest(name=name, variable=variable), patch.dict(os.environ, {env: "  "}, clear=True):
                with self.assertRaisesRegex(SystemExit, env):
                    exec(guard_code(name, variable), {"os": os, "Path": Path})

    def test_environment_inputs_nonexistent_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, variable, env, _ in ENV_INPUTS:
                with self.subTest(name=name, variable=variable), patch.dict(os.environ, {env: str(Path(tmp) / "missing")}, clear=True):
                    with self.assertRaisesRegex(SystemExit, env):
                        exec(guard_code(name, variable), {"os": os, "Path": Path})

    def test_environment_inputs_wrong_kind_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "input.xlsx"
            file.touch()
            for name, variable, env, kind in ENV_INPUTS:
                wrong = tmp if kind == "file" else str(file)
                with self.subTest(name=name, variable=variable), patch.dict(os.environ, {env: wrong}, clear=True):
                    with self.assertRaisesRegex(SystemExit, env):
                        exec(guard_code(name, variable), {"os": os, "Path": Path})

    def test_environment_inputs_explicit_valid_paths_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "input.xlsx"
            file.touch()
            for name, variable, env, kind in ENV_INPUTS:
                value = str(file) if kind == "file" else tmp
                scope = {"os": os, "Path": Path}
                with self.subTest(name=name, variable=variable), patch.dict(os.environ, {env: value}, clear=True):
                    exec(guard_code(name, variable), scope)
                    self.assertEqual(scope[variable], Path(value))

    def test_cli_private_inputs_are_required_without_default(self):
        for name, flag in CLI_INPUTS.items():
            with self.subTest(name=name):
                tree = ast.parse((LEGACY / name).read_text(encoding="utf-8"))
                call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument"
                            and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == flag)
                self.assertIn("required", {x.arg for x in call.keywords})
                self.assertNotIn("default", {x.arg for x in call.keywords})
                required = next(x.value for x in call.keywords if x.arg == "required")
                self.assertIs(ast.literal_eval(required), True)
                parser = argparse.ArgumentParser(exit_on_error=False)
                parser.add_argument(flag, type=Path, required=True)
                self.assertEqual(getattr(parser.parse_args([flag, "input.xlsx"]), flag[2:]), Path("input.xlsx"))

    def test_archived_sources_have_no_personal_machine_defaults(self):
        for name in {x[0] for x in ENV_INPUTS} | set(CLI_INPUTS) | {"verify_private_local_acceptance.py"}:
            with self.subTest(name=name):
                self.assertIsNone(re.search(r"[A-Za-z]:[/\\](?:Desktop|Users|ESH)[/\\]", (LEGACY / name).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
