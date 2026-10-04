"""Whole-public-set and changed-detail acceptance pinned to reviewed source.

The checked-in expectations are produced by freeze_recovery_expectations.py from
formal source and Gate projections. Generated site data is only the test subject.
"""
import copy
import json
from pathlib import Path
import sys
from urllib.parse import quote
from repair_acceptance import (DOM_SNAPSHOT, require, require_text, validate_release_match,
                               validate_rendered_detail)

FIXTURE = Path(__file__).parent / 'fixtures/recovery_release_20261004.json'
PUBLIC_SETS = ('hazards', 'links', 'clauses', 'majorHazards', 'profiles')


def validate_expectations(f):
    require(f.get('schemaVersion') == 'recovery-release-browser-v1', 'Unknown recovery release schema')
    require(set(f.get('expectedIds', {})) == set(PUBLIC_SETS), 'Missing exact public ID set')
    for key in PUBLIC_SETS:
        ids = f['expectedIds'][key]
        require(ids == sorted(set(ids)) and ids, 'Malformed exact public ID set: ' + key)
    require('H052' in f['expectedIds']['hazards'], 'Recovered H052 must have positive coverage')
    require(f.get('unpublishedProbeId') == 'H_12158_10_1_2' and f['unpublishedProbeId'] not in f['expectedIds']['hazards'], 'Unpublished probe is public or changed')
    rows = f.get('records', [])
    require([r['id'] for r in rows] == f.get('changedHazardIds') == sorted({r['id'] for r in rows}), 'Changed recovery detail identity drift')
    require('H052' in f['changedHazardIds'], 'H052 missing positive rendered test')
    require(set(f['changedHazardIds']) <= set(f['expectedIds']['hazards']), 'Nonpublic detail expected')
    for row in rows:
        require(row.get('changedDependencies'), 'Changed detail lacks source change provenance')
        require(row['bases'] and len({b['linkId'] for b in row['bases']}) == len(row['bases']), 'Missing or duplicate source basis')
        require(f'knowledge/hazards/{row["id"]}.json' in f['sourceFiles'], 'Missing changed H source pin')
        for b in row['bases']:
            require(b['linkId'] in f['expectedIds']['links'] and b['clauseId'] in f['expectedIds']['clauses'], 'Nonpublic source basis expected')
            for kind, key in [('links', 'linkId'), ('clauses', 'clauseId'), ('law-versions', 'lawId')]:
                require(f'knowledge/{kind}/{b[key]}.json' in f['sourceFiles'], 'Missing current basis source pin')
    for rel, digest in f['sourceFiles'].items():
        require(rel.startswith('knowledge/') and '..' not in Path(rel).parts and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'Malformed source pin')
    validate_release_match(f.get('knowledgeSnapshotHash'), f.get('knowledgeSnapshotHash'))
    return rows


def load_expectations(path=FIXTURE):
    f = json.loads(Path(path).read_text())
    validate_expectations(f)
    return f


def validate_source_pins(fixture, root):
    validate_expectations(fixture)
    sys.path.insert(0, str(Path(root) / 'tools/v4'))
    from release_snapshot import source_hashes, snapshot_digest
    hashes = source_hashes(Path(root) / 'knowledge')
    actual = snapshot_digest(hashes)
    require(actual == fixture['knowledgeSnapshotHash'], 'Recovery source snapshot changed; reviewed fixture must be explicitly re-frozen')
    require(len(hashes) == fixture['sourceFileCount'], 'Recovery source file inventory changed')
    for rel, digest in fixture['sourceFiles'].items():
        require(hashes.get(rel.removeprefix('knowledge/')) == digest, 'Recovery detail source drift: ' + rel)
    return {'knowledgeSnapshotHash': actual, 'sourceFiles': len(hashes), 'exactPublicSets': len(PUBLIC_SETS), 'changedPublicHazards': len(fixture['records'])}



