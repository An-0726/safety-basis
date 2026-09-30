"""Explicit real-pilot automated checks. Public synthetic tests are not acceptance."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--knowledge',type=Path,default=ROOT/'knowledge',
                        help='Restored project knowledge directory (no synthetic fallback)')
    args=parser.parse_args()
    expected={f'FP_P{i:02}' for i in range(1,19)}|{f'FP_N{i:02}' for i in range(1,7)}
    folder=args.knowledge/'field-profiles-pilot'
    try:
        records=[json.loads(p.read_text(encoding='utf-8')) for p in (folder/'records').glob('*.json')]
        evidence=list((folder/'evidence').glob('*.json'))
        if len(records)!=24 or {r['id'] for r in records}!=expected or len(evidence)!=18:
            raise ValueError('Required private overlay: 24 real FP records and 18 evidence records')
        if args.knowledge.resolve()!=(ROOT/'knowledge').resolve():
            raise ValueError('Restore verified overlay into this project before running real-case tests')
    except (ValueError,KeyError,OSError) as exc:
        print(json.dumps({'status':'NOT_ACCEPTED','reason':str(exc)},ensure_ascii=False))
        return 2
    commands=[['node','--test','tests/private/field-pilot-search.acceptance.mjs'],
              [sys.executable,'tools/pipeline/acceptance/field_profiles_pilot_acceptance.py']]
    for command in commands:
        result=subprocess.run(command,cwd=ROOT)
        if result.returncode:
            print(json.dumps({'status':'NOT_ACCEPTED','failedCommand':command}))
            return result.returncode
    print(json.dumps({'status':'AUTOMATED_CHECKS_PASSED','finalAcceptance':False,
                      'note':'R2 evidence review, checklist and real browser search still required'}))
    return 0


if __name__=='__main__':raise SystemExit(main())
