"""Additional source-pinned GB50054/JGJ91/JS30 browser checks, no browser launch."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from repair_acceptance import DOM_SNAPSHOT, require, require_text, validate_rendered_detail, validate_release_match

FIXTURE_PATH=Path(__file__).parent/'fixtures/technical_citations_20261003.json'
EXPECTED_IDS={'H057','H056','H_FE6C8CE7D9D74815847BCF72A7','H_B57B762BDB8149F4BACB629CFF','H_7A03BD4501C948B78EA50A2733','H_701AAE9385E74703A71396776E','H061','H_462D38828DEBA46C8E23C177D2_1','H_462D38828DEBA46C8E23C177D2_2','H_462D38828DEBA46C8E23C177D2_3'}
CORE_BASIS_KEYS=('linkId','clauseId','lawId','lawName','role','applicability','article','quote','sourceUrl','jurisdictionCode','clauseRegion','lawRegion')

def load_expectations(path=FIXTURE_PATH):
    f=json.loads(Path(path).read_text());validate_expectations(f);return f

def validate_expectations(f):
    require(f.get('schemaVersion')=='public-technical-browser-v1','Unknown technical browser fixture')
    rows=f.get('records',[])
    require(len(rows)==10 and {r['id'] for r in rows}==EXPECTED_IDS,'Technical/JS30 identity set drift')
    require(sum(len(r['bases']) for r in rows)==13,'Technical/JS30 basis set drift')
    require(f.get('excludedPublicClauseId')=='C_JGJ91_10_2_7','Buried-clause exclusion drift')
    for row in rows:
        require(all(row['hazard'].get(k) for k in ('title','description','conditions','measures','category','places')),'Missing hazard expectation')
        require(f'knowledge/hazards/{row["id"]}.json' in f['sourceFiles'],'Missing hazard pin')
        for b in row['bases']:
            require(set(b)==set(CORE_BASIS_KEYS),'Basis expectation schema drift')
            require(b['clauseId']!=f['excludedPublicClauseId'],'Wrong buried clause remains a public basis')
            for kind,ident in [('links',b['linkId']),('clauses',b['clauseId']),('law-versions',b['lawId'])]:
                require(f'knowledge/{kind}/{ident}.json' in f['sourceFiles'],'Missing exact source pin')
    require(f['expectedMajorAssociation']['jurisdictionCode']=='CN','H061 national major geography changed')
    require(f['expectedMajorAssociation']['linkId']=='K_7634A863A8C4CBA1D77F3A30','H061 national major identity changed')
    return rows

def validate_source_pins(f,root):
    validate_expectations(f)
    for path,want in f['sourceFiles'].items():
        require(hashlib.sha256((Path(root)/path).read_bytes()).hexdigest()==want,'Technical source drift: '+path)
    path=Path(root)/'tools/pipeline/tests/fixtures/public_technical_citations_20261003.json'
    require(hashlib.sha256(path.read_bytes()).hexdigest()==f['sourceReviewFixtureSha256'],'Technical review fixture drift')
    return {'sourceFiles':len(f['sourceFiles']),'hazards':10,'basisLinks':13}

def validate_rendered(expected,actual):
    result=validate_rendered_detail(expected,actual)
    by_id={b['linkId']:b for b in actual['bases']}
    for b in expected['bases']:
        parts=by_id[b['linkId']]['metadataText'].split('·')
        require(len(parts)==3,'Rendered law metadata shape differs: '+b['linkId'])
        require_text(parts[1],b['lawRegion'],'Rendered law region: '+b['linkId'])
    result['sourceLinksAndLawRegionsExact']=True
    return result

def validate_projection(f,actual,*,public_inventory=None):
    inventory=public_inventory or {'majorHazards':f['expectedMajorHazardCount'],'profiles':f['expectedProfiles']}
    require(len(actual['details'])==10 and len({r['id'] for r in actual['details']})==10,'Missing/duplicate hydrated technical detail')
    got={r['id']:r for r in actual['details']}
    require(set(got)==EXPECTED_IDS,'Hydrated technical identities differ')
    for row in f['records']:
        for k,v in row['hazard'].items():require(got[row['id']]['hazard'].get(k)==v,'Hydrated hazard field drift: '+row['id']+':'+k)
        require(sorted(got[row['id']]['bases'],key=lambda b:b['linkId'])==sorted(row['bases'],key=lambda b:b['linkId']),'Hydrated exact basis or geography differs: '+row['id'])
    require(f['excludedPublicClauseId'] not in actual['jgjLawClauseIds'],'Buried clause still used in current research-building catalogue')
    require(actual['majorAssociations']==[f['expectedMajorAssociation']],'H061 national major association changed')
    require(actual['majorHazardCount']==inventory['majorHazards'],'Major hazard membership changed')
    require(actual['profileCount']==inventory['profiles'],'Profile count changed')
    return {'hazards':10,'basisLinks':13,'sharedJS30Region':'CN-32 / 江苏','H061MajorRegion':'CN','correctedQuoteAndSourceIdentity':True}

HYDRATE=r'''async ids => {
 const {DataStore}=await import('./js/store.js'); const store=await new DataStore('.').init(),details=[];
 for(const id of ids){
  const index=store.searchIndex.find(h=>h.id===id);if(!index)throw Error('Missing '+id);
  const d=await store.getHazardDetail(index);
  details.push({id,hazard:d.hazard,bases:d.bases.map(b=>({linkId:b.ref.linkId,clauseId:b.clause.id,
   lawId:b.law.id,lawName:b.law.name,role:b.ref.role,applicability:b.ref.applicability,
   article:b.clause.article,quote:b.clause.quote,sourceUrl:b.sourceUrl,jurisdictionCode:b.ref.jurisdictionCode??null,
   clauseRegion:b.clause.region,lawRegion:b.law.scope}))});
 }
 const law=await store.getLawDetail(store.lawIndex.find(l=>l.id==='LV_STD_JGJ91_2019'));
 const fetchJson=async p=>{const r=await fetch(p,{cache:'no-store'});if(!r.ok)throw Error(p);return await r.json();};
 const topic=await fetchJson('./data/major-criteria-topic.json'),profiles=await fetchJson('./data/field-profiles.json');
 return {releaseHash:store.manifest.releaseHash,details,jgjLawClauseIds:law.clauses.map(c=>c.clause.id),
  majorAssociations:topic.associations.filter(a=>a.hazardId==='H061'),majorHazardCount:topic.hazardIds.length,profileCount:profiles.records.length};
}'''


def run_technical_browser_acceptance(browser,base,run,page_errors,expect,fixture,release_hash,*,public_inventory=None):
    """Use the existing CI browser; preserve every previous acceptance check."""
    rows=validate_expectations(fixture)
    def public_check():
        context=browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
        try:
            page=context.new_page();page.on('pageerror',lambda err:page_errors.append(str(err)))
            page.goto(base,wait_until='domcontentloaded');page.wait_for_selector('#detail h2')
            actual=page.evaluate(HYDRATE,[r['id'] for r in rows]);validate_release_match(actual['releaseHash'],release_hash)
            return validate_projection(fixture,actual,public_inventory=public_inventory)
        finally:context.close()
    run('technical_citations_exact_source_projection_and_JS30_regions',public_check)
    for width in (1440,375,390,485):
        context=browser.new_context(viewport={'width':width,'height':1000},is_mobile=width<=780,has_touch=width<=780,service_workers='block')
        try:
            page=context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda err:page_errors.append(str(err)))
            for row in rows:
                def render_one(row=row):
                    page.goto(base+'?id='+quote(row['id'])+'&q='+quote(row['hazard']['title']),wait_until='domcontentloaded')
                    expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                    page.locator('#list .card[data-id="'+row['id']+'"]').click()
                    actual=page.evaluate(DOM_SNAPSHOT)
                    metadata=page.locator('#detail .basis[data-link-id]').evaluate_all('(rows)=>Object.fromEntries(rows.map(b=>[b.dataset.linkId,b.querySelector(".basismeta > span.article").innerText]))')
                    for b in actual['bases']:b['metadataText']=metadata[b['linkId']]
                    result=validate_rendered(row,actual)
                    page.wait_for_function('''narrow=>{const h=document.querySelector('header').getBoundingClientRect(),t=document.querySelector('#detail h2').getBoundingClientRect();return t.top>=h.bottom-1&&(!narrow||t.bottom<=innerHeight)&&document.documentElement.scrollWidth<=innerWidth+1;}''',arg=width<=780)
                    page.reload(wait_until='domcontentloaded');expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                    require(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Technical detail overflows after reload')
                    result.update(width=width,reload=True);return result
                run(f'technical_detail_{width}px_{row["id"]}',render_one)
            def major_check():
                page.goto(base+'major-criteria.html?view=hazards&standard=L019&q='+quote('承包'),wait_until='domcontentloaded')
                card=page.locator('.hazard-card').filter(has=page.locator('h3 a[href="./?id=H061"]'))
                expect(card).to_have_count(1)
                text=card.inner_text();require('工贸企业重大事故隐患判定标准' in text,'H061 national major card missing')
                require('江苏省安全生产条例' not in text,'JS30 leaked into national major card')
                require(fixture['expectedMajorAssociation']['applicability'] in text,'H061 major trigger display changed')
                require(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Major page overflow')
                return {'width':width,'hazardId':'H061','selectedNationalBasisPreserved':True,'JS30NotMajorCriterion':True}
            run(f'JS30_H061_national_major_preserved_{width}px',major_check)
        finally:context.close()