def full_dated_public_projections(root, as_of, *, knowledge):
    """All six dated builder projections, derived from source, not a bundle."""
    sys.path.insert(0, str(Path(root) / 'tools/v4'))
    from major_criteria import public_projection as major
    from field_profiles import public_projection as profiles
    from major_criteria_references import public_projection as references
    from major_criteria_directory import public_projection as directory
    from major_criteria_reading import public_projection as reading
    knowledge, publication = Path(knowledge), Path(root) / 'source/publication'
    m = major(knowledge, as_of=as_of)
    values = {'majorCatalog': m['catalog'], 'majorTopic': m['topic'],
        'profiles': profiles(knowledge, as_of=as_of)['public'],
        'references': references(knowledge, publication, as_of=as_of)['public'],
        'directory': directory(knowledge, publication, as_of=as_of)['public'],
        'reading': reading(knowledge, publication, as_of=as_of)['public']}
    # These six documented top-level snapshot labels alone may advance.
    # Nested effective dates, conditions, status labels and every other field
    # remain part of the exact comparison; never recursively strip dates.
    for name, value in values.items():
        require(value.get('asOf') == as_of.isoformat(), 'Unexpected projection date: ' + name)
        value = copy.deepcopy(value)
        del value['asOf']
        values[name] = value
    return values


def fixture_for_release_date(frozen, actual_as_of, root):
    """Permit later-day replay only if the entire source projection is identical.

    The checked-in fixture and approvals are never rewritten. Any membership,
    exact detail, major/profile/read-only projection change fails closed and
    requires an explicitly reviewed new freeze, even when counts stay equal.
    """
    from datetime import date
    try:
        current = date.fromisoformat(actual_as_of)
        original = date.fromisoformat(frozen['asOf'])
    except (ValueError, TypeError) as exc:
        raise AssertionError('Release asOf is not an explicit ISO date') from exc
    require(actual_as_of == current.isoformat(), 'Release asOf is not a canonical ISO date')
    require(current >= original, 'Release date precedes reviewed source freeze')
    validate_source_pins(frozen, root)
    if current == original:
        return copy.deepcopy(frozen)
    from freeze_recovery_expectations import project_expectations
    from release_snapshot import stable_knowledge_snapshot, source_hashes
    with stable_knowledge_snapshot(Path(root) / 'knowledge') as (knowledge, digest):
        require(digest == frozen['knowledgeSnapshotHash'], 'Source changed during date compatibility check')
        hashes = source_hashes(knowledge)
        baseline = dict(hashes)
        for path, change in frozen['sourceChanges'].items():
            if change['beforeSha256'] is None:
                baseline.pop(path, None)
            else:
                baseline[path] = change['beforeSha256']
        projected = project_expectations(knowledge, current, hashes=hashes,
            baseline_commit=frozen['baselineCommit'], baseline=baseline)
        projected['knowledgeSnapshotHash'] = digest
        same_date = copy.deepcopy(projected)
        same_date['asOf'] = frozen['asOf']
        require(same_date == frozen, 'Date advancement changes reviewed public membership/details; new review and freeze required')
        require(full_dated_public_projections(root, original, knowledge=knowledge) == full_dated_public_projections(root, current, knowledge=knowledge),
            'Date advancement changes a complete public projection; new review and freeze required')
    validate_source_pins(frozen, root)
    return projected


def validate_release_source(fixture, release, expected_release_hash):
    validate_release_match(release.get('releaseHash'), expected_release_hash)
    require(release.get('knowledge', {}).get('snapshotSha256') == fixture['knowledgeSnapshotHash'], 'Browser release is not the source-pinned recovery snapshot')
    require(release.get('asOf') == fixture['asOf'], 'Browser release effective date differs from frozen source Gate date')
    return {'releaseHash': expected_release_hash, 'knowledgeSnapshotHash': fixture['knowledgeSnapshotHash'], 'asOf': fixture['asOf']}


def validate_projection(fixture, actual):
    for key, expected in fixture['expectedIds'].items():
        require(actual[key] == expected, 'Exact recovery public membership differs: ' + key)
    require(actual['lawClauses'] == fixture['expectedIds']['clauses'], 'Exact law catalogue clause membership differs')
    rows = actual['details']
    require(len(rows) == len({r['id'] for r in rows}) == len(fixture['records']), 'Missing/duplicate changed public detail')
    got = {r['id']: r for r in rows}
    require(set(got) == set(fixture['changedHazardIds']), 'Wrong changed public detail identities')
    for row in fixture['records']:
        value = got[row['id']]
        for key, want in row['hazard'].items():
            require(value['hazard'].get(key) == want, 'Changed public field differs: ' + row['id'] + ':' + key)
        require(value['hazard'].get('displayCategory') == row['displayCategory'], 'Changed display category differs')
        require(value['bases'] == row['bases'], 'Current exact K/C/quote/scope/source/table/geography differs: ' + row['id'])
    return {**{key: len(ids) for key, ids in fixture['expectedIds'].items()}, 'changedPublicHazards': len(rows), 'exactIdSetsAndCurrentBases': True}


