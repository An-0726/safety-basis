#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, shutil, sqlite3
from pathlib import Path
from urllib.parse import urlsplit

CHECK_TYPES = {
    'law': 'identity',
    'law_version': 'version',
    'clause': 'text',
    'hazard': 'content',
    'link': 'applicability',
}
ENTITY_DIR = {
    'law': 'laws',
    'law_version': 'law-versions',
    'clause': 'clauses',
    'hazard': 'hazards',
    'link': 'links',
}
REVIEW_DIR = {
    'law': 'laws',
    'law_version': 'law-versions',
    'clause': 'clauses',
    'hazard': 'hazards',
    'link': 'links',
}
SAFE_ID = re.compile(r'^[A-Za-z0-9_.-]+$')


def jd(obj, *, pretty=True):
    if pretty:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def canonical_obj(obj):
    if isinstance(obj, dict):
        out = {}
        for k in sorted(obj):
            v = obj[k]
            if k in {'aliases','places','keywords'} and isinstance(v, list):
                v = sorted(v)
            out[k] = canonical_obj(v)
        return out
    if isinstance(obj, list):
        return [canonical_obj(v) for v in obj]
    return obj


def content_hash(obj):
    s = jd(canonical_obj(obj), pretty=False).encode('utf-8')
    return hashlib.sha256(s).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(jd(obj), encoding='utf-8')


def official_tier(url):
    if not url:
        return 'unclassified'
    try:
        host=(urlsplit(url).hostname or '').lower()
    except Exception:
        return 'unclassified'
    if host == 'gov.cn' or host.endswith('.gov.cn'):
        return 'authoritative-public'
    return 'secondary'


def normalize_validity(v):
    return {'现行有效':'active','即将生效':'upcoming','已废止':'repealed','失效':'repealed','待核验':'unknown','':'unknown',None:'unknown'}.get(v,'unknown')


def normalize_mode(v):
    return {'直接适用':'direct','条件适用':'conditional','上位法兜底':'fallback','':'unknown',None:'unknown'}.get(v,'unknown')


def normalize_role(v):
    v=v or ''
    if '候选' in v or v == 'primary' or not v:
        return 'unclassified'
    if '上位法' in v or '兜底' in v:
        return 'fallback'
    if '补充' in v:
        return 'supporting'
    if '直接' in v:
        return 'direct'
    return 'unclassified'


def latest_verifications(con):
    latest={}
    q='SELECT rowid,* FROM verification ORDER BY rowid'
    cols=['rowid']+[r[1] for r in con.execute('PRAGMA table_info(verification)')]
    for row in con.execute(q):
        d=dict(zip(cols,row))
        et=d['entity_type']; ct=d['check_type']
        if CHECK_TYPES.get(et)==ct:
            latest[(et,d['entity_id'])]=d
    details={}
    dcols=[r[1] for r in con.execute('PRAGMA table_info(verification_details)')]
    for row in con.execute('SELECT * FROM verification_details'):
        d=dict(zip(dcols,row)); details[d['verification_id']]=d
    return latest,details


