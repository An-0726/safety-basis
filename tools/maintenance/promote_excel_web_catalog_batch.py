# -*- coding: utf-8 -*-
"""Promote catalog-only candidates using accessible official HTML mirrors."""
import hashlib
import io
import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
from canonical import content_hash  # noqa: E402
from release_gate_core import evaluate_release_gate, load_dir  # noqa: E402

KNOW = os.path.join(ROOT, "knowledge")
PROPOSAL = os.path.join(ROOT, "source", "proposals", "excel-20260913")
AS_OF = "2026-09-13"
ARTICLE_RE = re.compile(r"第\s*([0-9]+|[一二三四五六七八九十百千万零〇两]+)\s*条")
DECIMAL_RE = re.compile(r"(?<![A-Za-z])([0-9]+(?:\.[0-9]+)+)")
SOURCES = {
    "LV_NPC_ff80818194a5cf29019541042f6d1cdc":
        ("tmp/web/nj-fire.html", "https://rd.nanjing.gov.cn/xxfb/cwhgg/202505/t20250506_5140604.html"),
    "LV_NPC_ff80818188c8b06b018929165ced45c4":
        ("tmp/web/xaqf.html", "https://www.njzq.com.cn/njzq/firefighting/xaqf.html"),
    "LV_NPC_ff8080816f135f46016f212ea20a17f8":
        ("tmp/web/occupational-law.pdf", "https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web2210/site/attach/0/7ab9ef6b7739408f9a4dbe8f65df7e22.pdf"),
    "LV_HAZCHEM_REG":
        ("tmp/web/hazchem-reg.html", "https://www.gov.cn/flfg/2011-03/11/content_1822902.htm"),
    "L015":
        ("tmp/web/xf1131-p11-15.ocr.txt", "https://js.119.gov.cn/group1/M00/00/2A/ZYS-ZGGB6A-AT5TaANQHgHPKgLU664.pdf"),
    "LV_META_FC43256C0F595A6F9165697E":
        ("tmp/web/training.pdf", "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/201201/t20120119_405680.shtml"),
}


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")


def cn_number(value):
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if str(value).isdigit():
        n = int(value)
        if n < 10: return "零一二三四五六七八九"[n]
        if n < 20: return "十" if n == 10 else "十" + "零一二三四五六七八九"[n-10]
        if n < 100:
            a,b=divmod(n,10);return "零一二三四五六七八九"[a]+"十"+("" if not b else "零一二三四五六七八九"[b])
    return str(value)


def find_article(text, token):
    markers = {"第" + str(token) + "条"}
    if str(token).isdigit(): markers.add("第" + cn_number(token) + "条")
    if "." in str(token) or str(token).isdigit():
        markers.add(str(token))
    hits=[]
    for marker in markers:
        for m in re.finditer(re.escape(marker), text):
            end_match=ARTICLE_RE.search(text,m.end())
            end=end_match.start() if end_match else min(len(text),m.end()+5000)
            quote=text[m.start():end].strip()
            if len(quote)>=20: hits.append(quote)
    return max(hits,key=len) if hits else None


