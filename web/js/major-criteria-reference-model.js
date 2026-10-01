// Pure, isolated model for official bibliography and short locator topics.
// Nothing here grants reviewed-clause status, an H/K association, or a finding.
const ROOT_KEYS = ['schemaVersion', 'asOf', 'catalogScope', 'allIndustryCoverage',
  'wholeNormNotFieldFinding', 'notice', 'referenceEntries'];
const ENTRY_KEYS = ['id', 'lawId', 'lawVersionId', 'title', 'standardNumber', 'versionKey',
  'issuer', 'effectiveDate', 'validityStatus', 'checked', 'officialLink', 'officialTextLink',
  'contentKind', 'textMode', 'publicationPermission', 'fullTextReviewed',
  'fullQuotePublicationReady', 'publicationReady', 'reviewedClauseCount', 'directHazardCount',
  'standaloneDeterminationAllowed', 'wholeStandardComplete', 'searchTopicCount', 'searchTopics'];
const TOPIC_KEYS = ['article', 'searchTopic', 'contentKind', 'isOfficialQuote',
  'standaloneDeterminationAllowed'];
const normalize = value => value.normalize('NFKC').toLowerCase();

function check(condition, code) {
  if (!condition) throw new Error(`重大隐患题录数据校验失败：${code}`);
}

// Require a JSON record with every declared field and no extension payloads.
// Reflect also sees non-enumerable/symbol fields; accessors are not JSON data.
function record(value, keys, code) {
  check(value !== null && typeof value === 'object' && !Array.isArray(value) &&
    [Object.prototype, null].includes(Object.getPrototypeOf(value)), `${code}_OBJECT`);
  const actual = Reflect.ownKeys(value);
  check(actual.length === keys.length && actual.every(key => keys.includes(key)) &&
    keys.every(key => {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      return descriptor && Object.hasOwn(descriptor, 'value') && descriptor.enumerable;
    }), `${code}_FIELDS`);
}

function array(value, code) {
  check(Array.isArray(value), code);
  check(Reflect.ownKeys(value).length === value.length + 1 &&
    Array.from({length: value.length}, (_, index) => index).every(index => {
      const descriptor = Object.getOwnPropertyDescriptor(value, String(index));
      return descriptor && Object.hasOwn(descriptor, 'value') && descriptor.enumerable;
    }), `${code}_FIELDS`);
}

