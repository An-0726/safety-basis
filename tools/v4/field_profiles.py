"""Governed, reusable field-profile sidecars; never signs reviews or mutates knowledge.

The candidate pilot is deliberately not read. Publication needs BOTH the existing
legal release gate at an explicit date and a current, explicit semantic review.
See docs/FIELD_PROFILE_CONTRACT.md for the integration contract.
"""
import copy
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

from release_gate_core import evaluate_release_gate

SCHEMA_VERSION = 1
PROFILE_ROOT = 'field-profiles/v1'
ID = re.compile(r'^FPR_[A-Za-z0-9_\-]+$')
CLASSES = {'core_onsite_inspection', 'document_review', 'special_review', 'legal_obligation', 'undetermined'}
ENTRIES = {'include', 'conditional', 'exclude', 'undetermined'}
DISPOSITIONS = {'onsite_finding', 'document_check', 'special_check', 'legal_obligation', 'counterexample', 'undetermined'}
ROUTES = {'onsite_finding': 'core_onsite_inspection', 'document_check': 'document_review',
          'special_check': 'special_review', 'legal_obligation': 'legal_obligation'}
CHECKS = {'routing', 'applicability', 'findingTemplate', 'evidenceRequirements', 'correctiveDirection', 'scopeContainment'}
FIELDS = {'schemaVersion', 'id', 'revision', 'hazardId', 'title', 'inspectionClass',
          'defaultFieldEntry', 'contentDisposition', 'applicability', 'findingTemplate',
          'evidenceRequirements', 'correctiveDirection', 'basisLinkIds'}
# Safe serialization is allowlisted, including every nested object. Private review
# and drafting metadata is never copied. This pattern rejects common local paths
# in intentionally public text; it cannot detect all personal information in prose.
PRIVATE = re.compile(r'(?:[A-Za-z]:[\\/]|file://|/(?:home|Users|mnt|tmp|workspace|root|private|var)/)', re.I)
PLACEHOLDER = re.compile(r'\{\{([a-z][a-zA-Z0-9_]*)\}\}')


