"""Source-pinned author-rebuild browser contract. Imports no browser/launch code.
Run through the main required-CI browser harness after independent approval.
No claim of GUI execution is made by generating this module or its fixture.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from repair_acceptance import DOM_SNAPSHOT, require, validate_rendered_detail, validate_release_match

FIXTURE_PATH = Path(__file__).parent / 'fixtures/electrical_candidates_20261004.json'
EXPECTED_IDS = {'H_CF_GEN_13', 'H_GBT3787_PERIODIC_CHECK_MARK', 'H_JGJT46_2024_BOX_PE',
                'H_GB51251_MANUAL_SMOKE_WINDOW', 'H_GBT34525_CYLINDER_REGISTER',
                'H_GBT34525_CYLINDER_STORE_ALARM', 'H_89016FC0F3E849C2B8B8755C35'}
BASIS_KEYS = {'linkId','clauseId','lawId','lawName','role','applicability','article','quote','sourceUrl'}

def validate_expectations(f):
    require(f.get('schemaVersion') == 'electrical-rebuild-browser-v1', 'Electrical fixture schema drift')
    rows = f.get('records', [])
    require(len(rows) == 7 and {r['id'] for r in rows} == EXPECTED_IDS, 'Electrical identity set drift')
    require(sum(len(r['bases']) for r in rows) == 10, 'Electrical basis set drift')
    for row in rows:
        require(all(row['hazard'].get(k) for k in ('title','description','conditions','measures','category','places')), 'Incomplete H expectation')
        require(f'knowledge/hazards/{row["id"]}.json' in f['sourceFiles'], 'Missing H pin')
        for b in row['bases']:
            require(set(b) == BASIS_KEYS, 'Electrical basis schema drift')
            for group,key in (('links','linkId'),('clauses','clauseId'),('law-versions','lawId')):
                require(f'knowledge/{group}/{b[key]}.json' in f['sourceFiles'], 'Missing precise basis pin')
    return rows

def load_expectations(path=FIXTURE_PATH):
    f=json.loads(Path(path).read_text()); validate_expectations(f); return f

def validate_source_pins(f, root):
    validate_expectations(f)
    for rel,want in f['sourceFiles'].items():
        require(hashlib.sha256((Path(root)/rel).read_bytes()).hexdigest() == want, 'Electrical source drift: '+rel)
    return {'hazards':7, 'basisLinks':10, 'sourceFiles':len(f['sourceFiles'])}

def validate_projection(f, actual):
    rows = actual.get('details', [])
    require(len(rows) == len({x['id'] for x in rows}) == 7, 'Missing/duplicate hydrated electrical H')
    got = {x['id']:x for x in rows}
    require(set(got) == EXPECTED_IDS, 'Hydrated electrical identity drift')
    for want in f['records']:
        a=got[want['id']]
        for key,value in want['hazard'].items():
            require(a['hazard'].get(key) == value, f'Electrical H field mismatch: {want["id"]}:{key}')
        require(sorted(a['bases'],key=lambda b:b['linkId']) == sorted(want['bases'],key=lambda b:b['linkId']),
                'Electrical K/C/quote/scope/source mismatch: '+want['id'])
    return {'hazards':7,'basisLinks':10,'exactHydratedSourceProjection':True}

HYDRATE = r'''async ids => {
 const {DataStore}=await import('./js/store.js'); const store=await new DataStore('.').init(),details=[];
 for(const id of ids){const index=store.searchIndex.find(h=>h.id===id);if(!index)throw Error('Missing '+id);
 const d=await store.getHazardDetail(index);details.push({id,hazard:d.hazard,bases:d.bases.map(b=>({
 linkId:b.ref.linkId,clauseId:b.clause.id,lawId:b.law.id,lawName:b.law.name,role:b.ref.role,
 applicability:b.ref.applicability,article:b.clause.article,quote:b.clause.quote,sourceUrl:b.sourceUrl}))});}
 return {releaseHash:store.manifest.releaseHash,details};
}'''

def expected_clipboard(row):
    h=row['hazard']
    bases='\n\n'.join('《'+b['lawName']+'》'+b['article']+'\n本条依据适用范围：'+b['applicability']+'\n'+b['quote'] for b in row['bases'])
    return h['title']+'\n\n隐患专业描述：\n'+h['description']+'\n\n适用条件：\n'+h['conditions']+'\n\n法规依据：\n'+bases+'\n\n整改措施：\n'+h['measures']

def run_electrical_browser_acceptance(browser, base, run, page_errors, expect, fixture, release_hash):
    rows=validate_expectations(fixture)
    def projection():
        context=browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
        try:
            page=context.new_page();page.on('pageerror',lambda e:page_errors.append(str(e)))
            page.goto(base,wait_until='domcontentloaded');page.wait_for_selector('#detail h2')
            actual=page.evaluate(HYDRATE,[r['id'] for r in rows]);validate_release_match(actual['releaseHash'],release_hash)
            return validate_projection(fixture,actual)
        finally:context.close()
    run('electrical_rebuild_exact_source_projection',projection)
    for width in (1440,375,390,485):
        context=browser.new_context(viewport={'width':width,'height':1000},is_mobile=width<=780,has_touch=width<=780,
                                    service_workers='block',permissions=['clipboard-read','clipboard-write'])
        try:
            page=context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda e:page_errors.append(str(e)))
            for row in rows:
                def render_one(row=row):
                    page.goto(base+'?id='+quote(row['id'])+'&q='+quote(row['hazard']['title']),wait_until='domcontentloaded')
                    expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                    card=page.locator('#list .card[data-id="'+row['id']+'"]');card.click()
                    result=validate_rendered_detail(row,page.evaluate(DOM_SNAPSHOT))
                    page.wait_for_function('''narrow=>{const h=document.querySelector('header').getBoundingClientRect(),t=document.querySelector('#detail h2').getBoundingClientRect();return t.top>=h.bottom-1&&(!narrow||t.bottom<=innerHeight)&&document.documentElement.scrollWidth<=innerWidth+1;}''',arg=width<=780)
                    if width<=780:page.locator('#backResults').click()
                    card.click();validate_rendered_detail(row,page.evaluate(DOM_SNAPSHOT))
                    page.locator('#copy').click();wanted=expected_clipboard(row)
                    page.wait_for_function('async want=>(await navigator.clipboard.readText())===want',arg=wanted)
                    page.locator('#copyfull').click()
                    page.wait_for_function('async want=>{const t=await navigator.clipboard.readText();return t.startsWith(want)&&t.includes("核验状态：")&&t.includes("数据库版本：");}',arg=wanted)
                    page.reload(wait_until='domcontentloaded');expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                    validate_rendered_detail(row,page.evaluate(DOM_SNAPSHOT))
                    require(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Electrical detail overflows after reload')
                    actual=page.evaluate("async()=>await(await fetch('./data/manifest.json',{cache:'no-store'})).json()")
                    validate_release_match(actual['releaseHash'],release_hash)
                    return {**result,'width':width,'repeatedSelection':True,'copyExact':True,'copyFullPreservesExactScopeAndQuotes':True,'reload':True}
                run(f'electrical_rebuild_detail_copy_{width}px_{row["id"]}',render_one)
        finally:context.close()
