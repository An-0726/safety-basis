"""Copy only public application source and verified law assets to a Site checkout.

The Sites identity is created by the hosting connector and must already exist.
This command never copies workbench runtime, company data, credentials, or Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    target = args.site.resolve()
    bundle = args.bundle.resolve()
    identity = target / '.openai/hosting.json'
    config = json.loads(identity.read_text())
    if not config.get('project_id') or config.get('d1') != 'DB' or config.get('r2') != 'BUCKET' or config.get('static'):
        raise ValueError('Register a private Worker Site with DB and BUCKET first')
    if target == ROOT or ROOT in target.parents or target in ROOT.parents:
        raise ValueError('Use a separate Site checkout outside the GitHub repository')
    ignore = shutil.ignore_patterns('node_modules', 'dist', '.git', '.openai', '.wrangler', '.sites-runtime',
                                    '__pycache__', '*.pyc', '*.sqlite*', '*.db', '.env*', '.dev.vars*', 'generated', 'outputs')
    for relative in ('workbench/cloud', 'workbench/frontend', 'workbench/templates', 'web/js'):
        shutil.copytree(ROOT / relative, target / relative, dirs_exist_ok=True, ignore=ignore)
    public = target / 'public-knowledge'
    manifest = json.loads((bundle / 'site-manifest.json').read_text())
    if manifest.get('schemaVersion') != 'safety-site-bundle-v1':
        raise ValueError('A verified public bundle is required')
    public.mkdir(exist_ok=True)
    for name, expected in manifest['fileHashes'].items():
        if not name.startswith('data/') or '..' in Path(name).parts or not name.endswith('.json'):
            raise ValueError('Unsafe knowledge asset')
        data = (bundle / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Knowledge asset hash mismatch: ' + name)
        destination = public / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    shutil.copy2(bundle / 'site-manifest.json', public / 'site-manifest.json')
    shutil.copytree(ROOT / 'workbench/cloud/migrations', target / 'drizzle', dirs_exist_ok=True)
    package = json.loads((ROOT / 'workbench/cloud/package.json').read_text())
    package['scripts'] = {
        'dev': 'node workbench/cloud/preview.mjs',
        'build': 'node workbench/cloud/build.mjs --bundle public-knowledge --output dist --hosting .openai/hosting.json',
        'test': 'WORKBENCH_BUNDLE=public-knowledge node --test workbench/cloud/tests/*.test.mjs',
    }
    (target / 'package.json').write_text(json.dumps(package, ensure_ascii=False, indent=2) + '\n')
    shutil.copy2(ROOT / 'workbench/cloud/package-lock.json', target / 'package-lock.json')
    (target / '.gitignore').write_text('node_modules/\ndist/\n.wrangler/\n.sites-runtime/\noutputs/\n*.sqlite*\n*.db\n.env*\n.dev.vars*\n')
    print(json.dumps({'site_checkout': str(target), 'public_law_assets': len(manifest['fileHashes']),
                      'private_data_copied': False}))


if __name__ == '__main__':
    main()
