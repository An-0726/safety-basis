#!/usr/bin/env python3
"""Freeze reviewed browser expectations directly from knowledge, never a bundle.

Run only after source authoring/review is quiescent. --baseline-ref is a full Git
commit of the predecessor source. A later source edit requires explicit re-freeze
and independent review; required CI only validates the committed fixture.
"""
import argparse
from collections import defaultdict
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_gate_core import evaluate_release_gate, load_dir
from release_snapshot import stable_knowledge_snapshot, source_hashes, FORMAL_NAMESPACES
from major_criteria import public_projection as major_projection
from field_profiles import public_projection as profile_projection
from basis_refs import basis_sort_key
from presentation import project_hazard
from normative_content import validate_ordinary_clause_content

REGIONS = {'CN': '全国', 'CN-32': '江苏', 'CN-3201': '南京'}


def version_title(name, number):
    def norm(value):
        return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).translate(str.maketrans('—–－', '---')).casefold()
    number = (number or '').strip()
    return f'{name} {number}' if number and norm(number) not in norm(name) else name


def baseline_hashes(root, commit):
    resolved = subprocess.check_output(['git', 'rev-parse', commit + '^{commit}'], cwd=root, text=True).strip()
    raw = subprocess.check_output(['git', 'archive', resolved, 'knowledge'], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        hashes = {m.name.removeprefix('knowledge/'): hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                  for m in archive.getmembers() if m.isfile() and m.name.endswith('.json')}
    return resolved, hashes


def project_expectations(knowledge, as_of, *, hashes, baseline_commit, baseline):
    gate = evaluate_release_gate(knowledge, as_of)
    entities = {kind: load_dir(knowledge, kind) for kind in ('hazards', 'links', 'clauses', 'law-versions', 'laws', 'evidence')}
    major = major_projection(knowledge, as_of=as_of)['topic']
    profiles = profile_projection(knowledge, as_of=as_of)['public']['records']
    public_h = set(gate.eligible_hazards)
    public_k = {kid for kid in gate.eligible_links if entities['links'][kid]['hazardId'] in public_h}
    public_c = {entities['links'][kid]['clauseId'] for kid in public_k}
    expected_ids = {'hazards': sorted(public_h), 'links': sorted(public_k), 'clauses': sorted(public_c),
                    'majorHazards': sorted(major['hazardIds']), 'profiles': sorted(p['id'] for p in profiles)}
    changed = {path for path in set(hashes) | set(baseline) if hashes.get(path) != baseline.get(path)}
    all_links = defaultdict(list)
    for link in entities['links'].values():
        all_links[link['hazardId']].append(link)
    rows, pins = [], {}
    for hid in sorted(public_h):
        dependencies = {f'hazards/{hid}.json', f'reviews/hazards/{hid}.json'}
        for link in all_links[hid]:
            clause = entities['clauses'].get(link.get('clauseId'), {})
            version = entities['law-versions'].get(clause.get('lawVersionId'), {})
            for kind, ident in [('links', link['id']), ('clauses', clause.get('id')),
                                ('law-versions', version.get('id')), ('laws', version.get('lawId'))]:
                if ident:
                    dependencies.update((f'{kind}/{ident}.json', f'reviews/{kind}/{ident}.json'))
        # Evidence edits are part of the source chain, including current reviews.
        for relative in list(dependencies):
            path = Path(knowledge) / relative
            if path.is_file():
                raw = json.loads(path.read_text())
                for eid in raw.get('evidenceRefs', []):
                    dependencies.add(f'evidence/{eid}.json')
        if not dependencies & changed:
            continue
        h = entities['hazards'][hid]
        presentation = project_hazard(h, hazard_id=hid)
        business, historical = [], []
        prefix = '原 conditions 字段记录的引用依据为：'
        for line in presentation['businessNote'].splitlines():
            if line.startswith(prefix):
                value = line[len(prefix):].removeprefix('依据：').strip()
                if value: historical.append(value)
            else: business.append(line)
        review = json.loads((Path(knowledge) / f'reviews/hazards/{hid}.json').read_text())
        checked = (review.get('checkedAt') or (review.get('migratedFromV3Verification') or {}).get('reviewedAt')
                   or review.get('reviewedAt') or review.get('createdAt') or '2026-09-19')
        row = {'id': hid, 'cohort': 'recovery_changed_public',
               'hazard': {key: h.get(key, '') for key in ('title', 'description', 'conditions', 'measures', 'category')},
               'displayCategory': presentation['displayCategory'],
               'copyNotes': {'businessNote': '\n'.join(business).strip(), 'historicalReferences': historical},
               'profiles': [{'id': p['id'], 'defaultFieldEntry': p['defaultFieldEntry']} for p in profiles if p['hazardId'] == hid],
               'changedDependencies': sorted(dependencies & changed), 'bases': []}
        row['hazard']['checked'] = checked
        row['hazard']['status'] = '已核验'
        row['hazard']['conditions'] = row['hazard']['conditions'] or ''
        row['hazard']['places'] = h.get('places') or []
        for link in sorted((k for k in all_links[hid] if k['id'] in public_k), key=basis_sort_key):
            c = entities['clauses'][link['clauseId']]
            lv = entities['law-versions'][c['lawVersionId']]
            law = entities['laws'][lv['lawId']]
            validate_ordinary_clause_content(c)
            region = law.get('jurisdictionCode') or lv.get('scope') or 'CN'
            row['bases'].append({'linkId': link['id'], 'clauseId': c['id'], 'lawId': lv['id'],
                'lawName': version_title(law.get('canonicalName') or law.get('officialName') or lv.get('officialName') or lv['id'], lv.get('documentNumber')),
                'role': link['role'], 'applicability': link['applicability'],
                'article': c.get('articlePath') or c.get('clauseNumber') or '', 'quote': c['quote'],
                'sourceUrl': c.get('sourceUrl') or lv.get('sourceUrl') or '',
                'jurisdictionCode': link.get('jurisdictionCode'),
                'clauseRegion': REGIONS.get(c.get('jurisdictionCode') or 'CN', '全国'),
                'lawRegion': REGIONS.get(region, region), 'contentParts': c.get('contentParts', [])})
        rows.append(row)
        pins.update({f'knowledge/{p}': hashes[p] for p in sorted(dependencies) if p in hashes})
    return {'schemaVersion': 'recovery-release-browser-v1', 'asOf': as_of.isoformat(),
            'baselineCommit': baseline_commit, 'sourceDerivation': 'evaluate_release_gate + source H/K/C/LV/LF + major_criteria.public_projection + field_profiles.public_projection',
            'sourceFileCount': len(hashes), 'sourceFiles': dict(sorted(pins.items())),
            'expectedIds': expected_ids, 'changedHazardIds': [r['id'] for r in rows], 'records': rows,
            'sourceChanges': {p: {'beforeSha256': baseline.get(p), 'afterSha256': hashes.get(p)} for p in sorted(changed)},
            'unpublishedProbeId': 'H_12158_10_1_2'}


def freeze(root, as_of, baseline_ref):
    baseline_commit, baseline = baseline_hashes(root, baseline_ref)
    with stable_knowledge_snapshot(root / 'knowledge') as (knowledge, digest):
        hashes = source_hashes(knowledge)
        # Only formal release inputs count, not unrelated baseline JSON files.
        baseline = {p: v for p, v in baseline.items() if p == 'manifest.json' or any(p.startswith(ns + '/') for ns in FORMAL_NAMESPACES)}
        fixture = project_expectations(knowledge, as_of, hashes=hashes, baseline_commit=baseline_commit, baseline=baseline)
        fixture['knowledgeSnapshotHash'] = digest
    from recovery_release_acceptance import validate_expectations
    validate_expectations(fixture)
    return fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--baseline-ref', required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'tools/browser/fixtures/recovery_release_20261004.json')
    args = parser.parse_args()
    fixture = freeze(args.root.resolve(), args.as_of, args.baseline_ref)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'path': str(args.out), 'knowledgeSnapshotHash': fixture['knowledgeSnapshotHash'],
        'counts': {k: len(v) for k, v in fixture['expectedIds'].items()}, 'changedPublicHazards': len(fixture['records'])}))


if __name__ == '__main__':
    main()
