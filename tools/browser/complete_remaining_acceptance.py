"""Current complete-batch source pins and explicitly reviewed public withdrawals.

The production entry point loads only the new freeze. Historical fixtures stay
immutable; they are used to ensure no previously public H/K silently disappears.
"""
import copy
import hashlib
import json
from pathlib import Path
from recovery_release_acceptance import (
    load_expectations as load_frozen_expectations,
    fixture_for_release_date as shared_fixture_for_release_date,
)
from residual_clause_acceptance import FIXTURE as PRIOR_FIXTURE

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / 'fixtures/complete_remaining_20261005.json'


def validate_preservation(current, prior, withdrawals):
    if set(withdrawals) != {'hazards', 'links'}:
        raise AssertionError('Explicit H/K withdrawal sets required')
    for kind in ('hazards', 'links'):
        allowed = withdrawals[kind]
        if not isinstance(allowed, dict) or any(not isinstance(reason, str) or not reason.strip() for reason in allowed.values()):
            raise AssertionError('Every withdrawal needs an individual reviewed reason')
        old, new = set(prior['expectedIds'][kind]), set(current['expectedIds'][kind])
        if old - new != set(allowed):
            raise AssertionError('Unapproved missing or ineffective withdrawn public IDs: ' + kind)
        if set(allowed) & new:
            raise AssertionError('Withdrawn public ID leaked: ' + kind)
    permitted_profiles = {profile['id'] for row in prior.get('records', [])
        if row['id'] in withdrawals['hazards'] for profile in row.get('profiles', [])}
    for kind, permitted in (('majorHazards', set(withdrawals['hazards'])), ('profiles', permitted_profiles)):
        if kind in prior['expectedIds']:
            missing = set(prior['expectedIds'][kind]) - set(current['expectedIds'][kind])
            if not missing <= permitted:
                raise AssertionError('Unapproved old public membership lost: ' + kind)
    inherited = set(prior['changedHazardIds']) - set(withdrawals['hazards'])
    if not inherited <= set(current['changedHazardIds']):
        raise AssertionError('Inherited eligible detail coverage removed')
    if set(withdrawals['hazards']) & set(current['changedHazardIds']):
        raise AssertionError('Withdrawn hazard retained in changed-detail coverage')
    # An absent H/K must also be absent from every hydrated source basis, not just
    # the count or index. The shared contract compares all remaining IDs exactly.
    for row in current['records']:
        if row['id'] in withdrawals['hazards'] or any(b['linkId'] in withdrawals['links'] for b in row['bases']):
            raise AssertionError('Withdrawn source appears in a public detail')


def validate_batch_audit(current, root=ROOT):
    audit = current.get('batchAudit', {})
    if audit.get('schemaVersion') != 'complete-remaining-browser-audit-v1':
        raise AssertionError('Missing complete-batch browser audit')
    prior_raw = PRIOR_FIXTURE.read_bytes()
    if hashlib.sha256(prior_raw).hexdigest() != audit.get('predecessorFixtureSha256'):
        raise AssertionError('Immutable predecessor browser fixture changed')
    for relative, digest in audit['auditFileSha256'].items():
        p = Path(relative)
        if p.is_absolute() or '..' in p.parts or not relative.startswith(('docs/', 'tools/pipeline/tests/fixtures/', 'knowledge/', 'source/publication/')):
            raise AssertionError('Invalid batch audit path')
        if hashlib.sha256((Path(root) / relative).read_bytes()).hexdigest() != digest:
            raise AssertionError('Reviewed batch audit source changed: ' + relative)
    validate_preservation(current, json.loads(prior_raw), audit['withdrawals'])
    required = audit['requiredFormalHazardIds']
    if required != sorted(set(required)) or not set(required) <= set(current['changedHazardIds']):
        raise AssertionError('Authored current formal hazard is missing exact browser coverage')
    batch_ids = audit['currentBatchHazardIds']
    if batch_ids != sorted(set(batch_ids)) or not set(required) <= set(batch_ids) <= set(current['changedHazardIds']):
        raise AssertionError('Current-batch source dependency coverage changed')
    return audit


def load_expectations(path=FIXTURE, root=ROOT):
    result = load_frozen_expectations(path)
    validate_batch_audit(result, root)
    return result


def fixture_for_release_date(frozen, actual_as_of, root):
    """Retain immutable audit metadata while using the unchanged date contract."""
    validate_batch_audit(frozen, root)
    source_projection = copy.deepcopy(frozen)
    audit = source_projection.pop('batchAudit')
    projected = shared_fixture_for_release_date(source_projection, actual_as_of, root)
    projected['batchAudit'] = audit
    validate_batch_audit(projected, root)
    return projected
