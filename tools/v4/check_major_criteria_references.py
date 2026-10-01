"""Validate reference-only inputs without approving them or claiming coverage."""
import argparse
from pathlib import Path
from major_criteria_references import load_records, dependencies, _metadata_errors

ROOT = Path(__file__).resolve().parents[2]


def validate_namespace(knowledge, publication):
    records = load_records(knowledge)
    errors = []
    for record in records.values():
        deps = dependencies(record, knowledge, publication)
        errors += [record['id'] + ':' + e for e in _metadata_errors(record, deps)
                   if e != 'REFERENCE_DEPENDENCY_MISSING']
        # Missing reviews are valid pending work, but missing canonical entities/evidence are not.
        errors += [record['id'] + ':REFERENCE_DEPENDENCY_MISSING:' + key
                   for key, value in deps.items() if value is None and not key.startswith('reviews/')]
    return {'referenceCount': len(records), 'errors': sorted(set(errors))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--knowledge', type=Path, default=ROOT / 'knowledge')
    parser.add_argument('--publication', type=Path, default=ROOT / 'source/publication')
    args = parser.parse_args(argv)
    try:
        result = validate_namespace(args.knowledge, args.publication)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print('major criteria references errors: 1 (' + str(exc) + ')')
        return 1
    print('major criteria references:', result['referenceCount'], 'errors:', len(result['errors']))
    for error in result['errors']:
        print(' -', error)
    print('Reference metadata/short-topic validation is not normative or field approval.')
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