def load_r10_ids(path):
    if not path: return {k:set() for k in ['hazards','laws','law_versions','clauses','links']}
    d=json.loads(Path(path).read_text(encoding='utf-8'))
    g=d['graph']
    return {k:{x['id'] for x in g.get(k,[])} for k in ['hazards','laws','law_versions','clauses','links']}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--r10')
    ap.add_argument('--out', required=True)
    ap.add_argument('--source-git-ref', required=True)
    ap.add_argument('--generated-at', required=True)
    args=ap.parse_args()
    db=Path(args.db); out=Path(args.out)
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    con=sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    con.row_factory=sqlite3.Row
    integ=con.execute('PRAGMA integrity_check').fetchone()[0]
    if integ!='ok': raise SystemExit(f'integrity_check failed: {integ}')
    dbsha=file_sha256(db)
    r10=load_r10_ids(args.r10)
    latest,details=latest_verifications(con)

    evid={}
    for r in con.execute('SELECT * FROM evidence ORDER BY id'):
        d=dict(r); tier=official_tier(d['official_url'])
        e={'id':d['id'],'tier':tier,'url':d['official_url'],'retrievedAt':d['retrieved_at'],'page':d['page'],'locator':d['locator']}
        if d['sha256']: e['snapshotSha256']=d['sha256']
        evid[d['id']]=e
        write_json(out/'knowledge'/'evidence'/f"{d['id']}.json", e)

    quarantine=[]; field_loss=[]; id_issues=[]
    entities={k:{} for k in ENTITY_DIR}

    aliases=collections.defaultdict(list)
    for r in con.execute('SELECT law_id,alias,ordinal FROM law_aliases ORDER BY law_id,ordinal'):
        aliases[r['law_id']].append(r['alias'])
    for r in con.execute('SELECT * FROM laws ORDER BY id'):
        d=dict(r)
        e={'id':d['id'],'canonicalName':d['canonical_name'],'issuer':d['issuer'],'jurisdictionCode':d['jurisdiction_code'],'documentKind':d['document_kind'],'identityKey':d['identity_key'],'aliases':aliases[d['id']], 'lifecycle':'merged' if d['identity_status']=='merged' else 'active'}
        entities['law'][d['id']]=e
        write_json(out/'knowledge'/'laws'/f"{d['id']}.json", e)
        field_loss.append({'entityType':'law','entityId':d['id'],'archivedPrivate':['checked','revision','legacy_payload','status'],'preserved':['id','canonical_name','issuer','jurisdiction_code','document_kind','identity_key','identity_status','law_aliases']})

    for r in con.execute('SELECT * FROM law_versions ORDER BY id'):
        d=dict(r); e={'id':d['id'],'lawId':d['law_id'],'versionKey':d['version_key'],'documentNumber':d['document_number'],'officialName':d['official_name'],'level':d['level'],'scope':d['scope'],'effectiveDate':d['effective_date'],'endDate':d['end_date'],'validityStatus':normalize_validity(d['validity_status']),'sourceUrl':d['source_url']}
        entities['law_version'][d['id']]=e; write_json(out/'knowledge'/'law-versions'/f"{d['id']}.json",e)
        if e['validityStatus']=='unknown' or not e['effectiveDate']:
            quarantine.append({'entityType':'law_version','entityId':d['id'],'reasonCode':'VERSION_EFFECTIVITY_UNCERTAIN','action':'migrate_as_pending'})

    loc_groups=collections.defaultdict(list)
    for r in con.execute('SELECT * FROM clauses ORDER BY id'):
        d=dict(r); e={'id':d['id'],'lawVersionId':d['law_version_id'],'articlePath':d['article_path'],'quote':d['quote'],'sourceUrl':d['source_url'],'lifecycle':'active'}
        entities['clause'][d['id']]=e; write_json(out/'knowledge'/'clauses'/f"{d['id']}.json",e)
        loc_groups[(d['law_version_id'],d['article_path'])].append(d['id'])
    for key,ids in loc_groups.items():
        if len(ids)>1:
            quotes={entities['clause'][i]['quote'] for i in ids}
            if len(quotes)>1:
                quarantine.append({'entityType':'clause','entityId':ids[0],'relatedIds':ids[1:],'reasonCode':'CLAUSE_LOCATOR_CONFLICT','action':'migrate_as_pending'})

    tags=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in con.execute('SELECT * FROM hazard_tags ORDER BY hazard_id,kind,ordinal'):
        tags[r['hazard_id']][r['kind']].append(r['value'])
    for r in con.execute('SELECT * FROM hazards ORDER BY id'):
        d=dict(r); lifecycle='merged' if d['merged_into'] else 'active'
        e={'id':d['id'],'title':d['title'],'description':d['description'],'measures':d['measures'],'category':d['category'],'conditions':d['conditions'],'note':d['note'],'mode':normalize_mode(d['mode']),'lifecycle':lifecycle,'mergedInto':d['merged_into'],'aliases':tags[d['id']].get('aliase',[]),'places':tags[d['id']].get('place',[]),'keywords':tags[d['id']].get('keyword',[])}
        entities['hazard'][d['id']]=e; write_json(out/'knowledge'/'hazards'/f"{d['id']}.json",e)

    link_legacy={}
    for r in con.execute('SELECT * FROM links ORDER BY id'):
        d=dict(r); role=normalize_role(d['role']); lifecycle='inactive' if d['status']=='已失效' else 'active'
        e={'id':d['id'],'hazardId':d['hazard_id'],'clauseId':d['clause_id'],'role':role,'legacyRole':d['role'],'priority':d['priority'],'applicability':d['applicability'],'jurisdictionCode':d['jurisdiction_code'],'lifecycle':lifecycle}
        entities['link'][d['id']]=e; link_legacy[d['id']]=d
        write_json(out/'knowledge'/'links'/f"{d['id']}.json",e)
        if lifecycle=='active' and role=='unclassified':
            quarantine.append({'entityType':'link','entityId':d['id'],'reasonCode':'ROLE_UNCLASSIFIED','legacyRole':d['role'],'action':'migrate_as_pending'})

    succ=[]
    for idx,r in enumerate(con.execute('SELECT * FROM law_successions ORDER BY old_version_id,new_version_id,relation'),1):
        d=dict(r); rel={'replaced_by':'replaces','partial_replaced_by':'partially_replaces'}.get(d['relation'],d['relation'])
        raw=f"{d['old_version_id']}|{d['new_version_id']}|{d['relation']}|{d['scope'] or ''}|{d['effective_date'] or ''}"
        sid='LS_'+hashlib.sha256(raw.encode()).hexdigest()[:24]
        e={'id':sid,'oldVersionId':d['old_version_id'],'newVersionId':d['new_version_id'],'relation':rel,'legacyRelation':d['relation'],'scope':d['scope'],'effectiveDate':d['effective_date']}
        succ.append(e); write_json(out/'knowledge'/'successions'/f'{sid}.json',e)

    review_counts=collections.Counter(); review_reasons=collections.Counter()
    verified_ids=collections.defaultdict(set)
    for et,emap in entities.items():
        for eid,e in emap.items():
            v=latest.get((et,eid)); detail=details.get(v['id']) if v else None
            decision='pending'; reasons=[]
            evidence_refs=[]
            if v and v['evidence_id']:
                evidence_refs=[v['evidence_id']]
            ev_tier=evid.get(v['evidence_id'],{}).get('tier') if v and v['evidence_id'] else None
            if not v: reasons.append('NO_CURRENT_V3_REVIEW')
            elif v['result']!='passed': reasons.append('V3_REVIEW_NOT_PASSED')
            else:
                if et=='law':
                    src=con.execute('SELECT identity_status FROM laws WHERE id=?',(eid,)).fetchone()
                    if src and src[0]=='confirmed' and ev_tier=='authoritative-public': decision='verified'
                    else: reasons.append('LAW_IDENTITY_OR_EVIDENCE_NOT_STRONG_ENOUGH')
                elif et=='law_version':
                    if e['validityStatus'] in {'active','upcoming'} and e['effectiveDate'] and ev_tier=='authoritative-public': decision='verified'
                    else: reasons.append('VERSION_EFFECTIVITY_OR_EVIDENCE_NOT_STRONG_ENOUGH')
                elif et=='clause':
                    src=con.execute('SELECT status,identity_status FROM clauses WHERE id=?',(eid,)).fetchone()
                    if src and src[0]=='已核验' and src[1]=='confirmed_locator' and ev_tier=='authoritative-public' and (detail or {}).get('locator'):
                        decision='verified'
                    else: reasons.append('CLAUSE_TEXT_REVIEW_NOT_STRONG_ENOUGH')
                elif et=='hazard':
                    src=con.execute('SELECT status FROM hazards WHERE id=?',(eid,)).fetchone()
                    pfr=(detail or {}).get('public_fields_reviewed')
                    if src and src[0]=='已核验' and pfr==1 and e['lifecycle']=='active': decision='verified'
                    else: reasons.append('HAZARD_PUBLIC_REVIEW_NOT_STRONG_ENOUGH')
                elif et=='link':
                    src=link_legacy[eid]
                    trusted_release = eid in r10['links']
                    if src['status']=='已核验' and e['lifecycle']=='active' and e['role'] in {'direct','supporting','fallback'} and v['reason'] and trusted_release:
                        decision='verified'
                    else:
                        reasons.append('LINK_NOT_CORROBORATED_FOR_AUTO_VERIFY')
                        if src['status']=='已失效': reasons.append('LINK_INACTIVE')
                        if e['role']=='unclassified': reasons.append('ROLE_UNCLASSIFIED')
                        if not trusted_release: reasons.append('NOT_IN_R10_CORROBORATION_SET')
            if e.get('lifecycle')=='merged':
                decision='superseded'; reasons=['ENTITY_MERGED']
            if et=='link' and e.get('lifecycle')=='inactive':
                decision='superseded'; reasons=['LINK_INACTIVE']
            rev={'entityType':et,'entityId':eid,'reviewType':CHECK_TYPES[et],'decision':decision,'reviewedContentHash':content_hash(e)}
            if evidence_refs: rev['evidenceRefs']=evidence_refs
            if reasons: rev['reasonCodes']=reasons
            if v:
                rev['migratedFromV3Verification']={'id':v['id'],'reviewedAt':v['checked_at'],'reviewer':v['reviewer'],'method':v['method']}
            if et=='link':
                hz=entities['hazard'].get(e['hazardId']); cl=entities['clause'].get(e['clauseId'])
                if hz and cl:
                    rev['contextHashes']={'hazard':content_hash(hz),'clause':content_hash(cl)}
            write_json(out/'knowledge'/'reviews'/REVIEW_DIR[et]/f'{eid}.json',rev)
            review_counts[(et,decision)]+=1
            if decision=='verified': verified_ids[et].add(eid)
            review_reasons.update(reasons)

    for et,emap in entities.items():
        for eid,e in emap.items():
            if not SAFE_ID.match(eid): id_issues.append({'type':'UNSAFE_ID','entityType':et,'id':eid})
    for vid,e in entities['law_version'].items():
        if e['lawId'] not in entities['law']: id_issues.append({'type':'BROKEN_FK','entityType':'law_version','id':vid,'field':'lawId','target':e['lawId']})
    for cid,e in entities['clause'].items():
        if e['lawVersionId'] not in entities['law_version']: id_issues.append({'type':'BROKEN_FK','entityType':'clause','id':cid,'field':'lawVersionId','target':e['lawVersionId']})
    for lid,e in entities['link'].items():
        if e['hazardId'] not in entities['hazard']: id_issues.append({'type':'BROKEN_FK','entityType':'link','id':lid,'field':'hazardId','target':e['hazardId']})
        if e['clauseId'] not in entities['clause']: id_issues.append({'type':'BROKEN_FK','entityType':'link','id':lid,'field':'clauseId','target':e['clauseId']})

    asof=args.generated_at[:10]
    current_versions=set()
    for vid in verified_ids['law_version']:
        e=entities['law_version'][vid]
        if e['validityStatus']=='active' and e['effectiveDate'] and e['effectiveDate']<=asof and (not e['endDate'] or e['endDate']>=asof):
            current_versions.add(vid)
    current_clauses={cid for cid in verified_ids['clause'] if entities['clause'][cid]['lawVersionId'] in current_versions}
    qualifying_links={lid for lid in verified_ids['link'] if entities['link'][lid]['role'] in {'direct','fallback'} and entities['link'][lid]['clauseId'] in current_clauses}
    eligible_hazards={entities['link'][lid]['hazardId'] for lid in qualifying_links if entities['link'][lid]['hazardId'] in verified_ids['hazard']}
    eligible_laws={entities['law_version'][vid]['lawId'] for vid in current_versions if entities['law_version'][vid]['lawId'] in verified_ids['law']}

    qdir=out/'quarantine'
    for i,q in enumerate(quarantine,1): write_json(qdir/f'{i:04d}-{q["entityType"]}-{q["entityId"]}.json',q)

    counts={tbl:con.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0] for tbl in ['laws','law_versions','clauses','hazards','links','evidence','verification','sources','source_rows','law_successions']}
    schema_row=con.execute("SELECT value FROM meta WHERE key='schemaVersion'").fetchone()
    manifest={
        'formatVersion':'safety-v3-v4-migration-v1','sourceDatabaseSha256':dbsha,
        'sourceSchemaVersion':int(schema_row[0]) if schema_row else None,
        'sourceGitRef':args.source_git_ref,'generatedAt':args.generated_at,'integrityCheck':integ,
        'sourceCounts':counts,
        'migratedCounts':{'laws':len(entities['law']),'lawVersions':len(entities['law_version']),'clauses':len(entities['clause']),'hazards':len(entities['hazard']),'links':len(entities['link']),'evidence':len(evid),'successions':len(succ)},
        'verifiedCandidates':{k:len(v) for k,v in verified_ids.items()},
        'eligibleComparisonSubset':{'laws':len(eligible_laws),'law_versions':len(current_versions),'clauses':len(current_clauses),'links':len(verified_ids['link']),'hazards':len(eligible_hazards)},
        'quarantined':len(quarantine),'idIssues':len(id_issues),
        'rulesVersion':'MIGRATION_V3_TO_V4.md@11b6f65f7e8004a2fcdcde2ed7f506dcf929d38e',
    }
    if args.r10:
        rd=json.loads(Path(args.r10).read_text(encoding='utf-8')); manifest['r10ReleaseHash']=rd.get('releaseHash')
    write_json(out/'migration-manifest.json',manifest)
    write_json(out/'reports'/'id-issues.json',id_issues)
    write_json(out/'reports'/'field-preservation-sample.json',field_loss[:25])
    write_json(out/'reports'/'review-summary.json',{'counts':{f'{k[0]}:{k[1]}':v for k,v in sorted(review_counts.items())},'reasonCounts':dict(sorted(review_reasons.items()))})
    comparison={k:{'v4Eligible':len(x),'r10':len(r10[k])} for k,x in [('laws',eligible_laws),('law_versions',current_versions),('clauses',current_clauses),('links',verified_ids['link']),('hazards',eligible_hazards)]}
    write_json(out/'reports'/'r10-count-comparison.json',comparison)

    files=[]
    for p in sorted((out/'knowledge').rglob('*.json')):
        files.append((str(p.relative_to(out)).replace(os.sep,'/'),file_sha256(p)))
    for p in sorted((out/'quarantine').rglob('*.json')) if (out/'quarantine').exists() else []:
        files.append((str(p.relative_to(out)).replace(os.sep,'/'),file_sha256(p)))
    tree_hash=hashlib.sha256('\n'.join(f'{a} {b}' for a,b in files).encode()).hexdigest()
    write_json(out/'reports'/'tree-hash.json',{'algorithm':'sha256(path + fileSha256)','fileCount':len(files),'treeHash':tree_hash})
    print(jd({'manifest':manifest,'treeHash':tree_hash,'reviewCounts':{f'{k[0]}:{k[1]}':v for k,v in sorted(review_counts.items())},'comparison':comparison}))


if __name__=='__main__': main()
