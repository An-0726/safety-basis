"""Structural checks for isolated official-source reading; never text approval."""
import argparse
from pathlib import Path
from major_criteria_reading import load_records, dependencies
import major_criteria_directory as directory
ROOT = Path(__file__).resolve().parents[2]


def validate_namespace(knowledge, publication):
    records=load_records(knowledge); source=directory.load_records(knowledge); groups=directory.relationships(source)
    errors=[]
    for row in records.values():
        members=groups.get(row['directoryGroupId'],[])
        if {r['id'] for r in members} != set(row['requiredReferenceIds']):
            errors.append(row['id']+':READING_DIRECTORY_MEMBERSHIP')
        deps=dependencies(row,knowledge,publication)
        for key,value in deps.items():
            if value is None and not any(marker in key for marker in ('text-reviews/','directory-reviews/','/reviews/')):
                errors.append(row['id']+':READING_DEPENDENCY_MISSING:'+key)
    return {'groupCount':len(records),'documentCount':sum(len(r['documents']) for r in records.values()),'errors':sorted(set(errors))}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--knowledge',type=Path,default=ROOT/'knowledge');p.add_argument('--publication',type=Path,default=ROOT/'source/publication');args=p.parse_args(argv)
    try:result=validate_namespace(args.knowledge,args.publication)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print('major criteria reading errors: 1 ('+str(exc)+')');return 1
    print('major criteria reading groups:',result['groupCount'],'documents:',result['documentCount'],'errors:',len(result['errors']))
    for error in result['errors']:print(' -',error)
    print('Source structure is not text/rights approval and never current determination eligibility.')
    return int(bool(result['errors']))


if __name__=='__main__':raise SystemExit(main())