def expected_tables(basis):
    return [{key: copy.deepcopy(part[key]) for key in ('caption', 'headerRows', 'bodyRows')}
            for part in basis.get('contentParts', []) if part['type'] == 'table']


def validate_rendered(row, actual):
    result = validate_rendered_detail(row, actual)
    by_id = {b['linkId']: b for b in actual['bases']}
    for b in row['bases']:
        shown = by_id[b['linkId']]
        parts = shown['metadataText'].split('·')
        require(len(parts) == 3, 'Wrong rendered law metadata shape')
        require_text(parts[1], b['lawRegion'], 'Rendered law geography')
        require(shown['tables'] == expected_tables(b), 'Rendered complete table cell text, order or spans differ: ' + b['linkId'])
    return {**result, 'completeTablesAndLawRegionsExact': True}


def expected_clipboard(row):
    h = row['hazard']
    prefix = ''
    if row['profiles']:
        prefix = '核查参考资料，非已核实的现场隐患。场景选择不代表条件成立或违规已发生。'
        if all(p['defaultFieldEntry'] == 'exclude' for p in row['profiles']):
            prefix += '本条已审场景不纳入默认现场检查；排除现场入口不等于本项要求不适用。'
        prefix += '\n\n'
    conditions = '\n\n适用条件：\n' + h['conditions'] if h['conditions'] else ''
    bases = '\n\n'.join('《' + b['lawName'] + '》' + b['article'] + '\n本条依据适用范围：' + b['applicability'] + '\n' + b['quote'] for b in row['bases'])
    return prefix + h['title'] + '\n\n隐患专业描述：\n' + h['description'] + conditions + '\n\n法规依据：\n' + bases + '\n\n整改措施：\n' + h['measures']


def expected_full_clipboard(row, data_version):
    sections = [expected_clipboard(row)]
    notes = row['copyNotes']
    if notes['businessNote']:
        sections.append('补充说明：\n' + notes['businessNote'])
    if notes['historicalReferences']:
        sections.append('历史引用（不替代当前依据）：\n' + '\n\n'.join(notes['historicalReferences']))
    sections.append(f"核验状态：{row['hazard']['status']}；核验日期：{row['hazard']['checked'] or '未填写'}；数据库版本：{data_version}。")
    return '\n\n'.join(sections)


HYDRATE = r'''async wantedIds => {
 const {DataStore}=await import('./js/store.js');
 const store=await new DataStore('.').init(),wanted=new Set(wantedIds),details=[];
 const hazards=[],links=[],clauses=new Set(),lawClauses=new Set();
 for(const row of store.searchIndex){hazards.push(row.id);const d=await store.getHazardDetail(row);
  for(const b of d.bases){links.push(b.ref.linkId);clauses.add(b.clause.id);}
  if(wanted.has(row.id))details.push({id:row.id,hazard:d.hazard,bases:d.bases.map(b=>({
   linkId:b.ref.linkId,clauseId:b.clause.id,lawId:b.law.id,lawName:b.law.name,role:b.ref.role,
   applicability:b.ref.applicability,article:b.clause.article,quote:b.clause.quote,sourceUrl:b.sourceUrl,
   jurisdictionCode:b.ref.jurisdictionCode??null,clauseRegion:b.clause.region,lawRegion:b.law.scope,
   contentParts:b.clause.contentParts??[]}))});}
 for(const row of store.lawIndex){const d=await store.getLawDetail(row);for(const b of d.clauses)lawClauses.add(b.clause.id);}
 const get=async name=>{const r=await fetch('./data/'+name+'.json',{cache:'no-store'});if(!r.ok)throw Error(name);return r.json();};
 const major=await get('major-criteria-topic'),profiles=await get('field-profiles');
 return {releaseHash:store.manifest.releaseHash,hazards:hazards.sort(),links:links.sort(),
  clauses:[...clauses].sort(),lawClauses:[...lawClauses].sort(),details,
  majorHazards:[...major.hazardIds].sort(),profiles:profiles.records.map(p=>p.id).sort()};
}'''


def rendered_snapshot(page):
    actual = page.evaluate(DOM_SNAPSHOT)
    metadata = page.locator('#detail .basis[data-link-id]').evaluate_all('(rows)=>Object.fromEntries(rows.map(b=>[b.dataset.linkId,b.querySelector(".basismeta > span.article").innerText]))')
    for b in actual['bases']:
        b['metadataText'] = metadata[b['linkId']]
    return actual


