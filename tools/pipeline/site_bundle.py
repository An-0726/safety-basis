"""Build an isolated website data bundle and reviewed full-text library together."""
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import tempfile

import exchange
import master
import public_fulltext
import publish
import review

SITE_ASSETS = ('index.html', 'library.html', 'style.css', 'library.css', 'app.js',
               'sw.js', 'icon.svg', 'manifest.webmanifest', 'js/store.js', 'js/search.js',
               'js/library.js', 'js/fulltext-search.js', 'js/verified-files.js')


def verify_bundle(output):
    """Validate a committed public package without opening the private master."""
    root=Path(output).resolve()
    read=lambda name:json.loads((root/name).read_text(encoding='utf-8'))
    checksums=read('checksums.json')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='checksums.json'}
    if set(checksums)!=actual:
        raise ValueError('发布包文件集合与校验清单不一致')
    for name,expected in checksums.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or exchange.sha256_bytes(path.read_bytes())!=expected:
            raise ValueError('发布包文件哈希不匹配：'+name)
        if name not in {*SITE_ASSETS,'release.json','site-manifest.json'} and not (name.startswith('data/') and name.endswith('.json')):
            raise ValueError('发布包含非公开文件：'+name)
    release=publish.validate_release(read('release.json'))
    publish.check_runtime(root,release)
    manifest=read('site-manifest.json')
    wanted={name:sha for name,sha in checksums.items() if name.startswith('data/')}
    if manifest.get('fileHashes')!=wanted or manifest.get('releaseHash')!=release['releaseHash']:
        raise ValueError('网站清单与发布版本不一致')
    catalog=read('data/fulltext/catalog.json')
    allowed={row['id'] for row in release['graph']['law_versions']}
    if any(doc['versionId'] not in allowed for doc in catalog['documents']):
        raise ValueError('全文目录包含未通过核验的法规版本')
    return {'ok':True,'files':len(actual)+1,'releaseHash':release['releaseHash'],
            'fullTextCount':manifest['fullTextCount'],'officialLinkCount':manifest['officialLinkCount']}


def fingerprint(db):
    with closing(master.connect_readonly(db)) as conn:
        conn.execute('BEGIN')
        return exchange.state_hash(conn)


def build_site(db, library, checklist, as_of, output, *, node='node', baseline=None):
    output=Path(output).resolve()
    if output.exists():
        raise ValueError('输出必须是新目录')
    report_path=output.with_name(output.name+'.review.json')
    exchange.check_output(report_path,'.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    release, report=publish.prepare(db,as_of,baseline=baseline)
    with tempfile.TemporaryDirectory(prefix='safety-site-',dir=output.parent) as scratch_name:
        scratch=Path(scratch_name).resolve()
        full=scratch/'fulltext'
        ft=public_fulltext.export_public(db,library,checklist,as_of,full)
        if fingerprint(db)!=release['sourceStateHash']:
            raise ValueError('母库在构建过程中发生变化，拒绝混合版本发布')
        built=publish.build(release,scratch/'bundle',node=node)
        bundle=scratch/'bundle'
        catalog=json.loads((full/'catalog.json').read_text(encoding='utf-8'))
        allowed={row['id'] for row in release['graph']['law_versions']}
        if any(doc['versionId'] not in allowed for doc in catalog['documents']):
            raise ValueError('全文目录包含未通过网站法规门禁的版本')
        shutil.copytree(full,bundle/'data/fulltext')
        site_manifest={'schemaVersion':'safety-site-bundle-v1','asOf':as_of,'releaseHash':release['releaseHash'],
                       'fullTextCatalog':'data/fulltext/catalog.json',
                       'fullTextCount':sum(d['textMode']=='full_text' for d in catalog['documents']),
                       'officialLinkCount':sum(d['textMode']=='link_only' for d in catalog['documents'])}
        site_manifest['fileHashes']={p.relative_to(bundle).as_posix():exchange.sha256_bytes(p.read_bytes())
                                    for p in sorted((bundle/'data').rglob('*.json'))}
        (bundle/'site-manifest.json').write_text(json.dumps(site_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for asset in SITE_ASSETS:
            target=bundle/asset
            target.parent.mkdir(parents=True,exist_ok=True)
            # All allowlisted assets are UTF-8 text; keep builds identical on Windows/Linux.
            target.write_bytes((publish.ROOT/asset).read_text(encoding='utf-8').encode('utf-8'))
        checksums={p.relative_to(bundle).as_posix():exchange.sha256_bytes(p.read_bytes())
                   for p in sorted(bundle.rglob('*')) if p.is_file() and p.name!='checksums.json'}
        (bundle/'checksums.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        report['fullText']=json.loads((scratch/'fulltext.blockers.json').read_text(encoding='utf-8'))
        report['fullText']['publicCount']=ft['publicCount']
        # Private reasons remain beside the package, never under its data/.
        review.write_json(report_path,report)
        if output.exists():
            raise ValueError('输出目录已被其他操作创建')
        os.rename(bundle,output)
    return {**built,'output':str(output),'fullTextCount':site_manifest['fullTextCount'],
            'officialLinkCount':site_manifest['officialLinkCount'],'fullTextBlocked':ft['blockedCount'],
            'reviewReport':str(report_path),'deployed':False,
            'requiresPublicationReview':report['requiresPublicationReview']}
