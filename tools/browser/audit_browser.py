"""Real Chromium acceptance tests; no screenshots or document conversion.

Requires Playwright and its Chromium. --observe records baseline defects without
turning an intentionally unfixed baseline into a failed acquisition workflow.
The normal mode exits nonzero if ANY assertion fails. No production writes.
"""
import argparse
import functools
import http.server
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from playwright.sync_api import sync_playwright, expect


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--bundle', type=Path)
    source.add_argument('--url')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--observe', action='store_true')
    parser.add_argument('--executable')
    args = parser.parse_args()
    server = None
    if args.bundle:
        bundle = args.bundle.resolve(strict=True)
        require((bundle / 'release.json').is_file(), 'Not a unified release bundle')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(bundle.parent)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/{quote(bundle.name)}/'
    else:
        base = args.url.rstrip('/') + '/'
        require(urlparse(base).scheme in ('http', 'https'), 'Only HTTP(S) sites are supported')
    report = {'startedAt': datetime.now(timezone.utc).isoformat(), 'target': base, 'observeOnly': args.observe, 'checks': []}
    started = time.monotonic()
    try:
        with sync_playwright() as pw:
            options = {'headless': True}
            if args.executable:
                options['executable_path'] = args.executable
            browser = pw.chromium.launch(**options)
            report['browserVersion'] = browser.version
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
            page = context.new_page()
            page.set_default_timeout(15000)
            page_errors = []
            page.on('pageerror', lambda err: page_errors.append(str(err)))

            def run(name, function):
                before = time.monotonic()
                try:
                    evidence = function()
                    result = {'name': name, 'pass': True, 'evidence': evidence}
                except Exception as exc:
                    result = {'name': name, 'pass': False, 'error': str(exc)}
                result['seconds'] = round(time.monotonic() - before, 3)
                report['checks'].append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)

            def home(suffix=''):
                page.goto(base + suffix, wait_until='domcontentloaded')
                expect(page.locator('#count')).to_have_text(re.compile(r'^[1-9][0-9]*$'))
                return page

            def detail_ready():
                page.wait_for_selector('#detail h2')

            def home_check():
                home(); detail_ready()
                count = int(page.locator('#count').inner_text())
                require(count > 0, 'Homepage contains no published hazards')
                require(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Desktop horizontal overflow')
                return {'count': count, 'title': page.locator('#detail h2').inner_text()}
            run('desktop_home', home_check)

            def hydrate_all():
                home()
                result = page.evaluate('''async () => {
                    const {DataStore} = await import('./js/store.js');
                    const store = await new DataStore('.').init();
                    let hazards = 0, links = 0, laws = 0; const errors = [];
                    for (const index of store.searchIndex) {
                        try {
                            const d = await store.getHazardDetail(index);
                            if (d.hazard.id !== index.id || d.hazard.status !== '已核验' || d.hazard.publishable === false) throw Error('wrong/unpublished hazard');
                            if (!d.bases.length) throw Error('no eligible basis');
                            for (const b of d.bases) {
                                if (!b.clause?.quote?.trim() || !b.law?.id) throw Error('empty quote or missing law');
                                links++;
                            }
                            hazards++;
                        } catch (e) { errors.push({id:index.id, error:String(e)}); }
                    }
                    for (const law of store.lawIndex) {
                        try {
                            const d = await store.getLawDetail(law);
                            if (d.clauses.length !== law.clauseCount) throw Error('clause count mismatch');
                            laws++;
                        } catch (e) { errors.push({id:law.id, error:String(e)}); }
                    }
                    return {hazards, links, laws, expected:store.manifest.counts, errors};
                }''')
                require(not result['errors'], str(result['errors']))
                for field in ('hazards', 'links', 'laws'):
                    require(result[field] == result['expected'][field], f'{field}: {result[field]} != {result["expected"][field]}')
                return result
            run('all_published_hazards_laws_quotes_and_counts', hydrate_all)

            def search_check(query):
                home(); page.fill('#search', query)
                page.wait_for_selector('#list .card'); detail_ready()
                require(int(page.locator('#count').inner_text()) > 0, 'No search results')
                return {'query': query, 'count': page.locator('#count').inner_text()}
            run('search_exact', lambda: search_check('灭火器'))
            run('search_typo', lambda: search_check('灭活器'))
            run('search_synonym', lambda: search_check('配电房'))

            def empty_check():
                home(); page.fill('#search', '不存在的测试词ZYX987654321')
                expect(page.locator('#count')).to_have_text('0')
                require('没有找到' in page.locator('#list').inner_text(), 'Empty-state explanation missing')
                return {'count': 0, 'text': page.locator('#list').inner_text()}
            run('empty_results', empty_check)

            def filter_roundtrip(selector, value, parameter):
                home(); page.select_option(selector, value)
                page.wait_for_timeout(100)
                before = page.locator('#count').inner_text(); shared = page.url
                require(parse_qs(urlparse(shared).query).get(parameter) == [value], f'Shared URL omits {parameter}: {shared}')
                page.reload(); page.wait_for_selector('#list .card')
                require(page.locator(selector).input_value() == value, 'Filter lost on reload')
                require(page.locator('#count').inner_text() == before, 'Result count changed after sharing')
                return {'filter': value, 'count': before, 'url': shared}
            run('category_share_reload', lambda: filter_roundtrip('#category', '电气安全', 'category'))
            run('scene_share_reload', lambda: filter_roundtrip('#scene', '仓储与物流', 'scene'))
            run('region_share_reload', lambda: filter_roundtrip('#region', '江苏', 'region'))

            def history_check():
                home(); page.locator('#list .card').nth(1).click(); detail_ready()
                previous = parse_qs(urlparse(page.url).query).get('id')
                page.locator('#list .card').nth(2).click(); detail_ready()
                current = parse_qs(urlparse(page.url).query).get('id')
                page.go_back(); page.wait_for_timeout(200)
                require(parse_qs(urlparse(page.url).query).get('id') == previous, 'Back did not restore previous selected ID')
                page.go_forward(); page.wait_for_timeout(200)
                require(parse_qs(urlparse(page.url).query).get('id') == current, 'Forward did not restore selected ID')
                return {'previous': previous, 'next': current}
            run('browser_back_forward', history_check)

            def cross_navigation():
                search_check('灭火器')
                page.wait_for_selector('.lawjump')
                button = page.locator('.lawjump').first; target = button.get_attribute('data-law')
                button.click(); page.wait_for_selector('.lawmeta')
                require(parse_qs(urlparse(page.url).query).get('law') == [target], 'Hazard-to-law link opened the wrong record')
                button = page.locator('.hazardjump').first; target_hazard = button.get_attribute('data-id')
                button.click(); page.wait_for_selector('#detail h2')
                require(parse_qs(urlparse(page.url).query).get('id') == [target_hazard], 'Law-to-hazard link opened the wrong record')
                return {'lawId': target, 'hazardId': target_hazard}
            run('hazard_law_bidirectional_navigation', cross_navigation)

            def unavailable():
                home('?id=H004'); expect(page.locator('#detail')).to_contain_text('H004')
                text = page.locator('#detail').inner_text()
                require('未' in text or '候选' in text, 'Unpublished ID silently selected another hazard')
                return {'id': 'H004', 'text': text}
            run('unpublished_H004_deep_link', unavailable)

            def unknown():
                home('?id=H_AUDIT_UNKNOWN_ZYX987')
                expect(page.locator('#detail')).to_contain_text('H_AUDIT_UNKNOWN_ZYX987')
                require(page.locator('#detail h2').count() == 0, 'Unknown ID silently selected a published record')
                return {'message': page.locator('#detail').inner_text()}
            run('unknown_ID_deep_link', unknown)

            def fulltext():
                page.goto(base + 'library.html'); page.wait_for_selector('.library-hit')
                count = page.locator('#libraryResultCount').inner_text()
                page.select_option('#coverage', 'full_text'); page.wait_for_selector('.library-hit')
                page.locator('.library-hit').first.click(); page.wait_for_selector('.library-article')
                paragraphs = page.locator('.library-article').count()
                require(paragraphs > 0, 'Full text does not render')
                page.fill('#textQuery', '安全'); page.locator('#librarySearch button[type=submit]').click()
                expect(page.locator('#libraryResultCount')).to_contain_text('处匹配')
                return {'catalog': count, 'paragraphs': paragraphs, 'search': page.locator('#libraryResultCount').inner_text()}
            run('fulltext_catalog_read_and_search', fulltext)

            def upcoming():
                page.goto(base + 'library.html'); page.wait_for_selector('.library-hit')
                page.select_option('#validityFilter', '即将生效'); page.wait_for_selector('.library-hit')
                page.locator('.library-hit').first.click(); page.wait_for_selector('#libraryDetail h2')
                text = page.locator('#libraryDetail').inner_text()
                require('尚未实施' in text, 'Upcoming standard shown as current')
                return {'title': page.locator('#libraryDetail h2').inner_text()}
            run('upcoming_not_current', upcoming)

            def mobile_check():
                mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, service_workers='block')
                mp = mobile.new_page(); mp.goto(base); mp.wait_for_selector('#list .card'); mp.wait_for_selector('#detail h2')
                width = mp.evaluate('document.documentElement.scrollWidth')
                require(width <= 391, f'Mobile horizontal overflow: {width}')
                mp.fill('#search', '灭火器'); mp.wait_for_selector('#list .card')
                mp.locator('#list .card').first.click(); mp.wait_for_selector('#detail h2')
                result = {'viewport': 390, 'documentWidth': width, 'count': mp.locator('#count').inner_text()}
                mobile.close(); return result
            run('mobile_390px_search_and_detail', mobile_check)
            run('no_unhandled_javascript_errors', lambda: require(not page_errors, str(page_errors)))
            context.close(); browser.close()
    finally:
        if server:
            server.shutdown()
        report['seconds'] = round(time.monotonic() - started, 3)
        report['passed'] = sum(item['pass'] for item in report['checks'])
        report['failed'] = sum(not item['pass'] for item in report['checks'])
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if args.observe or report['failed'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
