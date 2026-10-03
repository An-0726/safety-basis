"""Source-pinned rendered acceptance for the reviewed repair cohort.

The pure validators do not import Playwright, launch Chromium, alter the Gate, or
perform legal review. Expectations are frozen source records, never scraped back
from a generated bundle to make that same bundle pass.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

FIXTURE_PATH = Path(__file__).parent / 'fixtures/repaired_hazards_20261003.json'
COHORT_COUNTS = {'flange': 3, 'training': 5, 'occupational': 3, 'remaining': 26}
SOURCE_FIXTURES = {
    'flange': 'flange_scope_corrections_20261003.json',
    'training': 'training_citation_repair_20261003.json',
    'occupational': 'occupational_citation_repair_20261003.json',
    'remaining': 'remaining_clause_repair_20261003.json',
}
ROLE_LABELS = {'direct': '直接依据', 'indirect': '间接依据',
               'supporting': '间接／辅助依据', 'fallback': '上位法／兜底依据'}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def visible_text(value):
    """Ignore browser whitespace layout only, preserving all words/punctuation."""
    require(isinstance(value, str), 'Visible content must be a string')
    return ' '.join(value.split())


def require_text(actual, expected, label):
    require(visible_text(actual) == visible_text(expected), f'{label}: rendered text differs from the frozen source')


def validate_expectations(fixture):
    require(fixture.get('schemaVersion') == 'reviewed-repair-browser-v1', 'Unknown repair expectation schema')
    records = fixture.get('records', [])
    require(len(records) == 37 and len({r['id'] for r in records}) == 37, 'Expected exactly 37 distinct repaired H')
    require(dict(Counter(r['cohort'] for r in records)) == COHORT_COUNTS == fixture.get('cohortCounts'), 'Repair cohort drift')
    excluded = fixture.get('excludedClauseIds', [])
    require(len(excluded) == len(set(excluded)) == 27, 'Expected exactly 27 quarantined C')
    require(fixture.get('expectedHazards') == 1671 and fixture.get('expectedPublicLinks') == 1817 and fixture.get('expectedPublicClauses') == 1362, 'Public inventory expectation drift')
    require(set(fixture.get('sourceFixtureHashes', {})) == set(COHORT_COUNTS), 'Missing source review fixture bindings')
    all_links = []
    required_paths = {f'knowledge/clauses/{cid}.json' for cid in excluded}
    for row in records:
        required_paths.add(f'knowledge/hazards/{row["id"]}.json')
        for field in ('title', 'description', 'conditions', 'measures', 'category'):
            require(isinstance(row['hazard'][field], str) and row['hazard'][field].strip(), f'{row["id"]}: missing {field}')
        require(isinstance(row['hazard']['places'], list) and row['hazard']['places'], 'Missing places')
        require(len(row['bases']) == 1, f'{row["id"]}: unexpected reviewed basis cardinality')
        for basis in row['bases']:
            require(basis['clauseId'] not in excluded, 'Quarantined C used by a positive expectation')
            require(basis['role'] == 'direct', 'Unexpected reviewed basis role')
            for key in ('linkId', 'clauseId', 'lawId', 'lawName', 'article', 'quote', 'applicability', 'sourceUrl'):
                require(isinstance(basis[key], str) and basis[key].strip(), f'Missing expected basis {key}')
            require(urlparse(basis['sourceUrl']).scheme in ('http', 'https'), 'Invalid public source URL')
            all_links.append(basis['linkId'])
            required_paths.update([f'knowledge/links/{basis["linkId"]}.json',
                                   f'knowledge/clauses/{basis["clauseId"]}.json',
                                   f'knowledge/law-versions/{basis["lawId"]}.json'])
    require(len(all_links) == len(set(all_links)) == 37, 'Expected exactly 37 distinct K')
    require(set(fixture['representativeIds']) <= {r['id'] for r in records}, 'Unknown flow representative')
    require(required_paths <= set(fixture['sourceFiles']), 'Missing repaired or quarantined source pins')
    for path, digest in fixture['sourceFiles'].items():
        require(path.startswith('knowledge/') and '..' not in Path(path).parts, 'Unexpected source pin path')
        require(len(digest) == 64 and all(ch in '0123456789abcdef' for ch in digest), 'Malformed source pin')
    return records


def load_expectations(path=FIXTURE_PATH):
    fixture = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_expectations(fixture)
    return fixture


def validate_source_pins(fixture, root):
    validate_expectations(fixture)
    checked = []
    for relative, expected in fixture['sourceFiles'].items():
        path = Path(root) / relative
        require(path.is_file(), f'Missing reviewed source: {relative}')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Reviewed source drift: {relative}')
        checked.append(relative)
    for cohort, filename in SOURCE_FIXTURES.items():
        path = Path(root) / 'tools/pipeline/tests/fixtures' / filename
        require(path.is_file(), 'Missing reviewed fixture: ' + cohort)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == fixture['sourceFixtureHashes'][cohort],
                'Reviewed fixture drift: ' + cohort)
    return {'sourceFiles': len(checked), 'sourceFixtures': 4, 'hazards': 37, 'basisLinks': 37, 'excludedClauses': 27}


def validate_release_match(actual, expected):
    require(isinstance(expected, str) and len(expected) == 64
            and all(ch in '0123456789abcdef' for ch in expected),
            'Missing exact release hash for repaired browser checks')
    require(actual == expected, 'Release changed during repaired-detail acceptance')
    return expected


def validate_rendered_detail(expected, actual):
    require(actual['id'] == expected['id'], f'Wrong rendered hazard ID: {actual["id"]}')
    h = expected['hazard']
    for key in ('title', 'description', 'conditions', 'measures'):
        require_text(actual[key], h[key], expected['id'] + ':' + key)
    require_text(actual['category'], expected.get('displayCategory', h['category']), 'Displayed category')
    require_text(actual['places'], ' · '.join(h['places']), 'Displayed places')
    bases = actual['bases']
    require(len(bases) == len(expected['bases']), 'Missing or extra rendered basis')
    require(len({b['linkId'] for b in bases}) == len(bases), 'Duplicate rendered basis')
    actual_by_id = {b['linkId']: b for b in bases}
    require(set(actual_by_id) == {b['linkId'] for b in expected['bases']}, 'Wrong rendered basis identities')
    for basis in expected['bases']:
        shown = actual_by_id[basis['linkId']]
        for key in ('applicability', 'article', 'quote', 'lawName'):
            require_text(shown[key], basis[key], expected['id'] + ':' + basis['linkId'] + ':' + key)
        require_text(shown['roleLabel'], ROLE_LABELS[basis['role']], 'Displayed basis role')
        require(shown['lawId'] == basis['lawId'], 'Wrong rendered law navigation target')
        require(shown['sourceUrl'] == basis['sourceUrl'], 'Wrong rendered official source URL')
    return {'id': expected['id'], 'cohort': expected['cohort'],
            'links': sorted(actual_by_id), 'fullQuotesExact': True, 'scopeAndFieldsExact': True}


def validate_public_projection(fixture, projection):
    require(projection['hazards'] == fixture['expectedHazards'], 'Public hazard membership count changed')
    require(projection['links'] == fixture['expectedPublicLinks'], 'Public link membership count changed')
    excluded = set(fixture['excludedClauseIds'])
    require(not excluded & set(projection['hazardClauseIds']), 'Quarantined clause still occurs in public hazard basis')
    require(not excluded & set(projection['lawClauseIds']), 'Quarantined clause still occurs in public law catalogue')
    hazard_clauses = set(projection['hazardClauseIds'])
    law_clauses = set(projection['lawClauseIds'])
    require(len(hazard_clauses) == len(law_clauses) == fixture['expectedPublicClauses'],
            'Public clause membership count changed')
    require(hazard_clauses == law_clauses, 'Hazard and law clause catalogues disagree')
    actual = projection['repairDetails']
    require(len(actual) == len({r['id'] for r in actual}) == 37, 'Missing or duplicate hydrated repair')
    actual = {r['id']: r for r in actual}
    require(set(actual) == {r['id'] for r in fixture['records']}, 'Hydrated repair identity drift')
    for expected in fixture['records']:
        got = actual[expected['id']]
        for key, value in expected['hazard'].items():
            require(got['hazard'].get(key) == value, f'Wrong public repaired field: {expected["id"]}:{key}')
        require(got['bases'] == expected['bases'], f'Wrong public repaired basis/clause/quote: {expected["id"]}')
    return {'hazards': projection['hazards'], 'links': projection['links'], 'repairedHazards': 37, 'clauses': len(hazard_clauses),
            'quarantinedClausesAbsentFromHazardsAndLaws': 27, 'exactHydratedSourceProjection': True}


# Read text from the DOM that the app rendered. No DataStore values enter this
# snapshot; the separate hydration audit below checks C IDs and catalogue joins.
DOM_SNAPSHOT = r'''() => {
    const detail = document.querySelector('#detail');
    const sections = [...detail.querySelectorAll('.detailbody > section.block')];
    const paragraph = label => {
        const section = sections.find(s => s.querySelector(':scope > h3')?.textContent.includes(label));
        const p = section?.querySelector(':scope > p');
        if (!p) throw Error('Missing rendered section: ' + label);
        return p.innerText;
    };
    const description = sections[0]?.querySelector(':scope > p');
    const subtitle = detail.querySelector('.detailtop .subtitle');
    return {
        id: new URL(location.href).searchParams.get('id'),
        title: detail.querySelector('h2').innerText,
        description: description?.innerText || '', conditions: paragraph('适用条件'),
        measures: paragraph('整改措施'), category: detail.querySelector('.detailtop .eyebrow').innerText,
        places: subtitle.firstChild.textContent,
        bases: [...detail.querySelectorAll('.basis[data-link-id]')].map(b => ({
            linkId: b.dataset.linkId, quote: b.querySelector('blockquote').innerText,
            applicability: b.querySelector('.basis-applicability p')?.innerText || '',
            article: b.querySelector(':scope > span.article').innerText.split(' · 条款核验：')[0],
            lawName: b.querySelector('h4').innerText,
            lawId: b.querySelector('.lawjump').dataset.law,
            roleLabel: b.querySelector('.basismeta > span:first-child').innerText,
            sourceUrl: b.querySelector('.basislinks a')?.getAttribute('href') || ''
        }))
    };
}'''

HYDRATE_PROJECTION = r'''async repairIds => {
    const {DataStore} = await import('./js/store.js');
    const store = await new DataStore('.').init(), wanted = new Set(repairIds);
    const hazardClauseIds = new Set(), lawClauseIds = new Set(), repairDetails = [];
    let links = 0;
    for (const index of store.searchIndex) {
        const d = await store.getHazardDetail(index);
        for (const b of d.bases) { links++; hazardClauseIds.add(b.clause.id); }
        if (wanted.has(index.id)) repairDetails.push({id: index.id, hazard: d.hazard,
            bases: d.bases.map(b => ({linkId:b.ref.linkId, clauseId:b.clause.id,
                lawId:b.law.id, lawName:b.law.name, role:b.ref.role,
                applicability:b.ref.applicability, article:b.clause.article,
                quote:b.clause.quote, sourceUrl:b.sourceUrl}))});
    }
    for (const law of store.lawIndex) {
        const d = await store.getLawDetail(law);
        for (const b of d.clauses) lawClauseIds.add(b.clause.id);
    }
    return {releaseHash:store.manifest.releaseHash, hazards:store.searchIndex.length, links, hazardClauseIds:[...hazardClauseIds],
            lawClauseIds:[...lawClauseIds], repairDetails};
}'''


def wait_for_repair_condition(page, predicate, *, arg, phase):
    """Retain the failed flow phase and measured state without relaxing waits."""
    try:
        return page.wait_for_function(predicate, arg=arg)
    except Exception as exc:
        try:
            state = page.evaluate('''() => {
                const h = document.querySelector('header')?.getBoundingClientRect();
                const t = document.querySelector('#detail h2')?.getBoundingClientRect();
                const list = document.querySelector('#list');
                return {url:location.href, title:document.querySelector('#detail h2')?.textContent,
                    headerHeight:h?.height, headerBottom:h?.bottom, titleTop:t?.top,
                    titleBottom:t?.bottom, viewport:innerWidth, viewportHeight:innerHeight,
                    scrollY, listScrollTop:list?.scrollTop,
                    cardCount:document.querySelectorAll('#list .card').length,
                    loadMorePresent:!!document.querySelector('#loadMore'),
                    measuredHeaderHeight:getComputedStyle(document.documentElement).getPropertyValue('--sticky-header-height')};
            }''')
        except Exception as diagnostic_error:
            state = {'diagnosticError': str(diagnostic_error)}
        raise AssertionError(f'{phase}: {exc}; state={json.dumps(state, ensure_ascii=False)}') from exc


def run_repair_browser_acceptance(browser, base, run, page_errors, expect, fixture, expected_release_hash):
    """Use the existing approved Playwright browser/CI; never launches another."""
    validate_expectations(fixture)
    validate_release_match(expected_release_hash, expected_release_hash)
    by_id = {r['id']: r for r in fixture['records']}

    def geometry(page, step, width, require_in_view=False):
        wait_for_repair_condition(page, '''inView => {
            const h = document.querySelector('header')?.getBoundingClientRect();
            const t = document.querySelector('#detail h2')?.getBoundingClientRect();
            if (!h || !t) return false;
            const measured = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sticky-header-height'));
            return t.top >= h.bottom - 1 && (!inView || t.bottom <= innerHeight)
                && Math.abs(measured - h.height) < 1;
        }''', arg=require_in_view, phase=f'geometry:{step}:{width}px')
        value = page.evaluate('''() => {
            const h = document.querySelector('header').getBoundingClientRect();
            const t = document.querySelector('#detail h2').getBoundingClientRect();
            return {headerHeight:h.height, headerBottom:h.bottom, titleTop:t.top,
                titleBottom:t.bottom, viewport:innerWidth, scrollY,
                documentWidth:document.documentElement.scrollWidth};
        }''')
        require(value['documentWidth'] <= width + 1, 'Repaired detail has horizontal overflow')
        return {'step': step, **value}

    def detail(page, row):
        expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
        result = validate_rendered_detail(row, page.evaluate(DOM_SNAPSHOT))
        manifest = page.evaluate("async () => { const r = await fetch('./data/manifest.json', {cache:'no-store'}); if (!r.ok) throw Error('Cannot recheck release identity'); return await r.json(); }")
        validate_release_match(manifest.get('releaseHash'), expected_release_hash)
        result['releaseHash'] = expected_release_hash
        return result

    def public_check():
        device = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
        try:
            page = device.new_page()
            page.on('pageerror', lambda error: page_errors.append(str(error)))
            page.goto(base, wait_until='domcontentloaded')
            expect(page.locator('#count')).to_have_text(str(fixture['expectedHazards']))
            actual = page.evaluate(HYDRATE_PROJECTION, list(by_id))
            validate_release_match(actual.get('releaseHash'), expected_release_hash)
            return validate_public_projection(fixture, actual)
        finally:
            device.close()
    run('37_repairs_exact_public_projection_and_27_excluded_clauses', public_check)

    # Each H has its own check result at every width, so one failure cannot hide
    # coverage of the rest of the cohort. Responsive contexts are simulated, not
    # a claim of physical-phone testing.
    for width in (1440, 375, 390, 485):
        device = browser.new_context(viewport={'width': width, 'height': 1000},
                                    is_mobile=width <= 780, has_touch=width <= 780,
                                    service_workers='block')
        try:
            page = device.new_page()
            page.set_default_timeout(15000)
            page.on('pageerror', lambda error: page_errors.append(str(error)))
            for row in fixture['records']:
                def render_one(row=row):
                    page.goto(base + '?id=' + quote(row['id']) + '&q=' + quote(row['hazard']['title']),
                              wait_until='domcontentloaded')
                    expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                    page.locator('#list .card[data-id="' + row['id'] + '"]').click()
                    result = detail(page, row)
                    result['geometry'] = geometry(page, 'select_repaired_detail', width, width <= 780)
                    result['width'] = width
                    return result
                run(f'repaired_detail_{width}px_{row["id"]}', render_one)

            def representative_flows():
                representatives = [by_id[hid] for hid in fixture['representativeIds']]
                first, second = representatives[:2]
                page.goto(base + '?id=' + quote(first['id']), wait_until='domcontentloaded')
                expect(page.locator('#count')).to_have_text(str(fixture['expectedHazards']))
                detail(page, first)
                # Real list controls expose all targets. Do not inject routing,
                # edit app state, or force scroll to manufacture geometry passes.
                while page.locator('#loadMore').count():
                    previous = page.locator('#list .card').count()
                    require(previous < fixture['expectedHazards'], 'Load-more failed to terminate')
                    page.locator('#loadMore').click()
                    wait_for_repair_condition(page, 'n => document.querySelectorAll("#list .card").length > n',
                                              arg=previous, phase=f'load_more:{width}px:previous={previous}')
                evidence = []
                for row in representatives:
                    card = page.locator('#list .card[data-id="' + row['id'] + '"]')
                    card.click(); detail(page, row)
                    evidence.append({'id': row['id'], **geometry(page, 'selection', width, width <= 780)})
                    if width <= 780:
                        page.locator('#backResults').click()
                        require(page.locator('#list').evaluate('el => el === document.activeElement'), 'Return-results focus lost')
                    card.click(); detail(page, row)
                    evidence.append({'id': row['id'], **geometry(page, 'repeated_selection', width, width <= 780)})
                # Two different actual card clicks create SPA history entries.
                page.locator('#list .card[data-id="' + first['id'] + '"]').click(); detail(page, first)
                page.locator('#list .card[data-id="' + second['id'] + '"]').click(); detail(page, second)
                page.go_back(); detail(page, first)
                evidence.append({'id': first['id'], **geometry(page, 'detail_back', width)})
                page.go_forward(); detail(page, second)
                evidence.append({'id': second['id'], **geometry(page, 'detail_forward', width)})
                page.reload(wait_until='domcontentloaded'); detail(page, second)
                # An interrupted empty search must recover through reset.
                page.fill('#search', '不存在的修复验收词REPAIR_ZYX_98765')
                expect(page.locator('#count')).to_have_text('0')
                page.locator('#reset').click()
                expect(page.locator('#count')).to_have_text(str(fixture['expectedHazards']))
                expect(page.locator('#search')).to_have_value('')
                require(not parse_qs(urlparse(page.url).query).get('q'), 'Reset retained query')
                for row in (first, representatives[-1]):
                    page.fill('#search', row['hazard']['title'])
                    page.locator('#list .card[data-id="' + row['id'] + '"]').click(); detail(page, row)
                    evidence.append({'id': row['id'], **geometry(page, 'selection_after_reset', width, width <= 780)})
                return {'width': width, 'representatives': fixture['representativeIds'],
                        'repeated': True, 'spaBackForward': True, 'reload': True,
                        'emptySearchReset': True, 'reselectedAfterReset': True, 'geometry': evidence}
            run(f'repaired_repeated_reset_history_{width}px', representative_flows)
        finally:
            device.close()
