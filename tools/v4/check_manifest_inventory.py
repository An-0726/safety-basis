# -*- coding: utf-8 -*-
"""Validate manifest inventory counts against physical knowledge records.

This is intentionally a blocking structural gate. The manifest is the public
inventory ledger; it must never lag behind or get ahead of the JSON records on
disk, and its hazard lifecycle totals must reconcile to the hazard files.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ENTITY_DIRS = {
    "laws": "laws",
    "lawVersions": "law-versions",
    "clauses": "clauses",
    "hazards": "hazards",
    "links": "links",
    "evidence": "evidence",
    "successions": "successions",
    "requirements": "requirements",
}
LIFECYCLES = ("active", "proposed", "superseded")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest_inventory(repo_root: Path) -> list[str]:
    knowledge = repo_root / "knowledge"
    manifest_path = knowledge / "manifest.json"
    errors: list[str] = []
    if not manifest_path.is_file():
        return ["missing knowledge/manifest.json"]

    manifest = _load_json(manifest_path)
    physical: dict[str, int] = {}

    for key, dirname in ENTITY_DIRS.items():
        files = sorted((knowledge / dirname).glob("*.json"))
        physical[key] = len(files)
        nested_value = (manifest.get("counts") or {}).get(key)
        if nested_value != physical[key]:
            errors.append(
                f"manifest count mismatch counts.{key}: manifest={nested_value!r} physical={physical[key]}"
            )
        if key in manifest and manifest.get(key) != physical[key]:
            errors.append(
                f"manifest count mismatch {key}: manifest={manifest.get(key)!r} physical={physical[key]}"
            )

    lifecycle = Counter()
    for path in sorted((knowledge / "hazards").glob("*.json")):
        hazard = _load_json(path)
        state = hazard.get("lifecycle")
        lifecycle[state] += 1
        if state not in LIFECYCLES:
            errors.append(f"invalid hazard lifecycle {path.name}: {state!r}")

    declared = manifest.get("lifecycle") or {}
    scalar_names = {
        "active": "activeHazards",
        "proposed": "proposedHazards",
        "superseded": "supersededHazards",
    }
    for state in LIFECYCLES:
        actual = lifecycle[state]
        if declared.get(state) != actual:
            errors.append(
                f"manifest lifecycle mismatch lifecycle.{state}: manifest={declared.get(state)!r} physical={actual}"
            )
        scalar = scalar_names[state]
        if manifest.get(scalar) != actual:
            errors.append(
                f"manifest lifecycle mismatch {scalar}: manifest={manifest.get(scalar)!r} physical={actual}"
            )

    lifecycle_total = sum(lifecycle[s] for s in LIFECYCLES)
    if lifecycle_total != physical["hazards"]:
        errors.append(
            f"hazard lifecycle total mismatch: lifecycle={lifecycle_total} physical={physical['hazards']}"
        )

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors = validate_manifest_inventory(repo_root)
    print("=== MANIFEST_INVENTORY_CHECK ===")
    for key, dirname in ENTITY_DIRS.items():
        count = len(list((repo_root / "knowledge" / dirname).glob("*.json")))
        print(f"{key}: {count}")
    print(f"errors: {len(errors)}")
    for error in errors:
        print("ERROR:", error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
