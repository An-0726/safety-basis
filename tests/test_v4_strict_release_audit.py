import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StrictV4ReleaseAuditTest(unittest.TestCase):
    def test_strict_audit_runs(self):
        p = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "v4" / "strict_release_audit.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        print(p.stdout)
        if p.stderr:
            print(p.stderr)
        self.assertEqual(p.returncode, 0)
        self.assertIn("STRICT_V4_RELEASE_AUDIT", p.stdout)


if __name__ == "__main__":
    unittest.main()
