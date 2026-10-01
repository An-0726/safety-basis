"""Structural controlled-catalog validation, never semantic approval/coverage."""
import argparse
from pathlib import Path

from field_profiles import ProfileContext
from major_criteria import load_config, _chain

ROOT = Path(__file__).resolve().parents[2]


def validate_namespace(knowledge):
    config, context = load_config(knowledge), ProfileContext(knowledge)
    errors = []
    for standard in config['standards']:
        vid = standard['lawVersionId']
        version = context.entities['law-versions'].get(vid)
        if version is None or version.get('lawId') != standard['identity']['lawId']:
            errors.append('MAJOR_VERSION_REFERENCE:' + vid)
        for selected in standard['clauses']:
            cid = selected['clauseId']
            clause = context.entities['clauses'].get(cid)
            if clause is None or clause.get('lawVersionId') != vid:
                errors.append('MAJOR_CLAUSE_REFERENCE:' + cid)
            for key, value in _chain(context, 'clauses', cid).items():
                if value is None and not key.startswith('reviews/'):
                    errors.append('MAJOR_DEPENDENCY_MISSING:' + key)
        for selected in standard['topicLinks'] + standard['pendingTopicLinks']:
            kid = selected['linkId']
            link = context.entities['links'].get(kid)
            if (link is None or link.get('hazardId') != selected['hazardId'] or
                    link.get('clauseId') != selected['clauseId'] or
                    selected['hazardId'] not in context.entities['hazards'] or
                    context.entities['clauses'].get(selected['clauseId'], {}).get('lawVersionId') != vid):
                errors.append('MAJOR_TOPIC_REFERENCE:' + kid)
    return {'standardCount': len(config['standards']), 'errors': sorted(set(errors))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--knowledge', type=Path, default=ROOT / 'knowledge')
    args = parser.parse_args(argv)
    try:
        result = validate_namespace(args.knowledge)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print('major criteria errors: 1 (' + str(exc) + ')')
        return 1
    print('major criteria standards:', result['standardCount'], 'errors:', len(result['errors']))
    for error in result['errors']:
        print(' -', error)
    print('Structural validation does not certify semantic approval or complete coverage.')
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
