#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real-browser check that the site shows what the data says.

Expectations are read from the site's own published data, so nothing has to be
frozen per batch. By default it opens the rules named by --ids plus an evenly
spaced sample of all public rules; --all opens every public rule.

  python tools/checks/browser_smoke.py --bundle source/releases/current --ids H_A,H_B --out report.json
  python tools/checks/browser_smoke.py --url https://example.org/site/ --expected-commit <sha> --out report.json
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import quote
from urllib.request import urlopen

MOBILE_WIDTH, DESKTOP_WIDTH = 390, 1440
EXTRA_LIMIT = 40  # most rules that also get the search and phone-width checks


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def fetch_json(base, relative):
    with urlopen(base + relative, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def shard_records(base, kind, count):
    records = {}
    for index in range(count):
        for record in fetch_json(base, f'data/{kind}/{kind[0]}{index:04d}.json')['records']:
            records[record['id']] = record
    return records


def compact(text):
    return re.sub(r'\s+', '', text or '')


def choose(all_ids, named, sample):
    ordered = sorted(all_ids)
    step = max(1, len(ordered) // sample) if sample else len(ordered) + 1
    spaced = ordered[::step][:sample] if sample else []
    return list(dict.fromkeys(named + spaced))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--bundle', type=Path)
    source.add_argument('--url')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ids', default='', help='Comma-separated hazard ids that must be opened')
    parser.add_argument('--sample', type=int, default=24)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--expected-commit')
    parser.add_argument('--wait-for-commit', type=int, default=0, metavar='SECONDS')
    parser.add_argument('--executable')
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright

    server = None
    if args.bundle:
        bundle = args.bundle.resolve(strict=True)
        server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(bundle.parent)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/{quote(bundle.name)}/'
    else:
        base = args.url.rstrip('/') + '/'

    failures, checked = [], 0

    def require(condition, message):
        if not condition:
            failures.append(message)
        return condition

    deadline = time.monotonic() + args.wait_for_commit
    while True:
        manifest = fetch_json(base, f'data/manifest.json?t={int(time.time())}')
        version = manifest.get('dataVersion', '')
        if not args.expected_commit or args.expected_commit[:12] in version or time.monotonic() >= deadline:
            break
        time.sleep(15)
    if args.expected_commit:
        require(args.expected_commit[:12] in version, f'Site serves {version}, expected commit {args.expected_commit[:12]}')
    counts = manifest['counts']
    listing = urlopen(base + 'site-manifest.json', timeout=30).read().decode('utf-8')
    shards = {kind: len(set(re.findall(rf'data/{kind}/{kind[0]}\d{{4}}\.json', listing))) for kind in ('hazards', 'clauses')}
    hazards = shard_records(base, 'hazards', shards['hazards'])
    clauses = shard_records(base, 'clauses', shards['clauses'])
    require(len(hazards) == counts['hazards'], f'{len(hazards)} hazard records, manifest says {counts["hazards"]}')
    named = [value for value in args.ids.split(',') if value]
    for hazard_id in named:
        require(hazard_id in hazards, f'{hazard_id} is not published')
    named = [hazard_id for hazard_id in named if hazard_id in hazards]
    targets = sorted(hazards) if args.all else choose(hazards, named, args.sample)

    with sync_playwright() as playwright:
        options = {'headless': True}
        if args.executable:
            options['executable_path'] = args.executable
        browser = playwright.chromium.launch(**options)
        context = browser.new_context(viewport={'width': DESKTOP_WIDTH, 'height': 1000}, service_workers='block')
        page = context.new_page()
        page.set_default_timeout(15000)
        page_errors = []
        page.on('pageerror', lambda error: page_errors.append(str(error)))

        def open_detail(hazard_id):
            page.goto(base + '?id=' + quote(hazard_id), wait_until='domcontentloaded')
            page.wait_for_function(
                '(title) => document.querySelector("#detail h2")?.innerText.trim() === title',
                arg=hazards[hazard_id]['title'].strip())

        page.goto(base, wait_until='domcontentloaded')
        page.wait_for_function('() => /^[1-9][0-9]*$/.test(document.querySelector("#count")?.innerText.trim() || "")')

        for hazard_id in targets:
            record = hazards[hazard_id]
            try:
                open_detail(hazard_id)
                shown = page.locator('#detail .basis').evaluate_all('(rows) => rows.map((row) => row.dataset.linkId)')
                expected = [ref['linkId'] for ref in record['basisRefs']]
                require(sorted(shown) == sorted(expected), f'{hazard_id}: basis shown {shown}, data has {expected}')
                body = compact(page.locator('#detail').inner_text())
                for field in ('description', 'measures'):
                    require(compact(record[field]) in body, f'{hazard_id}: {field} text is not shown as published')
                for ref in record['basisRefs']:
                    quote_text = clauses[ref['clauseId']].get('quote') or ''
                    if '|' in quote_text or not quote_text:
                        continue
                    first_line = compact(quote_text.split('\n')[0])[:40]
                    block = page.locator(f'#detail .basis[data-link-id="{ref["linkId"]}"]')
                    require(first_line in compact(block.inner_text()),
                            f'{hazard_id}: clause {ref["clauseId"]} quote is not shown as published')
                checked += 1
            except Exception as error:
                failures.append(f'{hazard_id}: {str(error).splitlines()[0]}')

        searched = (named + [t for t in targets if t not in named])[:min(max(len(named), 6), EXTRA_LIMIT)]
        for hazard_id in searched:
            title = hazards[hazard_id]['title'].strip()
            try:
                page.goto(base, wait_until='domcontentloaded')
                page.fill('#search', title)
                page.wait_for_function(
                    '(title) => [...document.querySelectorAll("#list .card")].some((card) => card.innerText.includes(title))',
                    arg=title)
            except Exception as error:
                failures.append(f'{hazard_id}: searching its title does not list it ({str(error).splitlines()[0]})')

        page.set_viewport_size({'width': MOBILE_WIDTH, 'height': 844})
        for hazard_id in (named + targets[:4])[:min(max(len(named), 4), EXTRA_LIMIT)]:
            try:
                open_detail(hazard_id)
                require(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),
                        f'{hazard_id}: page overflows sideways on a phone')
            except Exception as error:
                failures.append(f'{hazard_id} (phone): {str(error).splitlines()[0]}')

        page.set_viewport_size({'width': DESKTOP_WIDTH, 'height': 1000})
        for name in ('library.html', 'major-criteria.html'):
            try:
                page.goto(base + name, wait_until='load')
                require(page.locator('body').inner_text().strip(), f'{name} is empty')
            except Exception as error:
                failures.append(f'{name}: {str(error).splitlines()[0]}')
        for error in page_errors:
            failures.append(f'page script error: {error}')
        browser.close()
    if server:
        server.shutdown()

    report = {'target': base, 'dataVersion': version, 'publicHazards': len(hazards), 'opened': checked,
              'named': named, 'failures': failures}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('target', 'dataVersion', 'publicHazards', 'opened')}, ensure_ascii=False))
    for failure in failures:
        print('FAIL', failure)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