def digest(value):
    """Hash the complete JSON value without excluded/self-referential fields."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _strings(value, nonempty=False):
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(_text(x) for x in value) and len(value) == len(set(value)))


def _ident(value):
    # Existing stable knowledge IDs include Chinese article numbers and spaces.
    # These are lookup keys, never interpolated into filesystem paths.
    return (_text(value) and value == value.strip() and '/' not in value
            and '\\' not in value and '..' not in value
            and not any(ord(char) < 32 for char in value))


def validate_profile(profile):
    """Return stable error codes; draft/unknown states can be structurally valid."""
    if not isinstance(profile, dict):
        return ['PROFILE_NOT_OBJECT']
    errors = []
    if not FIELDS <= profile.keys():
        errors.append('PROFILE_FIELDS_MISSING')
    if type(profile.get('schemaVersion')) is not int or profile['schemaVersion'] != SCHEMA_VERSION:
        errors.append('PROFILE_SCHEMA_VERSION')
    if not isinstance(profile.get('id'), str) or not ID.fullmatch(profile['id']):
        errors.append('PROFILE_ID')
    if type(profile.get('revision')) is not int or profile['revision'] < 1:
        errors.append('PROFILE_REVISION')
    if not _ident(profile.get('hazardId')):
        errors.append('PROFILE_HAZARD_ID')
    for key in ('title', 'correctiveDirection'):
        if not _text(profile.get(key)):
            errors.append('PROFILE_CONTENT_MISSING:' + key)
    if not _strings(profile.get('basisLinkIds'), True) or not all(_ident(x) for x in profile.get('basisLinkIds', [])):
        errors.append('PROFILE_BASIS_LINKS')
    cls, entry, disposition = (profile.get(k) for k in ('inspectionClass', 'defaultFieldEntry', 'contentDisposition'))
    if not isinstance(cls, str) or cls not in CLASSES or not isinstance(entry, str) or entry not in ENTRIES or not isinstance(disposition, str) or disposition not in DISPOSITIONS:
        errors.append('PROFILE_ROUTING')
    elif disposition in ROUTES and cls != ROUTES[disposition]:
        errors.append('PROFILE_ROUTING_CONFLICT')
    if disposition != 'onsite_finding' and (not isinstance(entry, str) or entry not in {'exclude', 'undetermined'}):
        errors.append('PROFILE_NON_ONSITE_ENTRY')
    app = profile.get('applicability')
    if not isinstance(app, dict) or set(app) != {'requires', 'excludes', 'perUseFacts'}:
        errors.append('PROFILE_APPLICABILITY')
    elif not _strings(app['requires'], True) or not _strings(app['excludes']) or not _strings(app['perUseFacts'], True):
        errors.append('PROFILE_APPLICABILITY')
    elif disposition == 'onsite_finding' and not {'applicableRequirementConfirmed', 'siteTriggerConfirmed', 'defectObserved'} <= set(app['perUseFacts']):
        errors.append('PROFILE_ONSITE_FACTS')
    if not _strings(profile.get('evidenceRequirements'), True):
        errors.append('PROFILE_EVIDENCE_REQUIREMENTS')
    template = profile.get('findingTemplate')
    if disposition != 'onsite_finding':
        if template is not None:
            errors.append('PROFILE_NON_ONSITE_TEMPLATE')
    elif not isinstance(template, dict) or set(template) != {'text', 'slots'} or not _text(template.get('text')) or not isinstance(template.get('slots'), list) or not template['slots']:
        errors.append('PROFILE_TEMPLATE')
    else:
        keys = []
        for slot in template['slots']:
            if not isinstance(slot, dict) or set(slot) != {'key', 'label'} or not _text(slot.get('key')) or not _text(slot.get('label')):
                errors.append('PROFILE_TEMPLATE_SLOT')
                continue
            keys.append(slot['key'])
        matches = set(PLACEHOLDER.findall(template['text']))
        if not matches or matches != set(keys) or len(keys) != len(set(keys)) or '{{' in PLACEHOLDER.sub('', template['text']) or '}}' in PLACEHOLDER.sub('', template['text']):
            errors.append('PROFILE_TEMPLATE_PLACEHOLDERS')
    # Reject leaks in public allowlisted values, not arbitrary private metadata.
    if PRIVATE.search(json.dumps({k: profile[k] for k in FIELDS if k in profile}, ensure_ascii=False)):
        errors.append('PROFILE_PRIVATE_TEXT')
    return sorted(set(errors))


def _load_namespace(root, rel, review=False):
    """Reject ambiguity rather than silently overwriting duplicate entity IDs."""
    result = {}
    for path in sorted((root / rel).glob('*.json')):
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('non-object JSON in ' + rel)
        key = value.get('entityId') if review else value.get('id')
        if review and not key:
            key = path.stem
        if not _ident(key) or key in result:
            raise ValueError('invalid or duplicate identity in ' + rel)
        result[key] = value
    return result


class ProfileContext:
    """Read-only snapshot used for fingerprints; create fresh for each build."""
    def __init__(self, knowledge):
        self.root = Path(knowledge)
        kinds = ('hazards', 'links', 'clauses', 'law-versions', 'laws', 'evidence')
        self.entities = {kind: _load_namespace(self.root, kind) for kind in kinds}
        self.reviews = {kind: _load_namespace(self.root, 'reviews/' + kind, True) for kind in kinds if kind != 'evidence'}

    def dependencies(self, profile, *, selected_only=False):
        bound = {}
        def bind(kind, ident):
            key = kind + '/' + str(ident)
            if key in bound:
                return
            obj = self.entities[kind].get(ident)
            bound[key] = obj
            if kind == 'evidence':
                return
            review = self.reviews[kind].get(ident)
            bound['reviews/' + key] = review
            for source in (obj, review):
                if source:
                    refs = source.get('evidenceRefs', [])
                    if not isinstance(refs, list):
                        raise ValueError('invalid evidenceRefs in dependency')
                    for ref in refs:
                        if isinstance(ref, str):
                            eid = ref
                        elif isinstance(ref, dict):
                            eid = ref.get('evidenceId') or ref.get('id')
                        else:
                            raise ValueError('invalid evidence reference in dependency')
                        if not _ident(eid):
                            raise ValueError('invalid evidence identity in dependency')
                        bind('evidence', eid)
            if obj:
                if kind == 'links':
                    bind('clauses', obj.get('clauseId'))
                elif kind == 'clauses':
                    bind('law-versions', obj.get('lawVersionId'))
                elif kind == 'law-versions':
                    bind('laws', obj.get('lawId'))
        hid = profile['hazardId']
        bind('hazards', hid)
        # Whole source association set, not just selected bases: additions and
        # removals both invalidate semantic review, even if unselected/proposed.
        associated = sorted(key for key, link in self.entities['links'].items() if link.get('hazardId') == hid)
        bound['associationIds'] = associated
        for key in sorted(set(profile['basisLinkIds']) | (set() if selected_only else set(associated))):
            bind('links', key)
        return bound

    def fingerprint(self, profile):
        return digest(self.dependencies(profile))


def review_bindings(profile, knowledge):
    """Compute binding values for an independent reviewer; never approves/signs."""
    errors = validate_profile(profile)
    if errors:
        raise ValueError(','.join(errors))
    context = knowledge if isinstance(knowledge, ProfileContext) else ProfileContext(knowledge)
    return {'reviewedProfileHash': digest(profile), 'dependencyFingerprint': context.fingerprint(profile)}


def _review_errors(profile, review, context, as_of):
    if not review:
        return ['PROFILE_REVIEW_MISSING']
    errors = []
    if review.get('schemaVersion') != 1 or review.get('entityId') != profile['id'] or review.get('profileRevision') != profile['revision']:
        errors.append('PROFILE_REVIEW_IDENTITY')
    if review.get('decision') != 'verified':
        errors.append('PROFILE_REVIEW_NOT_VERIFIED')
    if not _text(review.get('reviewer')) or not _text(review.get('reason')):
        errors.append('PROFILE_REVIEW_METADATA')
    try:
        reviewed = date.fromisoformat(review.get('reviewedOn', ''))
        if reviewed > as_of:
            errors.append('PROFILE_REVIEW_FUTURE')
    except (TypeError, ValueError):
        errors.append('PROFILE_REVIEW_DATE')
    scope_reasons = review.get('basisScopeReasons')
    if not isinstance(scope_reasons, dict) or set(scope_reasons) != set(profile['basisLinkIds']) or not all(_text(x) for x in scope_reasons.values()):
        errors.append('PROFILE_SCOPE_REVIEW_INCOMPLETE')
    checks = review.get('semanticChecks')
    if not isinstance(checks, dict) or set(checks) != CHECKS or any(value is not True for value in checks.values()):
        errors.append('PROFILE_SEMANTIC_REVIEW_INCOMPLETE')
    for key, expected in review_bindings(profile, context).items():
        if review.get(key) != expected:
            errors.append('PROFILE_REVIEW_STALE:' + key)
    return errors




def _selected_review_date_errors(dependencies, as_of):
    """Validate explicitly supplied review dates without inventing legacy dates.

    as_of is a calendar date; timestamp comparisons use the date written in the
    timestamp's own timezone, rather than silently applying a machine timezone.
    """
    errors = []
    for key, review in dependencies.items():
        if not key.startswith('reviews/') or review is None:
            continue
        for field in ('checkedAt', 'reviewedAt', 'reviewedOn'):
            if field not in review:
                continue
            value = review[field]
            try:
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ].+)?', value):
                    raise ValueError('invalid review date')
                reviewed = (date.fromisoformat(value) if len(value) == 10
                            else datetime.fromisoformat(value).date())
            except ValueError:
                errors.append('SELECTED_REVIEW_DATE_INVALID:' + field)
                continue
            if reviewed > as_of:
                errors.append('SELECTED_REVIEW_DATE_FUTURE:' + field)
    return errors


def _selected_version_date_errors(version):
    """Do not let malformed expiry values become unbounded current validity.

    This additional profile boundary leaves the shared legacy Gate unchanged.
    An absent/null/empty endDate is intentionally open-ended; any supplied date
    must use a real ISO calendar day. The end is exclusive and must follow start.
    """
    parsed = {}
    errors = []
    for key in ('effectiveDate', 'endDate'):
        value = version.get(key)
        if key == 'endDate' and (value is None or value == ''):
            continue
        try:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('invalid calendar date')
            parsed[key] = date.fromisoformat(value)
        except ValueError:
            errors.append('SELECTED_VERSION_DATE_INVALID:' + key)
    if 'effectiveDate' in parsed and 'endDate' in parsed and parsed['endDate'] <= parsed['effectiveDate']:
        errors.append('SELECTED_VERSION_DATE_RANGE_INVALID')
    return errors


def public_projection(knowledge, *, as_of):
    """Return {public, inventory}; only `public` may enter a future web bundle.

    `as_of` must be a date (no implicit frozen Gate date). Unknown/missing reviews
    fail closed. Invalid JSON or ambiguous identities abort the entire operation.
    This function does not write files or approve any knowledge.
    """
    if type(as_of) is not date:
        raise TypeError('as_of must be an explicit datetime.date')
    root = Path(knowledge)
    context = ProfileContext(root)
    profiles = _load_namespace(root, PROFILE_ROOT + '/records')
    reviews = _load_namespace(root, PROFILE_ROOT + '/reviews', True)
    gate = evaluate_release_gate(root, as_of)
    records, inventory = [], []
    for ident, profile in sorted(profiles.items()):
        errors = validate_profile(profile)
        if not errors:
            errors += _review_errors(profile, reviews.get(ident), context, as_of)
            if any(profile[k] == 'undetermined' for k in ('inspectionClass', 'defaultFieldEntry', 'contentDisposition')):
                errors.append('PROFILE_UNDETERMINED')
            if profile['hazardId'] not in gate.eligible_hazards:
                errors.append('SOURCE_HAZARD_GATE_FAILED')
            for link_id in profile['basisLinkIds']:
                link = context.entities['links'].get(link_id, {})
                if link_id not in gate.eligible_links or link.get('hazardId') != profile['hazardId'] or link.get('role') not in {'direct', 'fallback'}:
                    errors.append('SELECTED_BASIS_GATE_FAILED:' + link_id)
                clause = context.entities['clauses'].get(link.get('clauseId'), {})
                version = context.entities['law-versions'].get(clause.get('lawVersionId'))
                if version is not None:
                    errors += _selected_version_date_errors(version)
            # Missing dependency data is explicit, never implicitly approved.
            selected_dependencies = context.dependencies(profile, selected_only=True)
            errors += _selected_review_date_errors(selected_dependencies, as_of)
            if any(value is None for value in selected_dependencies.values()):
                errors.append('PROFILE_DEPENDENCY_MISSING')
        bases = []
        source_hazard = None
        if not errors:
            hazard = context.entities['hazards'][profile['hazardId']]
            source_hazard = {'id': hazard['id'], 'title': hazard['title'], 'conditions': hazard.get('conditions')}
            conditions = source_hazard['conditions']
            if not _text(source_hazard['title']) or (conditions is not None and not isinstance(conditions, str)) or PRIVATE.search(json.dumps(source_hazard, ensure_ascii=False)):
                errors.append('SOURCE_HAZARD_PUBLIC_TEXT_UNSAFE')
            for link_id in sorted(profile['basisLinkIds']):
                link = context.entities['links'][link_id]
                clause = context.entities['clauses'][link['clauseId']]
                version = context.entities['law-versions'][clause['lawVersionId']]
                law = context.entities['laws'][version['lawId']]
                # Preserve restrictions verbatim; never widen a local or specialist
                # basis by presenting only a generic profile title.
                basis = {'linkId': link_id, 'clauseId': clause['id'], 'role': link['role'],
                         'applicability': link['applicability'],
                         'jurisdictionCode': link.get('jurisdictionCode'),
                         'lawVersionId': version['id'], 'lawId': law['id'],
                         'lawJurisdictionCode': law['jurisdictionCode']}
                if not _text(basis['applicability']) or (basis['jurisdictionCode'] is not None and not _text(basis['jurisdictionCode'])) or not _text(basis['lawJurisdictionCode']) or PRIVATE.search(json.dumps(basis, ensure_ascii=False)):
                    errors.append('SELECTED_BASIS_PUBLIC_TEXT_UNSAFE:' + link_id)
                bases.append(basis)
        if errors:
            inventory.append({'profileId': ident, 'reasons': sorted(set(errors))})
            continue
        public = {key: copy.deepcopy(profile[key]) for key in sorted(FIELDS)}
        # Never claim an actual inspection occurred merely because its reusable
        # template passed review. Runtime facts belong to the individual use.
        public['sourceHazard'] = source_hazard
        public['bases'] = bases
        public['recordKind'] = 'reusable_field_profile'
        public['observedViolation'] = False
        records.append(public)
    covered = {p.get('hazardId') for p in profiles.values() if _ident(p.get('hazardId'))}
    missing = sorted(set(context.entities['hazards']) - covered)
    orphan = sorted(set(reviews) - set(profiles))
    return {'public': {'schemaVersion': SCHEMA_VERSION, 'asOf': as_of.isoformat(), 'records': records},
            'inventory': {'profileCount': len(profiles), 'publishedCount': len(records),
                          'excludedProfiles': inventory, 'hazardsWithoutProfiles': missing,
                          'orphanReviewIds': orphan}}
