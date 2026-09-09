"""Prepare the selected reviewed website for hosting, without private inputs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from master import ROOT
import site_bundle
import verification


def prepare(selection, output, *, repository=ROOT, as_of=None):
    repository = Path(repository).resolve()
    config = json.loads(Path(selection).read_text(encoding='utf-8'))
    if (not isinstance(config, dict) or set(config) != {'schemaVersion', 'bundle', 'releaseHash'}
            or config['schemaVersion'] != 'safety-site-selection-v1'
            or not isinstance(config['bundle'], str)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]+', config['bundle'])):
        raise ValueError('网站发布选择格式无效；只能选择 releases 下的一个完整包')
    releases = repository / 'source/releases'
    source = (releases / config['bundle']).resolve()
    if not source.is_relative_to(releases.resolve()):
        raise ValueError('网站包超出 releases 目录')
    verified = site_bundle.verify_bundle(source)
    if verified['releaseHash'] != config['releaseHash']:
        raise ValueError('所选网站包 releaseHash 不匹配')
    release = json.loads((source / 'release.json').read_text(encoding='utf-8'))
    as_of = as_of or verification.business_date(datetime.now(timezone.utc)).isoformat()
    if verification.date(as_of) < verification.date(release['asOf']):
        raise ValueError('不能发布晚于当前基准日的网站包')
    proofs = {(row['entity_type'], row['entity_id']): row for row in release['proofs']}
    evidence = {row['id']: row for row in release['evidence']}
    gates = verification.gate(release['graph'], proofs, evidence, as_of)
    blocked = {group: sorted(ident for ident, reasons in rows.items() if reasons)
               for group, rows in gates.items() if any(rows.values())}
    if blocked:
        raise ValueError('所选包在发布当日存在过期或未通过门禁的内容，须从母库重新构建：'
                         + json.dumps(blocked, ensure_ascii=False))
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('托管输出必须是新目录')
    # Never put hosting output among originals or mutate the checked-in bundle.
    for protected in ('content', 'data', 'source', '.git'):
        if output.is_relative_to(repository / protected):
            raise ValueError('托管输出不能位于来源、母库、发布快照或现有运行数据目录内')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='safety-hosting-', dir=output.parent) as temporary:
        staged = Path(temporary) / 'site'
        shutil.copytree(source, staged)
        site_bundle.verify_bundle(staged)
        os.rename(staged, output)
    return {**verified, 'bundle': config['bundle'], 'output': str(output),
            'validatedAsOf': as_of, 'deployed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, default=ROOT / 'source/releases/site-selection.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.selection, args.output)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
