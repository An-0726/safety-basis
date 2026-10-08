#!/usr/bin/env python3
"""Create bounded, downloadable review volumes without dropping browser evidence.

The original complete browser artifact is retained by the workflow. These
additional focused volumes cover every current-batch source-affected formal H at
1440/390px; inherited unrelated screenshots are still in the complete artifact.
Missing screenshots are recorded as missing, never manufactured as a GUI pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

MAX_BYTES = 24 * 1024 * 1024
MAX_IMAGES = 60
MAX_PARTS = 10
MANIFEST_RESERVE = 128 * 1024
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tools/browser/fixtures/pending_source_20261008.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def partition(files, *, byte_limit=MAX_BYTES, image_limit=MAX_IMAGES):
    parts, batch, size, images = [], [], MANIFEST_RESERVE, 0
    for path, relative in files:
        file_size = path.stat().st_size
        is_image = path.suffix.lower() == '.png'
        if file_size + MANIFEST_RESERVE > byte_limit:
            raise AssertionError('Single evidence file exceeds focused volume limit: ' + relative)
        if batch and (size + file_size > byte_limit or images + is_image > image_limit):
            parts.append(batch); batch, size, images = [], MANIFEST_RESERVE, 0
        batch.append((path, relative)); size += file_size; images += is_image
    if batch:
        parts.append(batch)
    return parts


def package(source, out, fixture_path=FIXTURE):
    source, out, fixture_path = Path(source), Path(out), Path(fixture_path)
    if out.exists() and any(out.iterdir()):
        raise AssertionError('Focused output must be new or empty; refusing stale evidence mix')
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    ids = fixture['batchAudit']['currentBatchHazardIds']
    if not ids or ids != sorted(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', hid) for hid in ids):
        raise AssertionError('Focused hazards must be the exact sorted current-batch source-pinned IDs')
    if not set(ids) <= set(fixture['changedHazardIds']):
        raise AssertionError('Focused hazard absent from full browser detail coverage')
    groups, missing, selected = [], [], []
    for width in (1440, 390):
        files = []
        for hid in ids:
            relative = f'recovery-screenshots/recovery-{width}-{hid}.png'
            path = source / relative
            if path.is_file():
                files.append((path, relative)); selected.append(relative)
            else:
                missing.append(relative)
            failed_relative = f'recovery-screenshots/FAILED-recovery-{width}-{hid}.png'
            if (source / failed_relative).is_file():
                files.append((source / failed_relative, failed_relative))
        groups.append((f'screenshots-{width}', files))
    summary = []
    for pattern in ('*.json', 'ordinary-table-*.png', 'ordinary-law-table-*.png',
                    'FAILED-ordinary-*.png', 'tsg-reading-*.png'):
        for path in sorted(source.glob(pattern)):
            item = (path, path.relative_to(source).as_posix())
            if item not in summary and path.is_file(): summary.append(item)
    for filename in ('browser.json', 'browser-public.json'):
        if (source / filename).is_file():
            browser_report = json.loads((source / filename).read_text())
            if browser_report.get('failed') == 0 and browser_report.get('checks') and missing:
                raise AssertionError('Browser reported success but current-batch screenshots are missing; no evidence omitted')
    out.mkdir(parents=True, exist_ok=True)
    inventory_path = out / 'focused-evidence-inventory.json'
    inventory = {'schemaVersion': 'complete-remaining-focused-artifacts-v1',
        'sourceFixtureSha256': sha(fixture_path), 'knowledgeSnapshotHash': fixture['knowledgeSnapshotHash'],
        'selectedHazardIds': ids, 'expectedScreenshotCount': len(ids) * 2,
        'presentScreenshotCount': len(selected), 'missingScreenshotPaths': missing,
        'fullEvidenceRetainedInOriginalWorkflowArtifact': True,
        'limits': {'maxUncompressedBytes': MAX_BYTES, 'maxImagesPerPart': MAX_IMAGES, 'maxParts': MAX_PARTS},
        'note': 'Artifact packaging is not a pass verdict. Consult browser JSON and every missing/failed screenshot.'}
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary.append((inventory_path, inventory_path.name))
    plan = [(group, batch) for group, files in [('summary', summary), *groups] for batch in partition(files)]
    if len(plan) > MAX_PARTS:
        raise AssertionError(f'Focused evidence needs {len(plan)} volumes, exceeds reviewed maximum {MAX_PARTS}; no files omitted')
    result = []
    for number, (group, batch) in enumerate(plan, 1):
        name = f'part-{number:02d}'; destination = out / name; destination.mkdir()
        rows = []
        for path, relative in batch:
            target = destination / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            rows.append({'path': relative, 'bytes': target.stat().st_size, 'sha256': sha(target)})
        manifest = {'schemaVersion': 'complete-remaining-focused-volume-v1', 'part': name,
            'group': group, 'sourceFixtureSha256': inventory['sourceFixtureSha256'], 'files': rows}
        (destination / 'part-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        raw_bytes = sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
        images = sum(p.suffix.lower() == '.png' for p in destination.rglob('*') if p.is_file())
        if raw_bytes > MAX_BYTES or images > MAX_IMAGES:
            raise AssertionError('Focused volume exceeded its bound: ' + name)
        result.append({'part': name, 'group': group, 'bytes': raw_bytes, 'images': images})
    return {'parts': result, 'missingScreenshotCount': len(missing), 'presentScreenshotCount': len(selected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    args = parser.parse_args()
    result = package(args.source, args.out, args.fixture)
    if os.environ.get('GITHUB_OUTPUT'):
        present = {row['part'] for row in result['parts']}
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            for number in range(1, MAX_PARTS + 1):
                output.write(f'part_{number:02d}={str(f"part-{number:02d}" in present).lower()}\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
