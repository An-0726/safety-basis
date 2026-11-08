"""Verify a deployed owner-private Site using explicitly synthetic business data.

Supply {"url": "https://<exact deployed origin>", "token": "<Sites service token>"}
on stdin. Tokens are never stored, printed, put in URLs, or forwarded on redirects.
This creates one labelled synthetic project and leaves its report history for review.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_private_input():
    saved = None
    if sys.stdin.isatty():
        import termios
        saved = termios.tcgetattr(sys.stdin)
        hidden = list(saved)
        hidden[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin, termios.TCSANOW, hidden)
        print('Ready for private acceptance JSON on stdin (input is hidden).', flush=True)
    try:
        return json.loads(sys.stdin.readline())
    finally:
        if saved is not None:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, saved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    repository = Path(__file__).resolve().parents[3]
    if output == repository or repository in output.parents:
        raise ValueError('Acceptance downloads must stay outside the public repository')
    params = read_private_input()
    origin = params['url'].rstrip('/')
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme != 'https' or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('Use the exact HTTPS deployed Site origin without a path or credentials')
    token = params['token']
    opener = urllib.request.build_opener(NoRedirect)
    checks = []

    def request(path, *, method='GET', body=None, status=200, authenticated=True):
        if not path.startswith('/api/') or path.startswith('//'):
            raise ValueError('Only same-origin API requests are allowed')
        headers = {'Accept': 'application/json'}
        if authenticated:
            headers['OAI-Sites-Authorization'] = 'Bearer ' + token
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode()
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(origin + path, data=data, headers=headers, method=method)
        try:
            with opener.open(req, timeout=120) as response:
                actual, content, response_headers = response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            actual, content, response_headers = error.code, error.read(), error.headers
        if status is not None and actual != status:
            raise AssertionError(f'{method} {path}: expected {status}, got {actual}')
        return actual, content, response_headers

    def get(path, **kwargs):
        return json.loads(request(path, **kwargs)[1])

    anon, _, _ = request('/api/projects', authenticated=False, status=None)
    assert anon in (301, 302, 303, 307, 308, 401, 403), f'Anonymous business API unexpectedly returned {anon}'
    checks.append('anonymous business records require Sites admission')
    health = get('/api/health')
    assert health['status'] == 'ok' and health['deployment'] == 'private-cloud'
    checks.append('deployed Worker reaches its D1 and verified knowledge bindings')
    meta = get('/api/knowledge/meta')
    assert meta['counts']['hazards'] == 1764 and meta['release_hash']
    for query, expected in [('灭火器前堆放纸箱', 'needs_conditions'), ('氧气瓶没有防震圈', 'evidence_gap'), ('尚未确认压力表损坏', 'fact_unconfirmed')]:
        result = get('/api/knowledge/search?' + urllib.parse.urlencode({'q': query}))
        assert result['assessment']['classification'] == expected
        checks.append('live shared search preserves ' + expected)
    demo = get('/api/demo', method='POST', body={}, status=201)
    project, finding = demo['project'], demo['finding']
    fid, pid = finding['id'], project['id']
    assert finding['status'] == 'draft' and finding['photos'] and all(f['status'] == 'unknown' for f in finding['facts'])
    checks.append('synthetic project, observation and R2 photograph persist as an unconfirmed draft')
    request('/api/findings/' + fid + '/review', method='POST', body={'revision': finding['revision'], 'decision': 'confirm', 'reviewer': '合成验收', 'comment': '只测试阻断'}, status=409)
    checks.append('unknown facts cannot receive professional confirmation')
    draft = get('/api/projects/' + pid + '/reports', method='POST', body={'mode': 'draft'}, status=201)
    checks.append('live Worker exports a marked draft with photo and full law text')
    facts = [{'key': f['key'], 'status': f.get('expected', 'confirmed'), 'note': '自动化功能验收的完全合成事实；不是企业现场调查，也不形成真实专业结论。'} for f in finding['facts']]
    finding = get('/api/findings/' + fid + '/facts', method='PUT', body={'revision': finding['revision'], 'facts': facts})
    for decision in ('submit', 'confirm'):
        finding = get('/api/findings/' + fid + '/review', method='POST', body={'revision': finding['revision'], 'decision': decision, 'reviewer': '功能验收示例（非真实专业审核）', 'comment': '仅验证完全合成样例的工作流，不对应真实企业或专业签章。'})
    assert finding['status'] == 'confirmed'
    report = get('/api/projects/' + pid + '/reports', method='POST', body={'mode': 'confirmed'}, status=201)
    snapshot_bytes = request(report['snapshot_url'])[1]
    snapshot = json.loads(snapshot_bytes)
    checks.append('explicit synthetic facts and review create an immutable confirmed-report snapshot')
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for extension, magic in [('docx', b'PK'), ('pdf', b'%PDF')]:
        _, content, headers = request(report[extension + '_url'])
        assert content.startswith(magic) and 'no-store' in headers.get('Cache-Control', '')
        target = output / ('safety-basis-cloud-example.' + extension)
        target.write_bytes(content)
        artifacts[extension] = {'path': str(target), 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        checks.append('authenticated ' + extension + ' download returns real file bytes with private cache policy')
    with zipfile.ZipFile(artifacts['docx']['path']) as word:
        assert word.testzip() is None and 'word/document.xml' in word.namelist()
        assert any(name.startswith('word/media/') for name in word.namelist())
    from pypdf import PdfReader
    pdf = PdfReader(artifacts['pdf']['path'])
    text = ''.join(page.extract_text() for page in pdf.pages)
    normalized = re.sub(r'\s+', '', text)
    assert re.sub(r'\s+', '', project['company']) in normalized
    assert all(re.sub(r'\s+', '', b['text']) in normalized for b in finding['bases'])
    checks.append('downloaded Word has embedded photo and PDF retains extractable Chinese law text')
    _, backup, _ = request('/api/backup')
    with zipfile.ZipFile(io.BytesIO(backup)) as archive:
        assert archive.testzip() is None and 'workspace.json' in archive.namelist()
        assert any(name.startswith('files/photos/') for name in archive.namelist())
        assert any(name.startswith('files/reports/') for name in archive.namelist())
    checks.append('live private archive contains D1 records, photographs and report files')
    finding = get('/api/findings/' + fid, method='PATCH', body={'revision': finding['revision'], 'notes': '合成验收已完成；此示例重新回到草稿供试用，历史报告留作导出示范。'})
    assert finding['status'] == 'draft' and all(f['status'] == 'unknown' for f in finding['facts'])
    assert request(report['snapshot_url'])[1] == snapshot_bytes
    checks.append('substantive edits invalidate approval while preserving the historical report')
    assert get('/api/projects/' + pid)['id'] == pid
    assert get('/api/findings/' + fid)['photos']
    checks.append('fresh requests retain the project and private objects after the workflow')
    result = {'status': 'passed', 'target': origin, 'checks': checks, 'knowledge': meta,
              'project_id': pid, 'finding_id': fid, 'draft_report_id': draft['id'], 'report_id': report['id'],
              'pdf_pages': len(pdf.pages), 'artifacts': artifacts, 'synthetic_only': True}
    (output / 'live-acceptance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
