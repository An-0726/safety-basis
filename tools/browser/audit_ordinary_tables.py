#!/usr/bin/env python3
"""Real Chromium ordinary-table regression for a bundle or exact deployed commit.

A launch failure is failed/not-run GUI acceptance, never a visual pass. Source
expectations are frozen separately from Gate and knowledge, never site output.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlparse

from audit_browser import validate_release_identity
from repair_acceptance import DOM_CONTENT_HELPERS, require, require_text, validate_release_match
from complete_remaining_acceptance import load_expectations, fixture_for_release_date
from recovery_release_acceptance import (validate_source_pins, validate_release_source,
    validate_rendered, rendered_snapshot, expected_clipboard, expected_full_clipboard, expected_tables)

HAZARD_ID = 'H_12158_4_2_3_4_1'


def validate_table_geometry(value, width):
    require(value['rows'] == 9, 'Ordinary table must retain exactly all nine body rows')
    require(value['tabIndex'] == 0, 'Ordinary table region lost keyboard focus')
    require(value['pageWidth'] <= width + 1, 'Ordinary table overflows page')
    if width < 540:
        require(value['scroll'] > value['client'], 'Narrow table no longer offers horizontal scroll')
    return value


def validate_law_tables(expected, actual):
    require(len(actual) == len(expected), 'Missing or extra ordinary-law structured clause')
    by_article = {b['article']: b for b in actual}
    require(len(by_article) == len(actual), 'Duplicate structured law article')
    require(set(by_article) == {b['article'] for b in expected}, 'Wrong structured-law clause identities')
    for b in expected:
        shown = by_article[b['article']]
        require_text(shown['quote'], b['quote'], 'Full law table quote')
        require(shown['tables'] == expected_tables(b), 'Law table text, coordinates or spans differ')
    return {'structuredClauses': len(expected), 'tables': sum(len(expected_tables(b)) for b in expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--bundle', type=Path)
    source.add_argument('--url')
    parser.add_argument('--expected-commit')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = {'status': 'failed', 'acceptanceType': 'real_chromium_source_pinned_ordinary_table_UI', 'checks': []}
    server = None
    try:
        frozen_fixture = load_expectations()
        fixture = frozen_fixture
        report['source'] = validate_source_pins(fixture, Path(__file__).resolve().parents[2])
        row = next(r for r in fixture['records'] if r['id'] == HAZARD_ID)
        law_id = row['bases'][0]['lawId']
        law_bases = {b['clauseId']: b for r in fixture['records'] for b in r['bases']
                     if b['lawId'] == law_id and b['contentParts']}
        expected_law = list(law_bases.values())
        require(len(expected_law) >= 2, 'Missing source-pinned ordinary structured law coverage')
        from playwright.sync_api import sync_playwright, expect
        if args.bundle:
            handler = partial(SimpleHTTPRequestHandler, directory=str(args.bundle.resolve(strict=True)))
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_port}/'
        else:
            base = args.url.rstrip('/') + '/'
            require(urlparse(base).scheme in ('http', 'https'), 'Only HTTP(S) sites are supported')
        report['target'] = base
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            report['browserVersion'] = browser.version
            for width in (320, 390, 1280):
                context = browser.new_context(viewport={'width': width, 'height': 900},
                    service_workers='block', permissions=['clipboard-read', 'clipboard-write'])
                page = context.new_page()
                page.set_default_timeout(15000)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                def release_check():
                    nonlocal fixture
                    release = context.request.get(base + 'release.json')
                    manifest = context.request.get(base + 'data/manifest.json')
                    require(release.ok and manifest.ok, 'Missing public release identity')
                    identity = validate_release_identity(release.json(), manifest.json(), args.expected_commit)
                    fixture = fixture_for_release_date(frozen_fixture, release.json().get('asOf'), Path(__file__).resolve().parents[2])
                    validate_release_source(fixture, release.json(), identity['releaseHash'])
                    if report.get('release'):
                        validate_release_match(identity['releaseHash'], report['release']['releaseHash'])
                        require(identity == report['release'], 'Release identity changed during ordinary table flow')
                    report['release'] = identity
                def hazard_check():
                    expect(page.locator('#detail h2')).to_have_text(row['hazard']['title'])
                    validate_rendered(row, rendered_snapshot(page))
                def law_check():
                    expect(page.locator('#detail h2')).to_have_text(row['bases'][0]['lawName'])
                    require(page.evaluate("new URL(location.href).searchParams.get('law')") == law_id, 'Wrong ordinary-law history identity')
                    return validate_law_tables(expected_law, page.evaluate('() => {' + DOM_CONTENT_HELPERS + '''
                        return [...document.querySelectorAll('#detail .basis')].filter(b=>b.querySelector('.normative-content')).map(b=>({article:b.querySelector('.articletitle').innerText,...normative(b)}));}'''))
                try:
                    release_check()
                    page.goto(base + '?id=' + HAZARD_ID, wait_until='domcontentloaded')
                    hazard_check()
                    region = page.locator('#detail .normative-table-region')
                    region.scroll_into_view_if_needed()
                    dims = validate_table_geometry(region.evaluate('''x=>({rows:x.querySelectorAll('tbody tr').length,
                        client:x.clientWidth,scroll:x.scrollWidth,pageWidth:document.documentElement.scrollWidth,
                        tabIndex:x.tabIndex})'''), width)
                    region.focus(); region.press('ArrowRight')
                    if width < 540:
                        page.wait_for_function("() => document.querySelector('#detail .normative-table-region').scrollLeft > 0")
                    scroll_left = region.evaluate('x=>x.scrollLeft')
                    wanted = expected_clipboard(row)
                    for button in ('#copy', '#copyfull', '#copy'):
                        page.locator(button).click()
                        if button == '#copyfull':
                            page.wait_for_function('async want=>(await navigator.clipboard.readText())===want', arg=expected_full_clipboard(row, report['release']['dataVersion']))
                        else:
                            page.wait_for_function('async want=>(await navigator.clipboard.readText())===want', arg=wanted)
                    region.scroll_into_view_if_needed()
                    page.screenshot(path=str(args.out.parent / f'ordinary-table-{width}.png'))
                    page.locator('#detail .lawjump').first.click()
                    law_result = law_check()
                    page.locator('#copylaw').click()
                    page.wait_for_function('async quotes=>{const t=await navigator.clipboard.readText();return quotes.every(q=>t.includes(q));}', arg=[b['quote'] for b in expected_law])
                    require(page.evaluate('document.documentElement.scrollWidth') <= width + 1, 'Law table page overflow')
                    page.screenshot(path=str(args.out.parent / f'ordinary-law-table-{width}.png'), full_page=True)
                    page.go_back(); hazard_check()
                    page.go_forward(); law_check()
                    page.go_back(); hazard_check()
                    page.reload(wait_until='domcontentloaded'); hazard_check()
                    release_check()
                    require(not errors, str(errors))
                    report['checks'].append({'width': width, **dims, 'keyboardScrollLeft': scroll_left,
                        'hazardCopies': 3, **law_result, 'allCellsAndSpansExact': True, 'completeLawCopy': True,
                        'backForwardRestored': True, 'reload': True, 'pageErrors': errors})
                except Exception:
                    try:
                        page.screenshot(path=str(args.out.parent / f'FAILED-ordinary-table-{width}.png'), full_page=True)
                    except Exception:
                        pass
                    raise
                finally:
                    context.close()
            browser.close()
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if server:
            server.shutdown()
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
