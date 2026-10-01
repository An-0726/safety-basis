"""Structural checks for separately reviewed official metadata directory."""
import argparse
from pathlib import Path
from major_criteria_directory import load_records, relationships, dependencies, _metadata_errors
from field_profiles import ProfileContext
ROOT = Path(__file__).resolve().parents[2]


def validate_namespace(knowledge, publication):
    records = load_records(knowledge)
    groups = relationships(records)
    context = ProfileContext(knowledge) if records else None
    errors = []
    for row in records.values():
        deps = dependencies(row, knowledge, publication, context=context)
        errors += [row['id'] + ':' + e for e in _metadata_errors(row, deps) if e != 'DIRECTORY_DEPENDENCY_MISSING']
        errors += [row['id'] + ':DIRECTORY_DEPENDENCY_MISSING:' + key for key,value in deps.items()
                   if value is None and '/reviews/' not in '/' + key]
    return {'groupCount': len(groups), 'documentCount': len(records), 'errors': sorted(set(errors))}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--knowledge',type=Path,default=ROOT/'knowledge')
    parser.add_argument('--publication',type=Path,default=ROOT/'source/publication')
    args=parser.parse_args(argv)
    try:
        result=validate_namespace(args.knowledge,args.publication)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print('major criteria directory errors: 1 ('+str(exc)+')');return 1
    print('major criteria directory groups:',result['groupCount'],'documents:',result['documentCount'],'errors:',len(result['errors']))
    for error in result['errors']:print(' -',error)
    print('Metadata validation does not approve clauses, field findings or all-industry coverage.')
    return int(bool(result['errors']))


if __name__=='__main__':
    raise SystemExit(main())
