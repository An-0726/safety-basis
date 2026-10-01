// Strict, ordered official text/table content. Tabs/newlines are the complete
// plain-text fallback; cell coordinates and spans retain the original mapping.
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const keys = (x, names) => object(x) && Object.keys(x).sort().join(',') === [...names].sort().join(',');
const text = (x, limit) => typeof x === 'string' && Boolean(x.trim()) && x.length <= limit && !/[\x00-\x09\x0b-\x1f]/u.test(x);
const integer = (x, low, high) => Number.isSafeInteger(x) && x >= low && x <= high;
const check = (ok, code) => { if (!ok) throw new Error(`规范正文结构校验失败：${code}`); };

function grid(rows, columns, limit) {
  check(Array.isArray(rows) && rows.length > 0 && rows.length <= limit, 'ROWS');
  const occupied = rows.map(() => Array(columns).fill(false));
  const plain = rows.map(() => Array(columns).fill(''));
  rows.forEach((row, r) => {
    check(Array.isArray(row) && row.length > 0 && row.length <= columns, 'ROW_CELLS');
    let column = 0;
    for (const cell of row) {
      check(keys(cell, ['text', 'colSpan', 'rowSpan']) && text(cell.text, 1000), 'CELL');
      check(integer(cell.colSpan, 1, columns) && integer(cell.rowSpan, 1, rows.length), 'SPAN');
      while (column < columns && occupied[r][column]) column++;
      check(column + cell.colSpan <= columns && r + cell.rowSpan <= rows.length, 'SPAN_BOUNDS');
      for (let rr = r; rr < r + cell.rowSpan; rr++) for (let cc = column; cc < column + cell.colSpan; cc++) {
        check(!occupied[rr][cc], 'SPAN_OVERLAP'); occupied[rr][cc] = true;
      }
      plain[r][column] = cell.text; column += cell.colSpan;
    }
    check(occupied[r].every(Boolean), 'GRID_HOLE');
  });
  return plain.map(row => row.join('\t')).join('\n');
}

export function normativeContentText(parts) {
  check(Array.isArray(parts) && parts.length > 0 && parts.length <= 100, 'PARTS');
  check(object(parts[0]) && parts[0].type === 'text', 'FIRST_TEXT');
  const output = [], seen = new Set();
  for (const part of parts) {
    check(object(part), 'PART');
    if (part.type === 'text') {
      check(keys(part, ['type', 'text']) && text(part.text, 50000), 'TEXT');
      output.push(part.text); continue;
    }
    check(keys(part, ['type', 'id', 'caption', 'columnCount', 'headerRows', 'bodyRows', 'sourcePages']) && part.type === 'table', 'TABLE_FIELDS');
    check(typeof part.id === 'string' && /^[A-Za-z0-9_]+$/u.test(part.id) && !seen.has(part.id), 'TABLE_ID');
    seen.add(part.id);
    check(text(part.caption, 500) && integer(part.columnCount, 1, 12), 'CAPTION_OR_COLUMNS');
    check(Array.isArray(part.sourcePages) && part.sourcePages.length > 0 && part.sourcePages.every((p, i, a) =>
      integer(p, 1, 1000) && (i === 0 || p > a[i - 1])), 'PAGES');
    output.push(`${part.caption}\n${grid(part.headerRows, part.columnCount, 4)}\n${grid(part.bodyRows, part.columnCount, 200)}`);
  }
  return output.join('\n');
}

export function validateNormativeClause(clause) {
  if (!Object.hasOwn(clause, 'contentParts')) return [];
  check(normativeContentText(clause.contentParts) === clause.quote, 'QUOTE_FALLBACK_MISMATCH');
  const ids = clause.contentParts.filter(part => part.type === 'table').map(part => part.id);
  check(ids.length > 0, 'TABLE_REQUIRED');
  return ids;
}

const escape = x => String(x).replace(/[&<>"']/gu, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
// The only display substitution is a linearized half-power in an official unit.
const mathText = x => escape(x).replaceAll('^(1/2)', '<sup>1/2</sup>');

export function renderNormativeContent(clause) {
  validateNormativeClause(clause);
  if (!clause.contentParts) return `<blockquote>${escape(clause.quote)}</blockquote>`;
  return `<div class="normative-content" aria-label="规范原文">${clause.contentParts.map(part => {
    if (part.type === 'text') return `<blockquote>${escape(part.text)}</blockquote>`;
    const rows = (value, heading) => value.map(row => `<tr>${row.map(cell => {
      const tag = heading ? 'th' : 'td';
      return `<${tag} colspan="${cell.colSpan}" rowspan="${cell.rowSpan}">${mathText(cell.text)}</${tag}>`;
    }).join('')}</tr>`).join('');
    return `<div class="normative-table-region" role="region" tabindex="0" aria-label="${escape(part.caption)}"><table class="normative-table"><caption>${escape(part.caption)}</caption><thead>${rows(part.headerRows, true)}</thead><tbody>${rows(part.bodyRows, false)}</tbody></table></div><p class="normative-table-source">原PDF第 ${part.sourcePages.join('、')} 页；横向滚动可查看完整表格</p>`;
  }).join('')}</div>`;
}
