import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { normativeContentText, renderNormativeContent, validateNormativeClause } from '../web/js/normative-content.js';
const clause = JSON.parse(fs.readFileSync(new URL('../knowledge/clauses/C_GB3836_15_6_4_4.json', import.meta.url)));

test('GB3836.15 Table9 render and copy retain complete mappings and exceptions', () => {
  assert.deepEqual(validateNormativeClause(clause), ['T_GB3836_15_2024_9']);
  assert.equal(normativeContentText(clause.contentParts), clause.quote);
  const html = renderNormativeContent(clause);
  assert.equal((html.match(/<tbody>/gu) || []).length, 1);
  const body = html.split('<tbody>')[1].split('</tbody>')[0];
  assert.equal((body.match(/<tr>/gu) || []).length, 12);
  assert.match(html, /rowspan="2"/u);
  assert.match(html, /colspan="4"/u);
  for (const text of ['IP54','取二者之中的较高级别','仅包含一个本质安全电路','6.4.5','6.4.6','6.4.7','7.3.4','√ᵇ','只对EPL Gc级装置允许','仅在证书条件允许的情况下']) {
    assert.ok(html.includes(text), text);
    assert.ok(clause.quote.includes(text), text);
  }
  assert.ok(clause.quote.includes('Ex“p”（Ⅱ类）\t√\t√\t√ᵇ\t—'));
  assert.ok(clause.quote.includes('Ex“p”（Ⅲ类）\t—\t—\t—\t√'));
});

test('render rejects truncated Table9 column and mismatched fallback', () => {
  const bad = structuredClone(clause);
  bad.contentParts[1].bodyRows[7].pop();
  assert.throws(() => renderNormativeContent(bad), /GRID_HOLE/u);
  const quote = structuredClone(clause);
  quote.quote = 'Truncated';
  assert.throws(() => renderNormativeContent(quote), /QUOTE_FALLBACK_MISMATCH/u);
});
