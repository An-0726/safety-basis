"""A clean checkout must produce the same business release hash."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class UnifiedReleaseReproducibilityTests(unittest.TestCase):
    def test_reversed_entity_discovery_and_hash_seed_do_not_change_release(self):
        script = r"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tools' / 'v4'))
import build_unified_release as builder
original = builder.load_dir
reverse = sys.argv[2] == 'reverse'
def permuted(root, rel):
    entities = original(root, rel)
    return {key: entities[key] for key in sorted(entities, reverse=reverse)}
builder.load_dir = permuted
sys.argv = ['builder', '--out', sys.argv[1], '--as-of', '2026-09-26',
            '--data-version', '2026.09.26.reproducibility-test']
builder.main()
"""
        releases = ROOT / 'source' / 'releases'
        releases.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='repro-test-', dir=releases) as temp:
            outputs = []
            for seed, direction in [('1', 'forward'), ('7', 'reverse')]:
                out = Path(temp) / direction
                result = subprocess.run(
                    [sys.executable, '-c', script, str(out), direction],
                    cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': seed},
                    text=True, capture_output=True, timeout=120, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                outputs.append(out)
            left, right = outputs
            first = json.loads((left / 'release.json').read_text(encoding='utf-8'))
            second = json.loads((right / 'release.json').read_text(encoding='utf-8'))
            self.assertEqual(first['releaseHash'], second['releaseHash'])
            self.assertEqual(first['counts'], second['counts'])
            for relative in sorted(p.relative_to(left) for p in (left / 'data').rglob('*.json')):
                self.assertEqual((left / relative).read_bytes(),
                                 (right / relative).read_bytes(), str(relative))


if __name__ == '__main__':
    unittest.main()
