"""Bind a static module graph and its HTML to the exact data release.

Only local JavaScript/CSS references are versioned. Navigation links, official
sources, data URLs and legal text are left intact. Source templates remain
readable/runnable without a build; public bundles use one version everywhere.
"""
import re
from urllib.parse import quote

VERSION_MARKER = '__SAFETY_BASIS_DATA_VERSION__'
_JS_IMPORT = re.compile(
    r'''((?:\bfrom\s+|\bimport\s*(?:\(\s*)?)["'])(\.[^"'\s?#]+\.js)(["'])''')
_HTML_ASSET = re.compile(r'''((?:src|href)=["'])([^"'\s?#]+\.(?:js|css))(["'])''')


def render_web_asset(asset, content, data_version):
    """Return deterministic bytes; this function never evaluates source code."""
    if not asset.endswith(('.html', '.js', '.css')):
        return content
    if not isinstance(data_version, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', data_version):
        raise ValueError('dataVersion must be a bounded, URL-safe build identity')
    text = content.decode('utf-8').replace(VERSION_MARKER, data_version)
    suffix = '?v=' + quote(data_version, safe='')

    def versioned(match):
        prefix, target, end = match.groups()
        if target.startswith('//') or re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', target):
            return match.group(0)
        return prefix + target + suffix + end

    if asset.endswith('.js'):
        text = _JS_IMPORT.sub(versioned, text)
    elif asset.endswith('.html'):
        text = _HTML_ASSET.sub(versioned, text)
        if 'name="safety-basis-version"' not in text:
            text = text.replace('</head>', '<meta name="safety-basis-version" content="' + data_version + '">\n</head>', 1)
    return text.encode('utf-8')
