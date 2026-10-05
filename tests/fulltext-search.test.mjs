import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeText, queryGrams, intersectDocuments, matchingParagraphs, resolveDocument} from '../web/js/fulltext-search.js';

test('Chinese and full-width references use the same search normalization', () => {
  assert.equal(normalizeText('ＧＢ １２３—２０２６'), 'gb123—2026');
  assert.equal(normalizeText('安\u0085全\ufeff生\u2009产'), '安全生产');
  assert.deepEqual(queryGrams('消防'), ['消防']);
  assert.deepEqual(queryGrams('安全生产'), ['安全', '全生', '生产']);
});

test('gram candidates require final phrase verification', () => {
  assert.deepEqual([...intersectDocuments([['a','b'], ['b','c']])], ['b']);
  assert.deepEqual(matchingParagraphs([{text:'生产单位保证消防通道。'}, {text:'消防设施定期维修。'}], '消防设施'), [{text:'消防设施定期维修。'}]);
  assert.deepEqual(matchingParagraphs([{text:'应当设置'}, {text:'不得设置'}], '不得'), [{text:'不得设置'}]);
});

test('reviewed reading aliases preserve legacy links and canonical IDs win', () => {
  const current = {versionId:'current', versionAliases:['legacy']};
  assert.equal(resolveDocument([current], 'legacy'), current);
  assert.equal(resolveDocument([current], 'current'), current);
  assert.equal(resolveDocument([current], 'missing'), null);
  assert.equal(resolveDocument([current], ''), null);
  assert.equal(resolveDocument(null, 'legacy'), null);
  assert.equal(resolveDocument([{versionId:'x', versionAliases:'legacy'}], 'legacy'), null);
  assert.equal(resolveDocument([current, {versionId:'other', versionAliases:['legacy']}], 'legacy'), null);
  assert.equal(resolveDocument([{versionId:'duplicate'}, {versionId:'duplicate'}], 'duplicate'), null);
  const canonical = {versionId:'legacy'};
  assert.equal(resolveDocument([current, canonical], 'legacy'), canonical);
});
