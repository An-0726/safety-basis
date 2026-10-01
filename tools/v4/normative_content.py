"""Lossless plain-text fallback and strict layout for official embedded tables.

Only source cell text is serialized; tabs/newlines represent layout. Row/column
spans are validated as a complete grid and never silently flattened or guessed.
"""
import re

IDENT = re.compile(r'^[A-Za-z0-9_]+$')


def _text(value, limit):
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= limit and
            not any(ord(c) < 32 and c != '\n' for c in value))


def _require(ok, code):
    if not ok:
        raise ValueError('NORMATIVE_CONTENT_' + code)


def _grid(rows, columns, limit):
    _require(isinstance(rows, list) and 0 < len(rows) <= limit, 'ROWS')
    occupied = [[False] * columns for _ in rows]
    plain = [[''] * columns for _ in rows]
    for r, row in enumerate(rows):
        _require(isinstance(row, list) and 0 < len(row) <= columns, 'ROW_CELLS')
        column = 0
        for cell in row:
            _require(isinstance(cell, dict) and set(cell) == {'text', 'colSpan', 'rowSpan'} and
                     _text(cell['text'], 1000), 'CELL')
            cs, rs = cell['colSpan'], cell['rowSpan']
            _require(type(cs) is int and type(rs) is int and cs >= 1 and rs >= 1, 'SPAN')
            while column < columns and occupied[r][column]:
                column += 1
            _require(column + cs <= columns and r + rs <= len(rows), 'SPAN_BOUNDS')
            for rr in range(r, r + rs):
                for cc in range(column, column + cs):
                    _require(not occupied[rr][cc], 'SPAN_OVERLAP')
                    occupied[rr][cc] = True
            plain[r][column] = cell['text']
            column += cs
        _require(all(occupied[r]), 'GRID_HOLE')
    return '\n'.join('\t'.join(row) for row in plain)


def content_text(parts):
    """Validate an ordered body and return its complete, deterministic fallback."""
    _require(isinstance(parts, list) and 0 < len(parts) <= 100, 'PARTS')
    _require(isinstance(parts[0], dict) and parts[0].get('type') == 'text', 'FIRST_TEXT')
    texts, seen = [], set()
    for part in parts:
        _require(isinstance(part, dict), 'PART')
        if part.get('type') == 'text':
            _require(set(part) == {'type', 'text'} and _text(part['text'], 50000), 'TEXT')
            texts.append(part['text'])
            continue
        _require(set(part) == {'type', 'id', 'caption', 'columnCount', 'headerRows', 'bodyRows', 'sourcePages'} and
                 part.get('type') == 'table', 'TABLE_FIELDS')
        ident = part['id']
        _require(isinstance(ident, str) and IDENT.fullmatch(ident) and ident not in seen, 'TABLE_ID')
        seen.add(ident)
        _require(_text(part['caption'], 500), 'CAPTION')
        columns = part['columnCount']
        _require(type(columns) is int and 1 <= columns <= 12, 'COLUMNS')
        pages = part['sourcePages']
        _require(isinstance(pages, list) and pages and all(type(p) is int and 1 <= p <= 1000 for p in pages) and
                 pages == sorted(set(pages)), 'PAGES')
        head = _grid(part['headerRows'], columns, 4)
        body = _grid(part['bodyRows'], columns, 200)
        texts.append(part['caption'] + '\n' + head + '\n' + body)
    return '\n'.join(texts)


def validate_clause_content(clause, required_table_ids):
    """The independently reviewed selection declares the exact required tables."""
    if 'contentParts' not in clause:
        _require(not required_table_ids, 'REQUIRED_TABLE_MISSING')
        return []
    parts = clause['contentParts']
    plain = content_text(parts)
    table_ids = [p['id'] for p in parts if p['type'] == 'table']
    _require(table_ids and table_ids == required_table_ids, 'CONTROLLED_TABLE_MEMBERSHIP')
    _require(clause.get('quote') == plain, 'QUOTE_FALLBACK_MISMATCH')
    return table_ids
