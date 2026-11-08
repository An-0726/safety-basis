"""Real Chromium acceptance of the original site's search and loading experience.

Uses the generated public bundle, user examples and synthetic development cases.
No held-out query dataset or search implementation is imported to derive expected
answers. Faults are injected only into isolated local browser contexts; nothing
is written into the bundle, knowledge or a live site.

python tools/browser/audit_search_ux.py --bundle source/releases/current --out /tmp/search-ux
Add --executable /usr/bin/chromium only to use a system browser; CI defaults to
Playwright's installed Chromium. Output includes report.json and QA screenshots.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import functools
import http.server
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import parse_qs, quote, urlencode, urlparse

from playwright.sync_api import expect, sync_playwright


PROFILE_DELAY_HEADER = 'X-Search-UX-Profile-Delay'


class HeldProfileResponse:
    """Delay an actual HTTP response without retaining a Playwright Route."""

    def __init__(self, path, key):
        self.path, self.key = path, key
        self.received, self.released = threading.Event(), threading.Event()
        self.lock, self.request_count = threading.Lock(), 0

    def matches(self, path, header):
        return header == self.key and urlparse(path).path.endswith('/' + self.path)

    def arrive(self):
        with self.lock:
            self.request_count += 1
        self.received.set()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
            gate = getattr(self.server, 'profile_gate', None)
            if gate and gate.matches(self.path, self.headers.get(PROFILE_DELAY_HEADER)):
                gate.arrive()
                if not gate.released.wait(timeout=30):
                    self.send_error(504, 'Acceptance test did not release the delayed response')
                    return
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            # Fault tests intentionally let the browser abort requests. The
            # response gate is always released in finally, including failures.
            pass

    def log_message(self, *_args):
        pass


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def compact(text):
    return re.sub(r'\s+', '', text or '')


def candidate_text(row):
    """Only the item's own curated names and keywords, never incidental prose."""
    return ' '.join([row.get('title', ''), *row.get('aliases', []), *row.get('keywords', [])])