def run_recovery_release_acceptance(browser, base, run, page_errors, expect, fixture, release_hash, *, artifact_dir=None, data_version=None):
    rows = validate_expectations(fixture)
    require(data_version, 'Missing pinned data version for complete copy checks')
    def release_check(page):
        release = page.evaluate("async()=>{const r=await fetch('./release.json',{cache:'no-store'});if(!r.ok)throw Error('release.json unavailable');return r.json();}")
        return validate_release_source(fixture, release, release_hash)

    def exact_sets():
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
        try:
            page = context.new_page()
            page.on('pageerror', lambda e: page_errors.append(str(e)))
            page.goto(base, wait_until='domcontentloaded')
            expect(page.locator('#count')).to_have_text(str(len(fixture['expectedIds']['hazards'])))
            release_check(page)
            actual = page.evaluate(HYDRATE, fixture['changedHazardIds'])
            validate_release_match(actual['releaseHash'], release_hash)
            result = validate_projection(fixture, actual)
            release_check(page)
            return result
        finally:
            context.close()
    run('recovery_exact_entire_public_membership', exact_sets)
    if artifact_dir:
        artifact_dir = Path(artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)
    for width in (1440, 375, 390, 485):
        context = browser.new_context(viewport={'width': width, 'height': 1000},
            is_mobile=width <= 780, has_touch=width <= 780, service_workers='block',
            permissions=['clipboard-read', 'clipboard-write'])
        try:
            page = context.new_page()
            page.set_default_timeout(15000)
            page.on('pageerror', lambda e: page_errors.append(str(e)))
            def detail(row):
                expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                return validate_rendered(row, rendered_snapshot(page))
            for row in rows:
                def render_one(row=row):
                    try:
                        page.goto(base + '?id=' + quote(row['id']) + '&q=' + quote(row['hazard']['title']), wait_until='domcontentloaded')
                        detail(row); release_check(page)
                        card = page.locator('#list .card[data-id="' + row['id'] + '"]')
                        card.click(); detail(row)
                        if width <= 780:
                            page.locator('#backResults').click()
                            require(page.locator('#list').evaluate('el=>el===document.activeElement'), 'Recovery return-results focus lost')
                        card.click(); result = detail(row)
                        page.wait_for_function('''narrow=>{const h=document.querySelector('header').getBoundingClientRect(),t=document.querySelector('#detail h2').getBoundingClientRect();return t.top>=h.bottom-1&&(!narrow||t.bottom<=innerHeight)&&document.documentElement.scrollWidth<=innerWidth+1;}''', arg=width <= 780)
                        for button in ('#copy', '#copyfull', '#copy'):
                            page.locator(button).click()
                            wanted = expected_clipboard(row)
                            if button == '#copyfull':
                                page.wait_for_function('async want=>(await navigator.clipboard.readText())===want', arg=expected_full_clipboard(row, data_version))
                            else:
                                page.wait_for_function('async want=>(await navigator.clipboard.readText())===want', arg=wanted)
                        if artifact_dir and width in (1440, 390):
                            page.screenshot(path=str(artifact_dir / f'recovery-{width}-{row["id"]}.png'), full_page=True)
                        first = row['bases'][0]
                        page.locator('#detail .lawjump').first.click()
                        expect(page.locator('#detail h2')).to_have_text(first['lawName'])
                        require(page.evaluate("new URL(location.href).searchParams.get('law')") == first['lawId'], 'Wrong law history destination')
                        require(page.locator('#copylaw').count() == 1, 'Law history destination missing')
                        page.go_back(); detail(row)
                        page.go_forward(); expect(page.locator('#detail h2')).to_have_text(first['lawName'])
                        require(page.evaluate("new URL(location.href).searchParams.get('law')") == first['lawId'], 'Forward restored wrong law identity')
                        page.go_back(); detail(row)
                        page.reload(wait_until='domcontentloaded'); detail(row)
                        require(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), 'Recovery detail overflow after reload')
                        release_check(page)
                        return {**result, 'width': width, 'reload': True, 'repeatedSelection': True,
                            'backForward': True, 'copyExact': True, 'fullCopyComplete': True}
                    except Exception:
                        if artifact_dir:
                            try:
                                page.screenshot(path=str(artifact_dir / f'FAILED-recovery-{width}-{row["id"]}.png'), full_page=True)
                            except Exception:
                                pass
                        raise
                run(f'recovery_detail_copy_history_{width}px_{row["id"]}', render_one)
        finally:
            context.close()
    run('recovery_exact_public_membership_after_flows', exact_sets)
