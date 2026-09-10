export function normalizeText(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+/gu, '');
}

export function queryGrams(query) {
  const chars = Array.from(normalizeText(query));
  const grams = [...new Set(chars.slice(0, -1).map((char, index) => char + chars[index + 1]))];
  if (grams.length <= 3) return grams;
  return [grams[0], grams[Math.floor(grams.length / 2)], grams.at(-1)];
}

export function intersectDocuments(lists) {
  if (!lists.length) return null;
  return new Set(lists[0].filter(id => lists.slice(1).every(list => list.includes(id))));
}

export function matchingParagraphs(paragraphs, query) {
  const needle = normalizeText(query);
  return needle ? paragraphs.filter(row => normalizeText(row.text).includes(needle)) : [];
}
