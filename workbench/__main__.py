"""python -m workbench [serve|prepare|demo|backup|restore|template]."""
import argparse
import json
import os
import subprocess
import sys
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def prepare(bundle, as_of=None):
    stamp = as_of or datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    bundle = Path(bundle).resolve()
    if bundle.exists():
        manifest = bundle / 'site-manifest.json'
        if not manifest.is_file() or json.loads(manifest.read_text(encoding='utf-8')).get('schemaVersion') != 'safety-site-bundle-v1':
            raise ValueError('目标目录已存在且不是可重建的正式知识包，请使用新的空路径')
    bundle.parent.mkdir(parents=True, exist_ok=True)
    releases = ROOT / 'source/releases'
    releases.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.workbench-build-', dir=releases) as temp, tempfile.TemporaryDirectory() as auxiliary:
        staged = Path(temp)
        subprocess.run([sys.executable, str(ROOT / 'tools/v4/build_unified_release.py'),
                        '--out', str(staged), '--as-of', stamp, '--overwrite'], cwd=ROOT, check=True)
        release = json.loads((staged / 'release.json').read_text(encoding='utf-8'))
        selection = Path(auxiliary) / 'site-selection.json'
        selection.write_text(json.dumps({'schemaVersion': 'safety-site-selection-v1',
                                        'bundle': staged.name, 'releaseHash': release['releaseHash']}), encoding='utf-8')
        subprocess.run([sys.executable, str(ROOT / 'tools/v4/verify_unified_bundle.py'),
                        '--bundle', str(staged), '--selection', str(selection)], cwd=ROOT, check=True)
        if bundle.parent != releases:
            candidate = bundle.with_name('.workbench-build-' + uuid.uuid4().hex)
            shutil.copytree(staged, candidate)
        else:
            candidate = staged
        previous = bundle.with_name('.workbench-previous-' + uuid.uuid4().hex)
        if bundle.exists():
            bundle.rename(previous)
        try:
            candidate.rename(bundle)
        except OSError:
            if previous.exists():
                previous.rename(bundle)
            raise
        if previous.exists():
            shutil.rmtree(previous)
        if bundle == releases / 'current':
            (releases / 'site-selection.json').write_text(json.dumps({
                'schemaVersion': 'safety-site-selection-v1', 'bundle': bundle.name,
                'releaseHash': release['releaseHash'],
            }, indent=2) + '\n', encoding='utf-8')
    print('已更新知识包；正在运行的工作台请重启：', bundle)


def main():
    parser = argparse.ArgumentParser(description='安全检查工作台：企业数据只保存在私有运行目录')
    parser.add_argument('command', nargs='?', default='serve', choices=['serve', 'prepare', 'demo', 'backup', 'restore', 'template'])
    parser.add_argument('file', nargs='?', help='恢复的 ZIP 文件或生成的 Word 模板文件')
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('WORKBENCH_DATA_DIR', Path.home() / '.safety-basis-workbench')))
    parser.add_argument('--bundle', type=Path, default=Path(os.environ.get('WORKBENCH_BUNDLE', ROOT / 'source/releases/current')))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--as-of', help='按 YYYY-MM-DD 构建知识快照，默认中国标准时间当天')
    parser.add_argument('--export', action='store_true', help='仅用于合成示例：模拟审核并导出报告')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.bundle, args.as_of)
        return
    if args.command == 'restore':
        from .backend.backup import restore_backup
        if not args.file:
            parser.error('restore 需要指定备份 ZIP 文件')
        print('已恢复到：', restore_backup(args.file, args.data_dir))
        return
    if args.command == 'template':
        from .backend.reporting import create_template
        target = Path(args.file) if args.file else args.data_dir / 'templates/inspection.docx'
        if target.exists():
            parser.error('目标模板已存在，请使用新文件名以保留原件')
        target.parent.mkdir(parents=True, exist_ok=True)
        create_template(target)
        print('可替换模板：', target)
        return
    if args.command == 'backup':
        from .backend.storage import Store
        from .backend.backup import create_backup
        if not (args.data_dir / 'workbench.sqlite3').is_file():
            parser.error('指定目录中没有工作台数据库')
        print(create_backup(Store(args.data_dir)))
        return
    if not (args.bundle / 'site-manifest.json').is_file():
        prepare(args.bundle, args.as_of)
    from .backend.app import create_app
    if args.command == 'demo':
        from fastapi.testclient import TestClient
        with TestClient(create_app(args.data_dir, args.bundle)) as client:
            result = client.post('/api/demo')
            result.raise_for_status()
            data = result.json()
            print('合成示例项目：', data['project']['id'])
            if args.export:
                fid = data['finding']['id']
                facts = [{**f, 'status': 'confirmed', 'note': '合成演示流程中的模拟核实，不代表真实现场结论'} for f in data['finding']['facts']]
                for url, body, method in [
                    (f'/api/findings/{fid}/facts', {'facts': facts}, 'put'),
                    (f'/api/findings/{fid}/review', {'decision': 'submit'}, 'post'),
                    (f'/api/findings/{fid}/review', {'decision': 'confirm', 'reviewer': '示例审核人', 'comment': '仅审核合成演示流程'}, 'post'),
                ]:
                    current = client.get(f'/api/findings/{fid}')
                    current.raise_for_status()
                    response = getattr(client, method)(url, json={**body, 'revision': current.json()['revision']})
                    response.raise_for_status()
                result = client.post(f'/api/projects/{data["project"]["id"]}/reports', json={'mode': 'confirmed'})
                result.raise_for_status()
                report = result.json()
                print('示例报告：', args.data_dir / 'reports' / report['id'])
                print('PDF引擎：', report['pdf_engine'])
            print('示例仍保存在该私有运行目录，启动服务即可查看。')
        return
    if args.host not in ('127.0.0.1', '::1', 'localhost') and not os.environ.get('WORKBENCH_ACCESS_TOKEN'):
        parser.error('远程监听请先设置 WORKBENCH_ACCESS_TOKEN，并使用 HTTPS 反向代理；本机使用无需配置')
    import uvicorn
    uvicorn.run(create_app(args.data_dir, args.bundle), host=args.host, port=args.port)


if __name__ == '__main__':
    main()