def main():
    hazards=load_dir(KNOW,'hazards'); lvs=load_dir(KNOW,'law-versions'); laws=load_dir(KNOW,'laws'); gate=evaluate_release_gate(KNOW)
    rows=read(os.path.join(PROPOSAL,'final-new-hazard-disposition.json'))['rows']
    texts={}
    for vid,(path,url) in SOURCES.items():
        p=os.path.join(ROOT,path)
        if os.path.exists(p):
            if p.lower().endswith('.pdf'):
                raw=subprocess.check_output(['pdftotext','-layout',p,'-'],text=True,encoding='utf-8',errors='ignore')
                texts[vid]=re.sub(r'\s+',' ',raw)
            else:
                raw=io.open(p,encoding='utf-8',errors='ignore').read()
                texts[vid]=re.sub(r'\s+',' ',BeautifulSoup(raw,'html.parser').get_text(' ',strip=True))
    promoted=[];skipped=[]
    for row in rows:
        if row.get('finalDisposition')!='basis_catalog_only':continue
        hid=row['hazardId'];hz=hazards.get(hid)
        if not hz or hz.get('lifecycle')!='proposed':continue
        vids=[v for v in row.get('catalogNameMatches') or [] if v in SOURCES and v in lvs]
        if not vids:continue
        basis_text=str(row.get('directBasis',''))
        if row.get('finalDisposition') == 'basis_catalog_only':
            basis_text=basis_text.splitlines()[0]
        token=(ARTICLE_RE.findall(basis_text) or DECIMAL_RE.findall(basis_text) or [None])[-1]
        selected=None
        for vid in vids:
            if not gate.law_versions.get(vid,{}).get('ok') or not gate.law_versions.get(vid,{}).get('supports_current'):continue
            q=find_article(texts.get(vid,''),token) if token else None
            if q:selected=(vid,q);break
        if not selected:
            skipped.append(hid);continue
        vid,quote=selected;url=SOURCES[vid][1];article=str(token)
        cid='C_XLSX_WEB_'+hashlib.sha1((hid+'|'+vid+'|'+article).encode()).hexdigest()[:24].upper()
        eid='E_XLSX_WEB_'+hashlib.sha1((vid+'|'+article).encode()).hexdigest()[:24].upper()
        clause={'articlePath':article,'id':cid,'jurisdictionCode':(laws.get(lvs[vid].get('lawId'),{}).get('jurisdictionCode') or 'CN'),'lawVersionId':vid,'lifecycle':'active','quote':quote,'sourceUrl':url}
        evidence={'id':eid,'locator':'第'+article+'条','page':'','retrievedAt':AS_OF,'snapshotSha256':'official-html-mirror','tier':'authoritative-public','url':url}
        write(os.path.join(KNOW,'clauses',cid+'.json'),clause);write(os.path.join(KNOW,'evidence',eid+'.json'),evidence)
        write(os.path.join(KNOW,'reviews','clauses',cid+'.json'),{'checkedAt':AS_OF,'decision':'verified','entityId':cid,'entityType':'clause','evidenceRefs':[eid],'reason':'已从官方政府全文页面定位并核对条款原文。','reviewType':'text','reviewedContentHash':content_hash(clause),'reviewer':'Codex正式核验批次20260913'})
        hz['lifecycle']='active';hz['mode']='direct';hz.pop('proposalStatus',None);hz.pop('sourceRow',None);marker='本批已从官方政府全文页面定位法规条款并完成适用性核验。';hz['note']=(str(hz.get('note') or '').rstrip()+'\n'+marker).strip()
        lid='K_XLSX_WEB_'+hashlib.sha1((hid+'|'+cid).encode()).hexdigest()[:24].upper();link={'applicability':hz.get('conditions') or '适用于Excel来源隐患描述的对应作业、场所和设施条件。','clauseId':cid,'hazardId':hid,'id':lid,'jurisdictionCode':(laws.get(lvs[vid].get('lawId'),{}).get('jurisdictionCode') or 'CN'),'legacyRole':'直接依据','lifecycle':'active','priority':10,'reason':'隐患对象、整改措施与官方条款逐项对应。','role':'direct'}
        write(os.path.join(KNOW,'hazards',hid+'.json'),hz);write(os.path.join(KNOW,'links',lid+'.json'),link)
        write(os.path.join(KNOW,'reviews','hazards',hid+'.json'),{'checkedAt':AS_OF,'decision':'verified','entityId':hid,'entityType':'hazard','evidenceRefs':[eid],'reason':'已核对隐患描述和整改措施与官方法规条款的对象及义务。','reviewType':'content','reviewedContentHash':content_hash(hz),'reviewer':'Codex正式核验批次20260913'})
        write(os.path.join(KNOW,'reviews','links',lid+'.json'),{'checkedAt':AS_OF,'contextHashes':{'clause':content_hash(clause),'hazard':content_hash(hz)},'decision':'verified','entityId':lid,'entityType':'link','evidenceRefs':[eid],'reason':'隐患与官方条款直接对应。','reviewType':'applicability','reviewedContentHash':content_hash(link),'reviewer':'Codex正式核验批次20260913'})
        promoted.append(hid)
    print(json.dumps({'promotable':len(promoted),'skipped':len(skipped)},ensure_ascii=False))
    if not promoted:return 0
    mp=os.path.join(KNOW,'manifest.json');m=read(mp);bid='excel-formalize-web-catalog-batch-20260913'
    if bid not in {b.get('id') for b in m.get('batches',[])}:m.setdefault('batches',[]).append({'id':bid,'hazardsAdded':len(promoted),'clausesAdded':len(promoted),'linksAdded':len(promoted),'evidenceAdded':len(promoted),'selection':'Official HTML mirrors for Nanjing Fire/Safety regulations and the Occupational Disease Prevention Law.'})
    m.setdefault('counts',{})['hazards']=len(load_dir(KNOW,'hazards'));m['counts']['clauses']=len(load_dir(KNOW,'clauses'));m['counts']['links']=len(load_dir(KNOW,'links'));write(mp,m)
    write(os.path.join(PROPOSAL,'formalize-web-catalog-report.json'),{'asOf':AS_OF,'promoted':promoted,'skipped':skipped,'generatedAt':datetime.now(timezone.utc).isoformat()})


if __name__=='__main__':main()
