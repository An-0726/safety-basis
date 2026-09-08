"""Single command for producing a reviewed, isolated website data bundle."""
import argparse
import json
from pathlib import Path
import sys

import publish


def main():
    if len(sys.argv)>1 and sys.argv[1]=='verify-site':
        import site_bundle
        parser=argparse.ArgumentParser(description='校验已生成的公开网站包，无需私有母库')
        parser.add_argument('command',choices=['verify-site'])
        parser.add_argument('--output',type=Path,required=True)
        args=parser.parse_args()
        print(json.dumps(site_bundle.verify_bundle(args.output),ensure_ascii=False,indent=2))
        return 0
    if len(sys.argv)<2 or sys.argv[1]!='site':
        return publish.main()
    import site_bundle
    parser=argparse.ArgumentParser(description='母库核验门禁 → 网站 JSON + 法规全文检索包；不部署')
    parser.add_argument('command',choices=['site'])
    parser.add_argument('--db',type=Path,default=publish.ROOT/'source/master/safety.sqlite3')
    parser.add_argument('--library',type=Path,default=publish.ROOT/'source/library')
    parser.add_argument('--checklist',type=Path,default=publish.ROOT/'source/master/fulltext-reviewed.json')
    parser.add_argument('--as-of',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--node',default='node')
    parser.add_argument('--baseline',type=Path,default=publish.ROOT/'data/search-index.json')
    args=parser.parse_args()
    try:
        result=site_bundle.build_site(args.db,args.library,args.checklist,args.as_of,args.output,node=args.node,baseline=args.baseline)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,TypeError,KeyError,OSError) as error:
        print(json.dumps({'ok':False,'error':str(error)},ensure_ascii=False))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
