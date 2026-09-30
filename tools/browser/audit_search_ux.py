"""Local-only Chromium regression for search, clue taxonomy, routes and accessibility.

Reads a built bundle and writes QA evidence outside it. No external websites,
publication or knowledge writes. Requires installed Playwright and Chromium.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
from urllib.parse import quote, parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--executable', default='/usr/bin/chromium')
    args = parser.parse_args()
    bundle = args.bundle.resolve(strict=True)
    if not (bundle / 'release.json').is_file():
        raise SystemExit('A generated local release bundle is required')
    args.out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((bundle / 'data/search-index.json').read_text())
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(bundle.parent)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/{quote(bundle.name)}/'
    report = {'target': 'local generated bundle', 'checks': [], 'hazards': len(rows)}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=args.executable, headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))

            def check(name, fn):
                try:
                    evidence = fn()
                    result = {'name': name, 'pass': True, 'evidence': evidence}
                except Exception as error:
                    result = {'name': name, 'pass': False, 'error': str(error)}
                report['checks'].append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)

            def home(suffix=''):
                page.goto(base + suffix)
                expect(page.locator('#count')).not_to_have_text('0')
                page.wait_for_selector('#detail h2')

            def primary_controls():
                home()
                expect(page.get_by_label('专业分类', exact=True)).to_be_visible()
                expect(page.locator('#region')).to_be_visible()
                expect(page.locator('#scene')).not_to_be_visible()
                expect(page.locator('#hazardMoreFilters')).not_to_have_attribute('open', '')
                assert page.locator('#hazardFilters > label').count() == 2
                available = {tag for row in rows for tag in row['sceneTags']}
                options = set(page.locator('#scene option').evaluate_all('(nodes)=>nodes.map(node=>node.value)'))
                assert options == available | {'', '未细分场景'}, options - available
                page.screenshot(path=str(args.out / 'desktop-search.png'), full_page=True)
                return {'visiblePrimaryFilters': 2, 'sceneOptions': len(available), 'emptySceneOptions': 0}
            check('primary_search_category_region_and_no_empty_scene_options', primary_controls)

            def scene_filter():
                home()
                page.locator('#hazardMoreFilters summary').click()
                page.select_option('#scene', '配电室与配电装置')
                expected = [row['id'] for row in rows if '配电室与配电装置' in row['sceneTags']]
                expect(page.locator('#count')).to_have_text(str(len(expected)))
                actual = page.locator('#list .card').evaluate_all('(nodes)=>nodes.map(node=>node.dataset.id)')
                assert set(actual) == set(expected)
                assert 'H_ELECTRICAL_ROOM_SMALL_ANIMAL_PROTECTION' in actual
                assert 'H001' not in actual
                expect(page.locator('#hazardFilterCount')).to_have_text('（1）')
                page.locator('#hazardMoreFilters summary').click()
                expect(page.get_by_role('button', name='移除现场标签：配电室与配电装置')).to_be_visible()
                expect(page.locator('#scene')).not_to_be_visible()
                page.screenshot(path=str(args.out / 'desktop-scene-filter.png'), full_page=True)
                page.reload()
                expect(page.locator('#scene')).to_be_visible()
                expect(page.locator('#scene')).to_have_value('配电室与配电装置')
                page.get_by_role('button', name='移除现场标签：配电室与配电装置').click()
                expect(page.locator('#scene')).to_have_value('')
                expect(page.locator('#count')).to_have_text(str(len(rows)))
                return {'matchingStableIds': actual, 'sharedFilterRestored': True, 'removableWhileCollapsed': True}
            check('source_grounded_scene_filter_share_reload_remove', scene_filter)

            def compound_and_clear():
                home()
                page.fill('#search', '安全员 培训')
                expect(page.locator('#count')).not_to_have_text('0')
                assert '安全员' in page.locator('#search').input_value()
                page.select_option('#category', '特种设备')
                expect(page.locator('#category')).to_have_value('特种设备')
                page.locator('#clear').click()
                expect(page.locator('#search')).to_have_value('')
                expect(page.locator('#category')).to_have_value('特种设备')
                assert page.locator('#search').evaluate('node=>node===document.activeElement')
                category_count = int(page.locator('#count').inner_text())
                page.locator('#reset').click()
                expect(page.locator('#category')).to_have_value('')
                expect(page.locator('#count')).to_have_text(str(len(rows)))
                page.go_back()
                expect(page.locator('#category')).to_have_value('特种设备')
                expect(page.locator('#count')).to_have_text(str(category_count))
                page.go_forward()
                expect(page.locator('#category')).to_have_value('')
                return {'clearKeepsFilters': True, 'resetAndHistoryRestore': True}
            check('query_clear_reset_back_forward', compound_and_clear)

            def explained_search():
                home()
                page.fill('#search', '灭活器')
                expect(page.locator('#searchNotice')).to_contain_text('纠错')
                expect(page.locator('#searchNotice')).to_contain_text('灭火器')
                expect(page.locator('#search')).to_have_value('灭活器')
                assert parse_qs(urlparse(page.url).query)['q'] == ['灭活器']
                page.fill('#search', '灭火器')
                expect(page.locator('#searchNotice')).not_to_be_visible()
                page.fill('#search', '不可能匹配的测试词ZYX8923')
                expect(page.locator('#count')).to_have_text('0')
                expect(page.locator('#list')).to_contain_text('未检索到不代表不存在相关要求')
                return {'typoNotice': True, 'originalQueryPreserved': True, 'emptyNotNoLegalDuty': True}
            check('transparent_typo_and_safe_empty_state', explained_search)

            def phone():
                page.set_viewport_size({'width': 390, 'height': 844})
                home()
                for selector in ['#category', '#region', '#hazardMoreFilters summary']:
                    assert page.locator(selector).bounding_box()['height'] >= 44, selector
                page.locator('#hazardMoreFilters summary').click()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.select_option('#scene', '叉车与场车')
                page.locator('#hazardMoreFilters summary').click()
                page.locator('#list .card').first.click()
                page.locator('#backResults').click()
                assert page.locator('#list').evaluate('node=>node===document.activeElement')
                page.screenshot(path=str(args.out / 'mobile-search.png'), full_page=True)
                return {'width': 390, 'overflow': False, 'primaryTargetsAtLeast44px': True, 'returnFocus': 'results'}
            check('mobile_filters_and_return_to_results', phone)

            def keyboard():
                page.set_viewport_size({'width': 1440, 'height': 1000})
                home()
                page.locator('body').click(position={'x': 2, 'y': 300})
                page.keyboard.press('/')
                expect(page.locator('#search')).to_be_focused()
                page.locator('#hazardMoreFilters summary').focus()
                page.keyboard.press('Enter')
                expect(page.locator('#scene')).to_be_visible()
                page.keyboard.press('Tab')
                expect(page.locator('#scene')).to_be_focused()
                return {'slashFocus': True, 'nativeDisclosureEnter': True, 'tabReachesScene': True}
            check('keyboard_shortcut_and_progressive_filters', keyboard)

            check('no_unhandled_javascript_errors', lambda: {'errors': errors} if not errors else (_ for _ in ()).throw(AssertionError(errors)))
            browser.close()
    except Exception as error:
        report['checks'].append({'name': 'browser_execution', 'pass': False, 'error': str(error)})
    finally:
        server.shutdown()
        report['passed'] = sum(item['pass'] for item in report['checks'])
        report['failed'] = sum(not item['pass'] for item in report['checks'])
        (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return bool(report['failed'])


if __name__ == '__main__':
    raise SystemExit(main())
