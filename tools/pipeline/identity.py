"""Reviewed law-family merges preserving version IDs, clauses and old identities.

Only different, non-conflicting versions can be moved by this operation.
Duplicate versions require a separate clause/relationship reconciliation.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path

import admission
import catalog
import exchange
import master
import verification

FORMAT = 'law-identity-merge-v1'
AMEND_FORMAT = 'law-identity-amend-v1'
IDENTITY_FIELDS = {'canonical_name', 'issuer', 'jurisdiction_code', 'document_kind'}


def amendment_payload(conn, law_id, changes, evidence_id, reason):
    """Correct family identity fields without inheriting a previous passed review."""
    if (not isinstance(changes, dict) or not changes or not set(changes) <= IDENTITY_FIELDS
            or any(not isinstance(value, str) or not value.strip() for value in changes.values())
            or not isinstance(reason, str) or not reason.strip()):
        raise ValueError('身份修订需要明确字段、非空值及审阅理由；不能修改状态或ID')
    row = conn.execute('SELECT * FROM laws WHERE id=?', (law_id,)).fetchone()
    if not row or row['identity_status'] == 'merged' or row['status'] in ('已失效', '已废止'):
        raise ValueError('法规身份不存在或已关闭')
    evidence = conn.execute('SELECT * FROM evidence WHERE id=?', (evidence_id,)).fetchone()
    if not evidence or not verification.official_url(evidence['official_url']):
        raise ValueError('身份修订需要已登记的官方证据')
    before = dict(row)
    changes = {key: value.strip() for key, value in changes.items()}
    if all(before[key] == value for key, value in changes.items()):
        raise ValueError('没有身份字段变化')
    after = {**before, **changes}
    after.update(identity_key=catalog._identity_key(after), identity_status='provisional',
                 status='待核验', checked='', revision=before['revision'] + 1)
    if conn.execute('SELECT id FROM laws WHERE identity_key=? AND id<>?', (after['identity_key'], law_id)).fetchone():
        raise ValueError('修订后与已有法规身份冲突，应使用身份合并审查')
    return {'formatVersion': AMEND_FORMAT, 'kind': 'law-identity-amend',
            'baseStateHash': exchange.state_hash(conn), 'lawId': law_id, 'changes': changes,
            'before': before, 'after': after, 'evidenceId': evidence_id, 'reason': reason.strip()}


def propose_amendment(db, law_id, changes, evidence_id, reason, output):
    with closing(admission.open_db(db)) as conn:
        exchange.check_integrity(conn)
        proposal = admission.seal(amendment_payload(conn, law_id, changes, evidence_id, reason))
        admission.write_json(output, proposal)
        return {'ok': True, 'proposalId': proposal['proposalId'], 'lawId': law_id,
                'requiresIdentityAndDependentVersionReview': True}


def apply_amendment(db, proposal_file, actor):
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError('操作者不能为空')
    proposal = json.loads(Path(proposal_file).read_text(encoding='utf-8-sig'))
    original = {k: value for k, value in proposal.items() if k not in ('proposalId', 'proposalHash')}
    if (admission.seal(original) != proposal or original.get('formatVersion') != AMEND_FORMAT
            or original.get('kind') != 'law-identity-amend'):
        raise ValueError('身份修订提案格式或哈希无效')
    with closing(admission.open_db(db, write=True)) as conn:
        try:
            if exchange.has_table(conn, 'law_identity_amendments'):
                previous = conn.execute('SELECT receipt_json FROM law_identity_amendments WHERE id=?', (proposal['proposalId'],)).fetchone()
                if previous:
                    conn.rollback()
                    return {**json.loads(previous[0]), 'status': 'already_applied'}
            current = amendment_payload(conn, original['lawId'], original['changes'], original['evidenceId'], original['reason'])
            if current != original:
                raise ValueError('母库已变化或提案内容被修改，拒绝身份修订')
            evidence = conn.execute('SELECT snapshot_ref,sha256 FROM evidence WHERE id=?', (original['evidenceId'],)).fetchone()
            snapshot = Path(db).resolve().parent / evidence['snapshot_ref']
            if not snapshot.is_file() or exchange.sha256_bytes(snapshot.read_bytes()) != evidence['sha256']:
                raise ValueError('证据原件缺失或损坏')
            conn.execute('CREATE TABLE IF NOT EXISTS law_identity_amendments(id TEXT PRIMARY KEY,law_id TEXT NOT NULL REFERENCES laws(id),proposal_json TEXT NOT NULL,receipt_json TEXT NOT NULL,created_at TEXT NOT NULL,actor TEXT NOT NULL)')
            for action in ('UPDATE', 'DELETE'):
                conn.execute(f"CREATE TRIGGER IF NOT EXISTS law_identity_amendments_no_{action.lower()} BEFORE {action} ON law_identity_amendments BEGIN SELECT RAISE(ABORT,'law identity amendments are append-only'); END")
            fields = sorted(IDENTITY_FIELDS | {'identity_key', 'identity_status', 'status', 'checked', 'revision'})
            conn.execute('UPDATE laws SET ' + ','.join(f'{field}=?' for field in fields) + ' WHERE id=?',
                         [original['after'][field] for field in fields] + [original['lawId']])
            result = {'ok': True, 'status': 'applied', 'proposalId': proposal['proposalId'],
                      'lawId': original['lawId'], 'requiresIdentityAndDependentVersionReview': True,
                      'resultStateHash': exchange.state_hash(conn)}
            conn.execute('INSERT INTO law_identity_amendments VALUES(?,?,?,?,?,?)',
                         (proposal['proposalId'], original['lawId'], master.dumps(proposal), master.dumps(result), master.now(), actor))
            exchange.check_integrity(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def payload(conn, source, target, evidence_id, reason):
    if source == target or not reason.strip():
        raise ValueError('必须指定不同法规身份及合并理由')
    source_law = conn.execute('SELECT * FROM laws WHERE id=?', (source,)).fetchone()
    target_law = conn.execute('SELECT * FROM laws WHERE id=?', (target,)).fetchone()
    if not source_law or not target_law:
        raise ValueError('法规身份不存在')
    if any(r['identity_status'] == 'merged' or r['status'] in ('已失效', '已废止') for r in (source_law, target_law)):
        raise ValueError('已关闭或已合并的法规不能再次合并')
    evidence = conn.execute('SELECT * FROM evidence WHERE id=?', (evidence_id,)).fetchone()
    if not evidence or not verification.official_url(evidence['official_url']):
        raise ValueError('法规身份合并需要已登记的官方证据')
    moving = [dict(r) for r in conn.execute('SELECT * FROM law_versions WHERE law_id=? ORDER BY id', (source,))]
    existing = [dict(r) for r in conn.execute('SELECT * FROM law_versions WHERE law_id=? ORDER BY id', (target,))]
    for version in moving:
        for other in existing:
            if version['version_key'] == other['version_key'] or (
                version['document_number'] and version['document_number'] == other['document_number']
            ) or (version['effective_date'] and version['effective_date'] == other['effective_date']):
                raise ValueError('版本键、文号或实施日期冲突；需先完成版本与条款对账')
    aliases = sorted({source_law['canonical_name']} | {r[0] for r in conn.execute('SELECT alias FROM law_aliases WHERE law_id=?', (source,))})
    return {'formatVersion':FORMAT,'kind':'law-identity-merge','baseStateHash':exchange.state_hash(conn),
            'sourceLaw':dict(source_law),'targetLaw':dict(target_law),'versions':moving,
            'targetVersions':existing,'aliases':aliases,'evidenceId':evidence_id,'reason':reason.strip()}


def propose(db, source, target, evidence_id, reason, output):
    with closing(admission.open_db(db)) as conn:
        exchange.check_integrity(conn)
        proposal = admission.seal(payload(conn, source, target, evidence_id, reason))
        admission.write_json(output, proposal)
        return {'ok':True,'proposalId':proposal['proposalId'],'movingVersions':len(proposal['versions'])}


def apply(db, proposal_file, actor):
    if not actor.strip():
        raise ValueError('操作者不能为空')
    proposal = json.loads(Path(proposal_file).read_text(encoding='utf-8-sig'))
    original = {k:v for k,v in proposal.items() if k not in ('proposalId','proposalHash')}
    if admission.seal(original) != proposal:
        raise ValueError('提案哈希无效')
    if original.get('formatVersion') != FORMAT or original.get('kind') != 'law-identity-merge':
        raise ValueError('不是法规身份合并提案')
    with closing(admission.open_db(db, write=True)) as conn:
        try:
            if exchange.has_table(conn, 'law_identity_actions'):
                previous = conn.execute('SELECT receipt_json FROM law_identity_actions WHERE id=?', (proposal['proposalId'],)).fetchone()
                if previous:
                    conn.rollback()
                    return {**json.loads(previous[0]),'status':'already_applied'}
            source, target = original['sourceLaw']['id'], original['targetLaw']['id']
            current = payload(conn, source, target, original['evidenceId'], original['reason'])
            if current != original:
                raise ValueError('母库已变化或提案内容被修改，拒绝合并')
            evidence = conn.execute('SELECT snapshot_ref,sha256 FROM evidence WHERE id=?', (original['evidenceId'],)).fetchone()
            snapshot = Path(db).resolve().parent/evidence['snapshot_ref']
            if not snapshot.is_file() or exchange.sha256_bytes(snapshot.read_bytes()) != evidence['sha256']:
                raise ValueError('证据原件缺失或损坏')
            conn.execute('CREATE TABLE IF NOT EXISTS law_identity_actions(id TEXT PRIMARY KEY,source_law_id TEXT NOT NULL REFERENCES laws(id),target_law_id TEXT NOT NULL REFERENCES laws(id),proposal_json TEXT NOT NULL,receipt_json TEXT NOT NULL,created_at TEXT NOT NULL,actor TEXT NOT NULL)')
            for action in ('UPDATE','DELETE'):
                conn.execute(f"CREATE TRIGGER IF NOT EXISTS law_identity_no_{action.lower()} BEFORE {action} ON law_identity_actions BEGIN SELECT RAISE(ABORT,'law identity actions are append-only'); END")
            conn.execute("UPDATE laws SET identity_status='merged',status='已失效',checked='',revision=revision+1 WHERE id=?", (source,))
            conn.execute("UPDATE laws SET identity_status='provisional',status='待核验',checked='',revision=revision+1 WHERE id=?", (target,))
            for version in original['versions']:
                status = '已失效' if version['review_status'] == '已失效' else '待核验'
                conn.execute('UPDATE law_versions SET law_id=?,review_status=?,checked=?,revision=revision+1 WHERE id=?', (target,status,'',version['id']))
            present = {r[0] for r in conn.execute('SELECT alias FROM law_aliases WHERE law_id=?',(target,))}
            ordinal = conn.execute('SELECT COALESCE(MAX(ordinal),-1)+1 FROM law_aliases WHERE law_id=?',(target,)).fetchone()[0]
            for alias in original['aliases']:
                if alias not in present and alias != original['targetLaw']['canonical_name']:
                    conn.execute('INSERT INTO law_aliases VALUES(?,?,?)', (target,alias,ordinal))
                    ordinal += 1
            result={'ok':True,'status':'applied','proposalId':proposal['proposalId'],'sourceLawId':source,
                    'targetLawId':target,'preservedVersionIds':[r['id'] for r in original['versions']],
                    'resultStateHash':exchange.state_hash(conn)}
            conn.execute('INSERT INTO law_identity_actions VALUES(?,?,?,?,?,?,?)',
                         (proposal['proposalId'],source,target,master.dumps(proposal),master.dumps(result),master.now(),actor))
            exchange.check_integrity(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    plan=commands.add_parser('propose')
    for name in ('source','target','evidence','reason'):
        plan.add_argument('--'+name,required=True)
    plan.add_argument('--output',type=Path,required=True)
    amend=commands.add_parser('amend', help='有官方证据的身份字段修订；修订后重新核验')
    for name in ('law','evidence','reason'):
        amend.add_argument('--'+name,required=True)
    amend.add_argument('--changes',type=Path,required=True)
    amend.add_argument('--output',type=Path,required=True)
    commit=commands.add_parser('apply')
    commit.add_argument('--proposal',type=Path,required=True)
    commit.add_argument('--actor',required=True)
    args=parser.parse_args()
    if args.command=='propose':
        result=propose(args.db,args.source,args.target,args.evidence,args.reason,args.output)
    elif args.command=='amend':
        changes=json.loads(args.changes.read_text(encoding='utf-8-sig'))
        result=propose_amendment(args.db,args.law,changes,args.evidence,args.reason,args.output)
    elif json.loads(args.proposal.read_text(encoding='utf-8-sig')).get('formatVersion')==AMEND_FORMAT:
        result=apply_amendment(args.db,args.proposal,args.actor)
    else:
        result=apply(args.db,args.proposal,args.actor)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
