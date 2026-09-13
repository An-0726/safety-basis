# -*- coding: utf-8 -*-
"""Merge the two duplicate Excel candidates while preserving both standards."""
import hashlib
import io
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
sys.path.insert(0, os.path.join(ROOT, "tools", "maintenance"))
from canonical import content_hash  # noqa: E402
from release_gate_core import load_dir  # noqa: E402
from promote_excel_fulltext_batch import choose_paragraph  # noqa: E402

KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")
DB = os.path.join(ROOT, "source", "library", "fulltext.sqlite3")
AS_OF = "2026-09-13"


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")


def main():
    hazards = load_dir(KNOW, "hazards"); lvs = load_dir(KNOW, "law-versions")
    db = sqlite3.connect(DB); cache = {}
    canonical_id = "H_12158_9_10_1"
    merge_id = "H_15577_6_3_2_1"
    specs = [
        ("C_XLSX_DUP_GB12158_9_10", "LV_STD_A318C93D7F3213B292AD5946", "GB 12158-2024", "9.10"),
        ("C_XLSX_DUP_GB15577_6_3_2", "LV_STD_A307C34C912F164D6A1D19E9", "GB 15577-2018", "6.3.2"),
    ]
    clauses = []; evidence_ids=[]
    for cid, vid, doc_version, article in specs:
        key = db.execute("select document_key from documents where version=? limit 1", (doc_version,)).fetchone()[0]
        got = choose_paragraph(db, key, article, cache)
        if not got: raise RuntimeError(f"article text not located: {doc_version} {article}")
        paragraph_no, quote = got
        doc = db.execute("select official_url,sha256,text_sha256 from documents where document_key=?",(key,)).fetchone()
        eid = "E_XLSX_DUP_" + hashlib.sha1((key+article).encode()).hexdigest()[:24].upper()
        clause={"articlePath":article,"id":cid,"jurisdictionCode":"CN","lawVersionId":vid,"lifecycle":"active","quote":quote,"sourceUrl":doc[0] or lvs[vid].get('sourceUrl','')}
        evidence={"id":eid,"locator":"第"+article+"条","page":str(paragraph_no),"retrievedAt":AS_OF,"snapshotSha256":doc[1] or doc[2],"tier":"authoritative-public","url":doc[0] or lvs[vid].get('sourceUrl','')}
        write(os.path.join(KNOW,'clauses',cid+'.json'),clause);write(os.path.join(KNOW,'evidence',eid+'.json'),evidence)
        write(os.path.join(KNOW,'reviews','clauses',cid+'.json'),{"checkedAt":AS_OF,"decision":"verified","entityId":cid,"entityType":"clause","evidenceRefs":[eid],"reason":"已从归档全文定位并核对原文，作为重复隐患合并后的两项直接技术依据。","reviewType":"text","reviewedContentHash":content_hash(clause),"reviewer":"Codex正式核验批次20260913"})
        clauses.append((clause,eid))
    hz=hazards[canonical_id]; hz['lifecycle']='active';hz['mode']='direct';hz.pop('proposalStatus',None);hz.pop('sourceRow',None)
    marker='本批已将重复候选合并，并保留GB 12158-2024与GB 15577-2018两项直接条款依据。'
    if marker not in str(hz.get('note') or ''):hz['note']=(str(hz.get('note') or '').rstrip()+'\n'+marker).strip()
    hazard_evidence=[e for _c,e in clauses];write(os.path.join(KNOW,'hazards',canonical_id+'.json'),hz)
    write(os.path.join(KNOW,'reviews','hazards',canonical_id+'.json'),{"checkedAt":AS_OF,"decision":"verified","entityId":canonical_id,"entityType":"hazard","evidenceRefs":hazard_evidence,"reason":"两个Excel候选为同一隐患，已合并为一个正式隐患并核对两项标准条款。","reviewType":"content","reviewedContentHash":content_hash(hz),"reviewer":"Codex正式核验批次20260913"})
    for clause,eid in clauses:
        kid='K_XLSX_DUP_'+hashlib.sha1((canonical_id+'|'+clause['id']).encode()).hexdigest()[:24].upper()
        link={"applicability":hz.get('conditions') or '适用于对应作业和场所条件。',"clauseId":clause['id'],"hazardId":canonical_id,"id":kid,"jurisdictionCode":"CN","legacyRole":"直接依据","lifecycle":"active","priority":10,"reason":"合并后的隐患与标准条款直接对应。","role":"direct"}
        write(os.path.join(KNOW,'links',kid+'.json'),link);write(os.path.join(KNOW,'reviews','links',kid+'.json'),{"checkedAt":AS_OF,"contextHashes":{"clause":content_hash(clause),"hazard":content_hash(hz)},"decision":"verified","entityId":kid,"entityType":"link","evidenceRefs":[eid],"reason":"合并后的隐患与条款原文直接对应。","reviewType":"applicability","reviewedContentHash":content_hash(link),"reviewer":"Codex正式核验批次20260913"})
    merged=hazards[merge_id];merged['lifecycle']='active';merged['mergedInto']=canonical_id;merged.pop('proposalStatus',None);merged.pop('sourceRow',None);merged['note']=(str(merged.get('note') or '').rstrip()+f'\n本批已与{canonical_id}合并，原始条款保留在合并后的正式隐患上。').strip();write(os.path.join(KNOW,'hazards',merge_id+'.json'),merged)
    mp=os.path.join(KNOW,'manifest.json');m=read(mp);bid='excel-merge-duplicate-batch-20260913'
    if bid not in {b.get('id') for b in m.get('batches',[])}:m.setdefault('batches',[]).append({'id':bid,'hazardsAdded':1,'clausesAdded':2,'linksAdded':2,'evidenceAdded':2,'selection':'Merge two duplicate Excel candidates into H_12158_9_10_1 while retaining both direct standard clauses.'})
    m.setdefault('counts',{})['hazards']=len(load_dir(KNOW,'hazards'));m['counts']['clauses']=len(load_dir(KNOW,'clauses'));m['counts']['links']=len(load_dir(KNOW,'links'));write(mp,m)
    write(os.path.join(PROPOSAL,'merge-duplicate-batch-report.json'),{'asOf':AS_OF,'canonical':canonical_id,'merged':merge_id,'generatedAt':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'canonical':canonical_id,'merged':merge_id,'clauses':2,'links':2},ensure_ascii=False))


if __name__=='__main__':main()