function dateText(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function checkedText(value) {
  if (dateText(value)) return true;
  if (typeof value !== 'string' || !dateText(value.slice(0, 10))) return false;
  // Explicit timezone and bounded clock/offset fields prevent Date.parse's
  // permissive rollover behavior from admitting malformed review timestamps.
  return /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/u.test(value) &&
    Number.isFinite(Date.parse(value));
}

const text = value => typeof value === 'string' && value.trim() === value &&
  value.length > 0 && !/[\u0000-\u001f\u007f]/u.test(value);
const id = value => typeof value === 'string' && /^[A-Za-z0-9_]+$/u.test(value);

function officialUrl(value) {
  if (!text(value) || /[\s\\]/u.test(value) || /%(?:0[0-9a-f]|1[0-9a-f]|7f)/i.test(value)) return false;
  try {
    const url = new URL(value);
    // These public reference records point to Chinese government originals.
    // A suffix boundary excludes lookalikes such as mem.gov.cn.evil.example.
    return url.protocol === 'https:' && !url.username && !url.password && !url.port &&
      /^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+gov\.cn$/i.test(url.hostname);
  } catch { return false; }
}

function designation(value) {
  const match = normalize(value).match(/^([a-z]{2,8})(?:\s*\/\s*([a-z]))?\s*([1-9]\d*(?:\.\d+)*)(?:\s*-\s*(\d{4}))$/u);
  return match && {family: `${match[1]}${match[2] ? `/${match[2]}` : ''}`,
    number: match[3], year: match[4]};
}

function unique(seen, value, code) {
  check(!seen.has(value), code);
  seen.add(value);
}

/** Validate the entire reference-only snapshot; return the unchanged input.
 * checked verifies bibliography/locator topics only, never full-text review.
 * expectedAsOf is the independently verified release snapshot, when supplied.
 */
export function validateMajorReferences(data, expectedAsOf) {
  record(data, ROOT_KEYS, 'REFERENCES');
  check(data.schemaVersion === 'safety-major-criteria-references-v1', 'SCHEMA');
  check(dateText(data.asOf), 'AS_OF');
  if (expectedAsOf !== undefined) {
    check(dateText(expectedAsOf) && data.asOf === expectedAsOf, 'EXPECTED_SNAPSHOT_MISMATCH');
  }
  check(data.catalogScope === 'official_reference_entries_only' && data.allIndustryCoverage === false &&
    data.wholeNormNotFieldFinding === true && text(data.notice), 'CATALOG_BOUNDARY');
  array(data.referenceEntries, 'REFERENCE_ENTRIES');
  const entryIds = new Set(), lawIds = new Set(), versionIds = new Set(), numbers = new Set();
  for (const entry of data.referenceEntries) {
    record(entry, ENTRY_KEYS, 'ENTRY');
    check(id(entry.id) && id(entry.lawId) && id(entry.lawVersionId), 'ENTRY_ID');
    unique(entryIds, entry.id, 'DUPLICATE_ENTRY_ID');
    unique(lawIds, entry.lawId, 'DUPLICATE_LAW_ID');
    unique(versionIds, entry.lawVersionId, 'DUPLICATE_VERSION_ID');
    check(['title', 'standardNumber', 'versionKey', 'issuer'].every(key => text(entry[key])), 'ENTRY_METADATA');
    const number = designation(entry.standardNumber);
    check(number !== null, 'STANDARD_NUMBER');
    unique(numbers, `${number.family}:${number.number}:${number.year}`, 'DUPLICATE_STANDARD_NUMBER');
    check(dateText(entry.effectiveDate) && entry.effectiveDate <= data.asOf &&
      checkedText(entry.checked) && entry.checked.slice(0, 10) <= data.asOf, 'ENTRY_DATE');
    check(entry.validityStatus === 'active', 'VALIDITY_STATUS');
    check(officialUrl(entry.officialLink) && officialUrl(entry.officialTextLink), 'OFFICIAL_LINK');
    check(entry.contentKind === 'reference_only' && entry.textMode === 'link_only' &&
      entry.publicationPermission === 'metadata_only' && entry.fullTextReviewed === false &&
      entry.fullQuotePublicationReady === false && entry.reviewedClauseCount === 0 &&
      entry.directHazardCount === 0 && entry.standaloneDeterminationAllowed === false &&
      entry.wholeStandardComplete === false, 'ENTRY_BOUNDARY');
    record(entry.publicationReady, ['metadata', 'searchTopics', 'fullText'], 'PUBLICATION_READY');
    check(entry.publicationReady.metadata === true && entry.publicationReady.searchTopics === true &&
      entry.publicationReady.fullText === false, 'PUBLICATION_BOUNDARY');
    array(entry.searchTopics, 'SEARCH_TOPICS');
    check(Number.isSafeInteger(entry.searchTopicCount) && entry.searchTopicCount >= 0 &&
      entry.searchTopicCount === entry.searchTopics.length, 'SEARCH_TOPIC_COUNT');
    const articles = new Set();
    for (const topic of entry.searchTopics) {
      record(topic, TOPIC_KEYS, 'TOPIC');
      check(typeof topic.article === 'string' && /^[1-9]\d*(?:\.(?:0|[1-9]\d*))*$/u.test(topic.article), 'ARTICLE');
      unique(articles, topic.article, 'DUPLICATE_ARTICLE');
      // Match the backend short-topic alphabet; only internal ASCII spaces are
      // allowed. No punctuation, markup, quote delimiters, or edge whitespace.
      check(typeof topic.searchTopic === 'string' && /^[\u3400-\u9fffA-Za-z0-9 ]{1,16}$/u.test(topic.searchTopic) &&
        topic.searchTopic.trim() === topic.searchTopic && topic.searchTopic.trim().length > 0, 'SEARCH_TOPIC');
      check(topic.contentKind === 'search_topic_only' && topic.isOfficialQuote === false &&
        topic.standaloneDeterminationAllowed === false, 'TOPIC_BOUNDARY');
    }
  }
  return data;
}

function prepareQuery(value) {
  const standards = [], articles = [];
  const remainder = normalize(value).replace(
    /(?<![a-z0-9/])([a-z]{2,8})(?:\s*\/\s*([a-z]))?\s*([1-9]\d*(?:\.\d+)*)(?:\s*-\s*(\d+))?(?![a-z0-9./-])/gu,
    (_match, family, kind, number, year) => {
      standards.push({family: `${family}${kind ? `/${kind}` : ''}`, number, year: year || ''});
      return ' ';
    }).replace(/(?<![\d.])\d+(?:\.\d+)+(?![\d.])/gu, article => {
    articles.push(article);
    return ' ';
  });
  return {standards, articles, terms: remainder.trim().split(/\s+/u).filter(Boolean)};
}

function literalMatch(fields, term) {
  if (!/\d/u.test(term)) return fields.some(field => field.includes(term));
  // Numeric terms must not leak through prefix matches (3067 != 30670).
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(?<![a-z0-9.])${escaped}(?![a-z0-9.])`, 'u');
  return fields.some(field => pattern.test(field));
}

/** Strict literal AND narrowing over this file only. No shared fuzzy search,
 * alias expansion, hazard search, or inferred on-site meaning is involved.
 * Entry searchTopicCount remains its source total; returned counts are filtered.
 */
export function selectMajorReferences(data, options = {}) {
  validateMajorReferences(data);
  const standard = typeof options?.standard === 'string' ? options.standard.trim() : '';
  const query = prepareQuery(typeof options?.query === 'string' ? options.query : '');
  const referenceEntries = [];
  for (const entry of data.referenceEntries) {
    if (standard && entry.id !== standard) continue;
    const available = designation(entry.standardNumber);
    if (!query.standards.every(wanted => wanted.family === available.family &&
      wanted.number === available.number && (!wanted.year || wanted.year === available.year))) continue;
    const metadata = [entry.title, entry.standardNumber].map(normalize);
    const searchTopics = entry.searchTopics.filter(topic =>
      query.articles.every(article => article === topic.article) &&
      query.terms.every(term => literalMatch([...metadata, normalize(topic.searchTopic), topic.article], term)));
    // A metadata-only record with zero topics remains discoverable as a record.
    if (searchTopics.length || (entry.searchTopics.length === 0 && query.articles.length === 0 &&
      query.terms.every(term => literalMatch(metadata, term)))) {
      referenceEntries.push({...entry, searchTopics});
    }
  }
  return {referenceEntries, referenceStandardCount: referenceEntries.length,
    searchTopicCount: referenceEntries.reduce((sum, entry) => sum + entry.searchTopics.length, 0)};
}