def require_candidate_semantics(candidate_ids, by_id, object_pattern, defect_pattern=None):
    assert candidate_ids, 'Expected at least one independently relevant candidate'
    rejected = []
    for candidate_id in candidate_ids:
        row = by_id[candidate_id]
        text = candidate_text(row)
        if not re.search(object_pattern, text) or (defect_pattern and not re.search(defect_pattern, text)):
            rejected.append({'id': candidate_id, 'title': row['title'], 'itemTerms': text})
    assert not rejected, {'wrongCandidateSemantics': rejected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--executable', help='Optional system Chromium; default: Playwright Chromium')
    args = parser.parse_args()
    bundle, output = args.bundle.resolve(strict=True), args.out.resolve()
    if bundle == output or bundle in output.parents:
        raise SystemExit('Write QA evidence outside the served public bundle')
    if not (bundle / 'release.json').is_file():
        raise SystemExit('A generated public release bundle is required')
    output.mkdir(parents=True, exist_ok=True)
    manifest = read_json(bundle / 'data/manifest.json')
    site_manifest = read_json(bundle / 'site-manifest.json')
    rows = read_json(bundle / manifest['files']['searchIndex'])
    by_id = {row['id']: row for row in rows}
    detailed = {}
    for shard in manifest['hazardShards']:
        detailed.update({row['id']: row for row in read_json(bundle / shard['url'])['records']})
    version, profile_path = site_manifest['dataVersion'], manifest['files'].get('fieldProfiles')
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(bundle.parent)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/{quote(bundle.name)}/'
    report = {
        'schemaVersion': 'search-ux-browser-audit-v2', 'target': 'local generated public bundle',
        'dataVersion': version, 'hazards': len(rows), 'sourceKind': 'synthetic',
        'samplePurpose': 'public requirements and development regression; not held-out accuracy',
        'realDeidentifiedSamples': 0, 'createdAt': datetime.now(timezone.utc).isoformat(), 'checks': [],
    }
    normal_errors = []
    try:
        with sync_playwright() as pw:
            launch = {'headless': True}
            if args.executable:
                launch['executable_path'] = args.executable
            browser = pw.chromium.launch(**launch)

            @contextmanager
            def session(name, *, width=1440, height=1000, injected=False):
                context = browser.new_context(viewport={'width': width, 'height': height}, service_workers='block')
                page = context.new_page()
                page.set_default_timeout(15000)
                page.set_default_navigation_timeout(30000)
                if not injected:
                    page.on('pageerror', lambda error: normal_errors.append({'check': name, 'error': str(error)}))
                try:
                    yield page
                except Exception:
                    try:
                        page.screenshot(path=str(output / f'failed-{name}.png'), full_page=True, timeout=5000)
                    except Exception:
                        pass
                    raise
                finally:
                    context.close()

            def check(name, fn):
                started = time.monotonic()
                try:
                    result = {'name': name, 'pass': True, 'evidence': fn()}
                except Exception as error:
                    result = {'name': name, 'pass': False, 'error': str(error)}
                result['elapsedSeconds'] = round(time.monotonic() - started, 3)
                report['checks'].append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)

            def ready(page, *, profiles=True):
                expect(page.locator('#loadStatus')).to_be_hidden(timeout=30000)
                expect(page.locator('#count')).to_have_text(re.compile(r'^[1-9][0-9]*$'))
                if profiles:
                    expect(page.locator('#profileStatus')).to_be_hidden(timeout=30000)

            def home(page, params=None, *, profiles=True):
                page.goto(base + ('?' + urlencode(params) if params else ''), wait_until='domcontentloaded')
                ready(page, profiles=profiles)

            def query(page, text, *, positive=True):
                page.locator('#search').fill(text)
                page.wait_for_function('(query) => new URL(location.href).searchParams.get("q") === query', arg=text)
                expect(page.locator('#count')).to_have_text(re.compile(r'^[1-9][0-9]*$') if positive else '0')
                expect(page.locator('#search')).to_have_value(text)
                assert parse_qs(urlparse(page.url).query).get('q') == [text], page.url

            def ids(page, selector='#list .card'):
                return page.locator(selector).evaluate_all('(nodes)=>nodes.map(node=>node.dataset.id)')

            def all_ids(page):
                while page.locator('#loadMore').count():
                    page.locator('#loadMore').click()
                return ids(page)

            def expand(page):
                if page.locator('#hazardMoreFilters').get_attribute('open') is None:
                    page.locator('#hazardMoreFilters summary').click()
                expect(page.locator('#category')).to_be_visible()

            def retry_visible(page, pattern, timeout=15000):
                expect(page.locator('#loadStatus.failed')).to_be_visible(timeout=timeout)
                expect(page.locator('#loadMessage')).to_contain_text(pattern)
                expect(page.locator('#retryLoad')).to_be_visible()
                expect(page.locator('#recoverCache')).to_be_visible()
                expect(page.locator('#list .card')).to_have_count(0)

            def retry(page):
                with page.expect_navigation(wait_until='domcontentloaded'):
                    page.locator('#retryLoad').click()
                ready(page)
                expect(page.locator('#loadStatus.failed')).not_to_be_visible()

            def no_overflow(page):
                size = page.evaluate("""() => ({
                    viewport:innerWidth, document:document.documentElement.scrollWidth, body:document.body.scrollWidth,
                    overflow:[...document.querySelectorAll('main button,main select,main input,main section')]
                      .filter(node=>{const r=node.getBoundingClientRect();return r.width&&r.right>innerWidth+1;})
                      .slice(0,8).map(node=>({tag:node.tagName,id:node.id,classes:node.className}))
                })""")
                assert size['document'] <= size['viewport'] + 1 and size['body'] <= size['viewport'] + 1, size
                return size

            def targets(page, selectors):
                checked = {}
                for selector in selectors:
                    nodes = page.locator(selector)
                    assert nodes.count(), f'Missing touch control: {selector}'
                    visible = 0
                    for i in range(nodes.count()):
                        if not nodes.nth(i).is_visible():
                            continue
                        visible += 1
                        box = nodes.nth(i).bounding_box()
                        assert box and box['height'] >= 43.5 and box['width'] >= 43.5, (selector, box)
                        checked[f'{selector}:{i}'] = {key: round(box[key], 1) for key in ['width', 'height']}
                    assert visible, f'Touch control is hidden: {selector}'
                return checked

            def controls():
                with session('controls') as page:
                    home(page)
                    for selector in ['#browse', '#equipment', '#problem']:
                        expect(page.locator(selector)).to_be_visible()
                        assert page.locator(selector + ' option').count() > 1
                    for selector in ['#category', '#region', '#scene', '#industry']:
                        expect(page.locator(selector)).not_to_be_visible()
                    available = {tag for row in rows for tag in row.get('sceneTags', [])}
                    options = set(page.locator('#scene option').evaluate_all('(nodes)=>nodes.map(node=>node.value)'))
                    assert options - {'', '未细分场景', '__unclassified__'} == available
                    page.screenshot(path=str(output / 'desktop-search.png'), full_page=True)
                    return {'primaryFilters': ['问题分类', '检索对象', '问题类型'], 'sourceGroundedSceneOptions': len(available)}
            check('primary_controls_and_source_grounded_scenes', controls)

            def versions():
                with session('versions') as page:
                    requested = []
                    page.on('request', lambda request: requested.append(request.url))
                    with page.expect_response(lambda response: urlparse(response.url).path.endswith('/site-manifest.json')) as sm:
                        with page.expect_response(lambda response: urlparse(response.url).path.endswith('/data/manifest.json')) as dm:
                            home(page)
                    pv = page.locator('meta[name="safety-basis-version"]').get_attribute('content')
                    sv, dv = sm.value.json()['dataVersion'], dm.value.json()['dataVersion']
                    assert pv == sv == dv == version
                    assets = [url for url in requested if url.startswith(base) and urlparse(url).path.endswith(('.js', '.css'))
                              and not urlparse(url).path.endswith('/sw.js')]
                    assert assets
                    wrong = [url for url in assets if parse_qs(urlparse(url).query).get('v') != [version]]
                    assert not wrong, wrong
                    return {'page': pv, 'manifest': sv, 'data': dv, 'versionedRuntimeAssets': len(assets)}
            check('page_scripts_and_data_use_one_release', versions)

            def multiple():
                text = '灭火器失压，疏散通道还堆了纸箱'
                with session('multiple') as page:
                    home(page)
                    query(page, text)
                    groups = page.locator('#list .issue-group')
                    expect(groups).to_have_count(2)
                    expect(page.locator('#issueOverview')).to_be_visible()
                    expect(groups.nth(0).locator('h3').first).to_contain_text('灭火器失压')
                    expect(groups.nth(1).locator('h3').first).to_contain_text('疏散通道还堆了纸箱')
                    first = ids(page, '#list .issue-group:nth-of-type(1) .card')
                    second = ids(page, '#list .issue-group:nth-of-type(2) .card')
                    require_candidate_semantics(first, by_id, '灭火器', '失压|压力不足|无压力|欠压')
                    require_candidate_semantics(second, by_id, '疏散通道|安全出口|逃生通道',
                                                '堆放|堆积|占用|堵塞|阻塞|封闭|不畅|障碍')
                    assert 'H001' in first, {'missingPressureAnchor': first}
                    assert not set(first) & set(second), {'mixedIssueGroups': [first, second]}
                    groups.nth(1).get_by_role('button', name=re.compile('只看这个问题')).click()
                    expect(page.locator('#list .issue-group')).to_have_count(0)
                    focused = all_ids(page)
                    require_candidate_semantics(focused, by_id, '疏散通道|安全出口|逃生通道',
                                                '堆放|堆积|占用|堵塞|阻塞|封闭|不畅|障碍')
                    assert 'H008' in focused and 'H001' not in focused, {'wrongFocusedCandidates': focused}
                    page.get_by_role('button', name='全部问题', exact=True).click()
                    expect(page.locator('#list .issue-group')).to_have_count(2)
                    expect(page.locator('#search')).to_have_value(text)
                    page.screenshot(path=str(output / 'desktop-multiple.png'), full_page=True)
                    return {'query': text, 'groups': 2, 'firstIds': first, 'secondIds': second,
                            'focusedIds': focused, 'independentObjectAndDefectChecks': True, 'focusKeepsOriginal': True}
            check('multiple_observations_have_independent_result_groups', multiple)

            def clarify():
                with session('clarify') as page:
                    home(page)
                    query(page, '灭火器没压力，通道堆东西')
                    groups = page.locator('#list .issue-group')
                    expect(groups).to_have_count(2)
                    expect(groups.nth(1).locator('.empty')).to_contain_text('需要补充对象或现场条件')
                    groups.nth(1).get_by_role('button', name='人员疏散通道', exact=True).click()
                    current = page.locator('#search').input_value()
                    assert current.startswith('灭火器没压力，'), current
                    expect(page.locator('#list .issue-group')).to_have_count(2)
                    assert page.locator('#list .issue-group').nth(1).locator('.card').count() > 0
                    return {'otherObservationPreserved': True, 'selectedQuery': current}
            check('clarifying_one_issue_preserves_other_observations', clarify)

            def negatives():
                values = ['应急灯没有坏', '通道没有堆东西', '现场尚未核实应急灯是否损坏', '灭火器已经修复了']
                with session('negatives') as page:
                    home(page)
                    for text in values:
                        query(page, text, positive=False)
                        expect(page.locator('#list .card')).to_have_count(0)
                        expect(page.locator('#list')).to_contain_text('尚未确认存在缺陷')
                    query(page, '灭火器没有损坏，疏散通道堵塞')
                    groups = page.locator('#list .issue-group')
                    expect(groups).to_have_count(2)
                    expect(groups.nth(0).locator('.card')).to_have_count(0)
                    assert groups.nth(1).locator('.card').count() > 0
                    return {'queries': values, 'negatedGroupEmpty': True, 'independentPositiveGroupSearchable': True}
            check('negation_uncertainty_and_completed_states_are_preserved', negatives)

            def states():
                with session('states') as page:
                    home(page)
                    query(page, '电箱没安装', positive=False)
                    expect(page.locator('#list .card')).to_have_count(0)
                    query(page, '安装后应急灯坏了')
                    titles = page.locator('#list .card h3').all_text_contents()
                    assert titles and all('损坏' in title or '不能正常' in title for title in titles), titles
                    assert not any('未设置' in title for title in titles), titles
                    query(page, '设备检验报告没有提供', positive=False)
                    expect(page.locator('#list')).to_contain_text('需要补充对象或现场条件')
                    expect(page.locator('#searchNotice')).to_contain_text(re.compile('不能.*(?:推定|认定)'))
                    return {'absentNotSubstituted': True, 'damagedLampTitles': titles, 'documentsNotImplementation': True}
            check('missing_fault_and_documentary_states_remain_separate', states)

            def devices():
                with session('devices') as page:
                    home(page)
                    query(page, '行车')
                    crane_ids = all_ids(page)
                    require_candidate_semantics(crane_ids, by_id, r'起重|吊钩|天车|桥式|(?<!自)行车(?!道)')
                    assert not any('自行车' in candidate_text(by_id[item]) for item in crane_ids), crane_ids
                    query(page, '自行车充电')
                    bicycle_ids = all_ids(page)
                    require_candidate_semantics(bicycle_ids, by_id, '自行车|电瓶车', '充电')
                    assert 'H010' in bicycle_ids, {'missingBicycleAnchor': bicycle_ids}
                    assert not set(crane_ids) & set(bicycle_ids), {'crossMatchedObjects': [crane_ids, bicycle_ids]}
                    return {'craneIds': crane_ids, 'bicycleIds': bicycle_ids,
                            'craneTitles': [by_id[item]['title'] for item in crane_ids],
                            'bicycleTitles': [by_id[item]['title'] for item in bicycle_ids],
                            'ownItemMetadataChecks': True}
            check('crane_and_bicycle_objects_do_not_cross_match', devices)

            def natural():
                values = ['今天检查时看到车间里的灭火器没有压力了', '灭活器没压力', '失压的灭火器']
                with session('natural') as page:
                    home(page)
                    for text in values:
                        query(page, text)
                        expect(page.locator('#list .card').first.locator('h3')).to_contain_text('灭火器')
                        assert any('失压' in title for title in page.locator('#list .card h3').all_text_contents()), text
                        if '灭活器' in text:
                            expect(page.locator('#searchNotice')).to_contain_text('纠错')
                    return {'queries': values, 'originalInputAndUrlPreserved': True}
            check('spoken_typo_long_and_reordered_queries_reach_candidates', natural)

            def ambiguity():
                with session('ambiguity') as page:
                    home(page)
                    query(page, '通道堆东西', positive=False)
                    for label in ['人员疏散通道', '消防车道', '配电箱操作通道']:
                        expect(page.locator('#searchSuggestions').get_by_role('button', name=label, exact=True)).to_be_visible()
                    page.locator('#searchSuggestions').get_by_role('button', name='人员疏散通道', exact=True).click()
                    expect(page.locator('#count')).not_to_have_text('0')
                    query(page, '电箱没接地')
                    expect(page.locator('#searchNotice')).to_contain_text('需要核实')
                    expect(page.locator('#searchNotice')).to_contain_text('箱门')
                    assert page.locator('#searchSuggestions button').count() >= 1
                    return {'passageChoices': 3, 'cabinetConditionsVisible': True}
            check('ambiguous_phrases_offer_choices_and_required_conditions', ambiguity)

            def facets():
                with session('facets') as page:
                    home(page)
                    text = '灭火器没压力'
                    query(page, text)
                    page.select_option('#equipment', '灭火器')
                    page.select_option('#problem', '损坏或失效')
                    expect(page.locator('#count')).not_to_have_text('0')
                    before = ids(page)
                    assert before and all('灭火器' in by_id[item]['title'] for item in before)
                    page.reload(wait_until='domcontentloaded')
                    ready(page)
                    expect(page.locator('#equipment')).to_have_value('灭火器')
                    expect(page.locator('#problem')).to_have_value('损坏或失效')
                    assert set(ids(page)) == set(before)
                    page.select_option('#equipment', '叉车')
                    expect(page.locator('#count')).to_have_text('0')
                    expect(page.locator('#list')).to_contain_text('当前筛选挡住了候选')
                    page.get_by_role('button', name='清除筛选，保留问法', exact=True).click()
                    expect(page.locator('#search')).to_have_value(text)
                    expect(page.locator('#equipment')).to_have_value('')
                    expect(page.locator('#problem')).to_have_value('')
                    expect(page.locator('#count')).not_to_have_text('0')
                    assert parse_qs(urlparse(page.url).query).get('q') == [text]
                    return {'combinedIds': before, 'reloadPreservesCombination': True, 'clearFiltersKeepsQuery': True}
            check('equipment_problem_filter_combinations_and_clear_keep_query', facets)

            def scenes():
                counts = {}
                for row in rows:
                    for scene in row.get('sceneTags', []):
                        counts[scene] = counts.get(scene, 0) + 1
                scene = '配电室与配电装置' if '配电室与配电装置' in counts else min(counts, key=counts.get)
                expected = {row['id'] for row in rows if scene in row.get('sceneTags', [])}
                with session('scenes') as page:
                    home(page)
                    expand(page)
                    page.select_option('#scene', scene)
                    expect(page.locator('#count')).to_have_text(str(len(expected)))
                    assert set(all_ids(page)) == expected
                    page.locator('#hazardMoreFilters summary').click()
                    chip = page.get_by_role('button', name=f'移除现场标签：{scene}', exact=True)
                    expect(chip).to_be_visible()
                    chip.click()
                    expect(page.locator('#count')).to_have_text(str(len(rows)))
                    page.go_back(wait_until='domcontentloaded')
                    expect(page.locator('#scene')).to_have_value(scene)
                    expect(page.locator('#count')).to_have_text(str(len(expected)))
                    page.go_forward(wait_until='domcontentloaded')
                    expect(page.locator('#scene')).to_have_value('')
                    return {'scene': scene, 'count': len(expected), 'sourceIdsAgree': True, 'collapsedChipAndHistory': True}
            check('scene_filter_matches_source_and_survives_history', scenes)

            def candidate():
                with session('candidate') as page:
                    home(page)
                    query(page, '灭火器没压力')
                    expect(page.locator('#list .card').first.locator('.candidate-status')).to_contain_text('现场事实待核实')
                    assert page.locator('#list .card h3 mark').count() > 0
                    labels = page.locator('#list .card').first.locator('.card-preview b').all_text_contents()
                    assert '依据' in labels and any(label in ['条件', '场所'] for label in labels), labels
                    target = next(row for key, row in detailed.items() if key in by_id and row.get('conditions'))
                    query(page, target['title'])
                    page.locator(f'#list .card[data-id="{target["id"]}"]').click()
                    expect(page.locator('#detail h2')).to_have_text(target['title'])
                    expect(page.locator('#detail .detail-candidate')).to_contain_text('现场事实待核实')
                    expect(page.locator('#detail .onsite-notice')).to_contain_text('不代表已确认现场存在隐患')
                    expect(page.locator('#detail')).to_contain_text('适用条件')
                    assert compact(target['conditions']) in compact(page.locator('#detail').inner_text())
                    assert page.locator('#detail .basis').count() > 0
                    return {'cardLabels': labels, 'highlighted': True, 'conditionsId': target['id'], 'sourceConditionsShown': True}
            check('candidate_status_highlighting_basis_and_conditions_are_visible', candidate)

            def empties():
                with session('empties') as page:
                    home(page)
                    query(page, '气瓶没防震圈', positive=False)
                    expect(page.locator('#list')).to_contain_text('当前已核验库暂缺对应依据')
                    query(page, '合成未知条目QZX9073', positive=False)
                    expect(page.locator('#list')).to_contain_text('没有找到对题候选')
                    expect(page.locator('#list')).to_contain_text('不代表没有相关要求')
                    return {'sourceGapDistinctFromNoMatch': True, 'zeroIsNotNoDuty': True}
            check('source_gap_and_generic_zero_result_have_distinct_explanations', empties)

            def keyboard():
                with session('keyboard') as page:
                    home(page)
                    page.locator('#sectionTitle').click()
                    page.keyboard.press('/')
                    expect(page.locator('#search')).to_be_focused()
                    page.locator('#hazardMoreFilters summary').focus()
                    page.keyboard.press('Enter')
                    expect(page.locator('#industry')).to_be_visible()
                    page.keyboard.press('Tab')
                    expect(page.locator('#industry')).to_be_focused()
                    return {'slashFocus': True, 'nativeDisclosure': True, 'tabReachesIndustry': True}
            check('keyboard_search_and_filter_disclosure', keyboard)

            def mobile():
                results = []
                for width in [320, 390]:
                    with session(f'mobile_{width}', width=width, height=844) as page:
                        home(page)
                        measured = targets(page, ['#search', '#clear', '#browse', '#equipment', '#problem', '#reset', '#hazardMoreFilters summary'])
                        no_overflow(page)
                        expand(page)
                        filter_box = page.locator('#hazardFilters').bounding_box()
                        open_box = page.locator('#hazardMoreFilters').bounding_box()
                        panel_box = page.locator('#hazardMoreFilters .more-filter-items').bounding_box()
                        assert filter_box and open_box and panel_box, 'Expanded filters have no visible dimensions'
                        assert abs(open_box['width'] - filter_box['width']) <= 1, {'filters': filter_box, 'open': open_box}
                        assert abs(panel_box['width'] - filter_box['width']) <= 1, {'filters': filter_box, 'panel': panel_box}
                        assert abs(panel_box['x'] - filter_box['x']) <= 1, {'filters': filter_box, 'panel': panel_box}
                        measured.update(targets(page, ['#industry', '#category', '#region', '#scene', '#level', '#mode', '#inspectionClass']))
                        no_overflow(page)
                        query(page, '灭火器没压力，疏散通道堆了纸箱')
                        measured.update(targets(page, ['#issueOverview button', '#list .issue-focus-button']))
                        no_overflow(page)
                        page.select_option('#equipment', '叉车')
                        expect(page.locator('#count')).to_have_text('0')
                        measured.update(targets(page, ['#activeFilters .filter-chip', '#list [data-clear-filters]']))
                        no_overflow(page)
                        page.locator('#list [data-clear-filters]').first.click()
                        expect(page.locator('#count')).not_to_have_text('0')
                        page.locator('#list .card').first.click()
                        expect(page.locator('#detail h2')).to_be_visible()
                        measured.update(targets(page, ['#backResults']))
                        page.locator('#backResults').click()
                        expect(page.locator('#list')).to_be_focused()
                        no_overflow(page)
                        page.screenshot(path=str(output / f'mobile-{width}-search.png'), full_page=True)
                        results.append({'width': width, 'noOverflow': True, 'returnFocus': 'results',
                                        'expandedFilterWidth': round(panel_box['width'], 1),
                                        'availableFilterWidth': round(filter_box['width'], 1), 'touchTargets': measured})
                return results
            check('mobile_widths_touch_targets_and_return_focus', mobile)

            def page_conflict():
                html = (bundle / 'index.html').read_text(encoding='utf-8')
                changed, count = re.subn(r'(<meta\s+name="safety-basis-version"\s+content=")[^"]*(")',
                                         rf'\g<1>{version}.stale-page\2', html, count=1)
                assert count == 1, 'Page is missing its release stamp'
                pattern = re.compile(re.escape(base) + r'(?:index\.html)?(?:\?.*)?$')
                with session('page_conflict', injected=True) as page:
                    def stale(route):
                        route.fulfill(status=200, content_type='text/html; charset=utf-8', body=changed)
                    page.route(pattern, stale)
                    page.goto(base, wait_until='domcontentloaded')
                    retry_visible(page, 'VERSION_MISMATCH')
                    expect(page.locator('#loadTitle')).to_contain_text('版本不一致')
                    message = page.locator('#loadMessage').inner_text()
                    page.unroute(pattern, stale)
                    retry(page)
                    return {'stalePageRejected': True, 'message': message, 'retryRestoresSearch': True}
            check('stale_page_and_current_script_fail_visibly_then_retry', page_conflict)

            def data_conflict():
                changed = {**site_manifest, 'dataVersion': version + '.other-release'}
                pattern = '**/site-manifest.json*'
                with session('data_conflict', injected=True) as page:
                    def stale(route):
                        route.fulfill(status=200, content_type='application/json', body=json.dumps(changed))
                    page.route(pattern, stale)
                    page.goto(base, wait_until='domcontentloaded')
                    retry_visible(page, 'VERSION_MISMATCH')
                    message = page.locator('#loadMessage').inner_text()
                    page.unroute(pattern, stale)
                    retry(page)
                    return {'mixedDataRejected': True, 'message': message, 'retryRestoresSearch': True}
            check('current_script_and_different_data_release_fail_visibly_then_retry', data_conflict)

            def corruption():
                pattern = '**/' + manifest['files']['searchIndex'] + '*'
                with session('corruption', injected=True) as page:
                    def corrupt(route):
                        route.fulfill(status=200, content_type='application/json', body='[]')
                    page.route(pattern, corrupt)
                    page.goto(base, wait_until='domcontentloaded')
                    retry_visible(page, 'INTEGRITY')
                    message = page.locator('#loadMessage').inner_text()
                    page.unroute(pattern, corrupt)
                    retry(page)
                    return {'wrongBytesRejected': True, 'message': message, 'retryRestoresSearch': True}
            check('incomplete_or_stale_index_bytes_are_not_silently_displayed', corruption)

            def network():
                pattern = '**/' + manifest['files']['searchIndex'] + '*'
                attempts = []
                with session('network', injected=True) as page:
                    def offline(route):
                        attempts.append(route.request.url)
                        route.abort('failed')
                    page.route(pattern, offline)
                    text = '灭火器没压力'
                    page.goto(base + '?' + urlencode({'q': text}), wait_until='domcontentloaded')
                    retry_visible(page, 'NETWORK')
                    message = page.locator('#loadMessage').inner_text()
                    page.unroute(pattern, offline)
                    retry(page)
                    expect(page.locator('#search')).to_have_value(text)
                    assert any('灭火器' in title for title in page.locator('#list .card h3').all_text_contents())
                    return {'failedRequests': len(attempts), 'visibleCause': message, 'retryRestoresSearch': True, 'queryPreserved': True}
            check('network_failure_has_reason_and_working_retry', network)

            def module_failure():
                pattern = '**/js/search.js*'
                with session('module_failure', injected=True) as page:
                    def unavailable(route):
                        route.abort('failed')
                    page.route(pattern, unavailable)
                    page.goto(base, wait_until='domcontentloaded')
                    retry_visible(page, re.compile('脚本|启动'), timeout=26000)
                    message = page.locator('#loadMessage').inner_text()
                    page.unroute(pattern, unavailable)
                    retry(page)
                    return {'moduleFailureHasRecovery': True, 'message': message, 'retryRestoresSearch': True}
            check('missing_module_cannot_leave_endless_initialization', module_failure)

            def delayed_profiles():
                assert profile_path, 'Release does not advertise field profiles'
                gate = HeldProfileResponse(profile_path, 'delayed-profiles')
                with session('delayed_profiles', injected=True) as page:
                    failures, responses = [], []

                    def is_profile(url):
                        return urlparse(url).path.endswith('/' + profile_path)

                    def failed(request):
                        if is_profile(request.url):
                            failures.append(request.failure)

                    page.on('requestfailed', failed)
                    page.on('response', lambda response: responses.append(response.url) if is_profile(response.url) else None)
                    page.set_extra_http_headers({PROFILE_DELAY_HEADER: gate.key})
                    server.profile_gate = gate
                    try:
                        started = time.monotonic()
                        home(page, profiles=False)
                        # The server must have the request before we inspect
                        # core usability; no profile headers/body are released.
                        request_deadline = time.monotonic() + 15
                        while not gate.received.is_set():
                            remaining = request_deadline - time.monotonic()
                            assert remaining > 0, 'No profile response was actually held'
                            page.wait_for_timeout(min(50, remaining * 1000))
                        expect(page.locator('#profileStatus')).to_contain_text('搜索已可用')
                        document_started = page.evaluate('performance.timeOrigin')
                        query(page, '灭火器没压力')
                        page.locator('#list .card').first.click()
                        expect(page.locator('#detail h2')).to_contain_text('灭火器')
                        expect(page.locator('#detail .basis').first).to_be_visible()
                        assert not responses, 'Core search/detail was checked after a profile response arrived'
                        assert not gate.released.is_set(), 'Profile response was released before core detail was checked'
                        core_seconds = round(time.monotonic() - started, 3)
                        held_count = gate.request_count
                        gate.released.set()
                        page.wait_for_function("""() => document.querySelector('#profileStatus').hidden ||
                            !!document.querySelector('#retryProfiles')""", timeout=30000)
                        retried = page.locator('#retryProfiles').is_visible()
                        if retried:
                            assert failures, 'Unexpected profile failure after the held response was released'
                            expect(page.locator('#profileStatus')).to_contain_text('超时')
                            page.locator('#retryProfiles').click()
                        expect(page.locator('#profileStatus')).to_be_hidden(timeout=30000)
                        assert responses, 'Profiles became ready without a profile response'
                        assert page.evaluate('performance.timeOrigin') == document_started
                        expect(page.locator('#search')).to_have_value('灭火器没压力')
                        expect(page.locator('#count')).not_to_have_text('0')
                        return {'heldProfileRequests': held_count, 'searchAndBasisBeforeProfiles': True,
                                'profileResponsesBeforeSearchAndBasis': 0, 'failedProfileRequests': failures,
                                'releasedProfileResponses': len(responses), 'retriedAfterProfileTimeout': retried,
                                'secondsToSearchAndDetail': core_seconds, 'profilesEventuallyJoin': True,
                                'originalDocumentPreserved': True}
                    finally:
                        gate.released.set()
                        server.profile_gate = None
            check('delayed_profiles_do_not_block_core_search_or_detail', delayed_profiles)

            def profiles_retry():
                assert profile_path, 'Release does not advertise field profiles'
                pattern = '**/' + profile_path + '*'
                with session('profiles_retry', injected=True) as page:
                    def offline(route):
                        route.abort('failed')
                    page.route(pattern, offline)
                    home(page, profiles=False)
                    expect(page.locator('#profileStatus')).to_contain_text('未能加载')
                    expect(page.locator('#retryProfiles')).to_be_visible()
                    query(page, '灭火器没压力')
                    before = ids(page)
                    assert before
                    document_started = page.evaluate('performance.timeOrigin')
                    page.unroute(pattern, offline)
                    page.locator('#retryProfiles').click()
                    expect(page.locator('#profileStatus')).to_be_hidden(timeout=30000)
                    assert page.evaluate('performance.timeOrigin') == document_started
                    expect(page.locator('#search')).to_have_value('灭火器没压力')
                    assert set(before) == set(ids(page))
                    return {'coreSurvivesOptionalFailure': True, 'retryWithoutReload': True, 'queryAndCandidatesPreserved': True}
            check('optional_profile_failure_preserves_search_and_can_retry', profiles_retry)

            def no_errors():
                assert not normal_errors, normal_errors
                return {'normalFlowUnhandledErrors': normal_errors, 'injectedFailureContextsExcluded': True}
            check('normal_search_flows_have_no_unhandled_javascript_errors', no_errors)
            browser.close()
    except Exception as error:
        report['checks'].append({'name': 'browser_execution', 'pass': False, 'error': str(error)})
    finally:
        server.shutdown()
        server.server_close()
        report['passed'] = sum(item['pass'] for item in report['checks'])
        report['failed'] = sum(not item['pass'] for item in report['checks'])
        report['total'] = len(report['checks'])
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'passed': report['passed'], 'failed': report['failed'], 'total': report['total'],
                          'report': str(output / 'report.json')}, ensure_ascii=False), flush=True)
    return bool(report['failed'])


if __name__ == '__main__':
    raise SystemExit(main())
