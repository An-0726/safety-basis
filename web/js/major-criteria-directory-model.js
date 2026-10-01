// Pure metadata-only directory. A returned group always contains its primary
// and every supplement; none of these records is a reviewed finding or clause.
const ROOT_KEYS = ['schemaVersion', 'catalogScope', 'allIndustryCoverage',
  'wholeNormNotFieldFinding', 'asOf', 'notice', 'directoryGroupCount', 'documentCount',
  'directoryGroups', 'entries'];
const GROUP_KEYS = ['id', 'label', 'primaryReferenceId', 'documentIds'];
const ENTRY_KEYS = ['directoryGroup', 'requiredCompanionIds', 'scopeCaveat',
  'supplementsReferenceId', 'lawVersionId', 'scopeHint', 'officialLink', 'criterionKind',
  'officialTextLink', 'effectiveDateNote', 'referenceStatus', 'legalNature', 'id',
  'statusAsOf', 'lawId', 'title', 'documentNumber', 'versionKey', 'issuer', 'documentKind',
  'publicationDate', 'effectiveDate', 'statusLabel', 'checked', 'contentKind', 'textMode',
  'publicationPermission', 'fullTextReviewed', 'fullQuotePublicationReady',
  'publicationReady', 'reviewedClauseCount', 'directHazardCount', 'searchTopicCount',
  'standaloneDeterminationAllowed', 'wholeStandardComplete'];
const STATUS_LABELS = new Map([['current', '现行有效'], ['current_in_use', '现行使用中']]);

function check(condition, code) {
  if (!condition) throw new Error(`重大隐患目录数据校验失败：${code}`);
}

// JSON records only: no extensions, symbols, hidden payloads, or accessors.
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

const text = value => typeof value === 'string' && value.trim() === value &&
  value.length > 0 && !/\p{Cc}/u.test(value);
const shortText = (value, maximum, empty = false) =>
  (empty && value === '') || (text(value) && [...value].length <= maximum);
const id = value => typeof value === 'string' && /^[A-Za-z0-9_]+$/u.test(value);

function unique(seen, value, code) {
  check(!seen.has(value), code);
  seen.add(value);
}

function ids(value, code, nonempty = false) {
  array(value, code);
  check((!nonempty || value.length > 0) && value.every(id) &&
    new Set(value).size === value.length, code);
}

function dateText(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(value) || value.startsWith('0000')) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function checkedText(value) {
  if (dateText(value)) return true;
  if (typeof value !== 'string' || !dateText(value.slice(0, 10))) return false;
  return /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/u.test(value) &&
    Number.isFinite(Date.parse(value));
}

function officialUrl(value) {
  if (!text(value) || /[\s\\\p{Cf}]/u.test(value) || /%(?:0[0-9a-f]|1[0-9a-f]|7f)/i.test(value)) return false;
  // Check the raw authority as well: URL.port discards an explicit :443.
  const authority = value.match(/^https:\/\/([^/?#]+)(?:[/?#]|$)/iu)?.[1];
  if (!authority || !/^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+gov\.cn$/iu.test(authority)) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password && !url.port &&
      url.hostname.toLowerCase() === authority.toLowerCase();
  } catch { return false; }
}

/** Validate the fixed public schema and the entire reciprocal directory graph.
 * expectedAsOf is the independently verified release date, when supplied.
 * checked certifies metadata review only. The original object is returned.
 */
export function validateMajorDirectory(data, expectedAsOf) {
  record(data, ROOT_KEYS, 'DIRECTORY');
  check(data.schemaVersion === 'safety-major-criteria-directory-v1', 'SCHEMA');
  check(dateText(data.asOf), 'AS_OF');
  if (expectedAsOf !== undefined) {
    check(dateText(expectedAsOf) && data.asOf === expectedAsOf, 'EXPECTED_SNAPSHOT_MISMATCH');
  }
  check(data.catalogScope === 'controlled_official_metadata_directory' &&
    data.allIndustryCoverage === false && data.wholeNormNotFieldFinding === true && text(data.notice), 'CATALOG_BOUNDARY');
  array(data.directoryGroups, 'DIRECTORY_GROUPS');
  array(data.entries, 'ENTRIES');
  check(Number.isSafeInteger(data.directoryGroupCount) && data.directoryGroupCount >= 0 &&
    data.directoryGroupCount === data.directoryGroups.length, 'DIRECTORY_GROUP_COUNT');
  check(Number.isSafeInteger(data.documentCount) && data.documentCount >= 0 &&
    data.documentCount === data.entries.length, 'DOCUMENT_COUNT');

  const groups = new Map(), entries = new Map(), lawIds = new Set(), versionIds = new Set();
  for (const group of data.directoryGroups) {
    record(group, GROUP_KEYS, 'GROUP');
    check(id(group.id) && id(group.primaryReferenceId) && text(group.label), 'GROUP_METADATA');
    check(!groups.has(group.id), 'DUPLICATE_GROUP_ID');
    ids(group.documentIds, 'GROUP_DOCUMENT_IDS', true);
    groups.set(group.id, group);
  }
  for (const entry of data.entries) {
    record(entry, ENTRY_KEYS, 'ENTRY');
    check(id(entry.id) && id(entry.lawId) && id(entry.lawVersionId) && id(entry.criterionKind), 'ENTRY_ID');
    check(!entries.has(entry.id), 'DUPLICATE_ENTRY_ID');
    unique(lawIds, entry.lawId, 'DUPLICATE_LAW_ID');
    unique(versionIds, entry.lawVersionId, 'DUPLICATE_VERSION_ID');
    check(['title', 'documentNumber', 'versionKey', 'issuer', 'documentKind', 'legalNature']
      .every(key => text(entry[key])), 'ENTRY_METADATA');
    check(shortText(entry.scopeHint, 240) && shortText(entry.scopeCaveat, 240) &&
      shortText(entry.effectiveDateNote, 180, true), 'ENTRY_SCOPE');
    record(entry.directoryGroup, ['id', 'label', 'role'], 'ENTRY_GROUP');
    check(id(entry.directoryGroup.id) && shortText(entry.directoryGroup.label, 48) &&
      ['primary', 'supplement'].includes(entry.directoryGroup.role), 'ENTRY_GROUP_METADATA');
    const group = groups.get(entry.directoryGroup.id);
    check(group && group.label === entry.directoryGroup.label, 'ENTRY_GROUP_IDENTITY');
    ids(entry.requiredCompanionIds, 'REQUIRED_COMPANION_IDS');
    check(!entry.requiredCompanionIds.includes(entry.id) &&
      (entry.supplementsReferenceId === null || id(entry.supplementsReferenceId)) &&
      entry.supplementsReferenceId !== entry.id, 'COMPANION_REFERENCES');
    check(entry.directoryGroup.role === 'primary'
      ? entry.supplementsReferenceId === null
      : entry.supplementsReferenceId !== null && entry.requiredCompanionIds.length === 0, 'COMPANION_ROLE');
    check(STATUS_LABELS.has(entry.referenceStatus) &&
      STATUS_LABELS.get(entry.referenceStatus) === entry.statusLabel, 'REFERENCE_STATUS');
    check(dateText(entry.publicationDate) && entry.publicationDate <= data.asOf &&
      dateText(entry.statusAsOf) && entry.statusAsOf <= data.asOf &&
      checkedText(entry.checked) && entry.checked.slice(0, 10) <= data.asOf, 'ENTRY_DATE');
    check(entry.statusAsOf <= entry.checked.slice(0, 10), 'CURRENTNESS_AFTER_REVIEW');
    check(entry.effectiveDate === null
      ? entry.referenceStatus === 'current_in_use' && text(entry.effectiveDateNote)
      : dateText(entry.effectiveDate) && entry.effectiveDate <= data.asOf, 'EFFECTIVE_DATE');
    check(officialUrl(entry.officialLink) && officialUrl(entry.officialTextLink), 'OFFICIAL_LINK');
    check(entry.contentKind === 'official_document_reference_only' && entry.textMode === 'link_only' &&
      entry.publicationPermission === 'metadata_only' && entry.fullTextReviewed === false &&
      entry.fullQuotePublicationReady === false && entry.reviewedClauseCount === 0 &&
      entry.directHazardCount === 0 && entry.searchTopicCount === 0 &&
      entry.standaloneDeterminationAllowed === false && entry.wholeStandardComplete === false, 'ENTRY_BOUNDARY');
    record(entry.publicationReady, ['metadata', 'fullText'], 'PUBLICATION_READY');
    check(entry.publicationReady.metadata === true && entry.publicationReady.fullText === false, 'PUBLICATION_BOUNDARY');
    entries.set(entry.id, entry);
  }

  for (const group of groups.values()) {
    const members = data.entries.filter(entry => entry.directoryGroup.id === group.id);
    const primaries = members.filter(entry => entry.directoryGroup.role === 'primary');
    check(primaries.length === 1 && primaries[0].id === group.primaryReferenceId, 'GROUP_PRIMARY');
    check(group.documentIds.length === members.length && group.documentIds.every(ident =>
      entries.get(ident)?.directoryGroup.id === group.id), 'GROUP_MEMBERS');
    const primary = primaries[0];
    const supplements = members.filter(entry => entry.directoryGroup.role === 'supplement');
    check(primary.requiredCompanionIds.length === supplements.length &&
      supplements.every(entry => primary.requiredCompanionIds.includes(entry.id) &&
        entry.supplementsReferenceId === primary.id), 'GROUP_COMPANION_GRAPH');
  }
  return data;
}

// Typography normalization is not fuzzy matching or synonym expansion.
const normalize = value => value.normalize('NFKC').toLowerCase()
  .replace(/[〔【﹝(]/gu, '[').replace(/[〕】﹞)]/gu, ']')
  .replace(/[‐‑‒–—−]/gu, '-');

const TECHNICAL = /(?<![a-z0-9/])([a-z]{2,8})(?:\s*\/\s*([a-z]))?\s*([1-9]\d*(?:\.\d+)*)(?:\s*-\s*(\d+)|\s+(\d{4})(?!\d))?(?![a-z0-9./-])/gu;
const ADMINISTRATIVE = /([\u3400-\u9fff]{1,40})\s*\[\s*(\d+)\s*\]\s*(\d+)\s*号(?:\s*\[[^\[\]]+\])?/gu;
const ORDER = /(?:([\u3400-\u9fff]{1,40}令)\s*)?第\s*(\d+)\s*号(?:\s*\[[^\[\]]+\])?/gu;
const compact = value => normalize(value).replace(/\s+/gu, '');

function prepareQuery(value) {
  const technical = [], official = [];
  const remainder = normalize(value).replace(TECHNICAL,
    (_match, family, kind, number, hyphenYear, spacedYear) => {
      technical.push({family: `${family}${kind ? `/${kind}` : ''}`, number,
        year: hyphenYear || spacedYear || ''});
      return ' ';
    }).replace(ADMINISTRATIVE, match => { official.push(compact(match)); return ' '; })
    .replace(ORDER, match => { official.push(compact(match)); return ' '; });
  return {technical, official, terms: remainder.trim().split(/\s+/u).filter(Boolean)};
}

function literalMatch(fields, term) {
  if (!/\d/u.test(term)) return fields.some(field => field.includes(term));
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(?<![a-z0-9.])${escaped}(?![a-z0-9.])`, 'u');
  return fields.some(field => pattern.test(field));
}

function matches(entry, group, query) {
  // A number mentioned in a scope hint or another document's title must not
  // become this document's identity. All designation checks use documentNumber.
  const identity = prepareQuery(entry.documentNumber);
  if (!query.technical.every(wanted => identity.technical.some(available =>
    wanted.family === available.family && wanted.number === available.number &&
    (!wanted.year || wanted.year === available.year)))) return false;
  if (!query.official.every(wanted => literalMatch([compact(entry.documentNumber)], wanted))) return false;
  const fields = [entry.title, entry.documentNumber, group.label, entry.scopeHint].map(normalize);
  return query.terms.every(term => literalMatch(fields, term));
}

/** Literal AND search over a single document's public bibliography/scope only.
 * A match returns its complete group, never an isolated supplement. Counts
 * describe those returned groups and documents, independently of source totals.
 */
export function selectMajorDirectory(data, options = {}) {
  validateMajorDirectory(data);
  const groupId = typeof options?.group === 'string' ? options.group.trim() : '';
  const query = prepareQuery(typeof options?.query === 'string' ? options.query : '');
  const byId = new Map(data.entries.map(entry => [entry.id, entry]));
  const directoryGroups = [];
  for (const group of data.directoryGroups) {
    if (groupId && group.id !== groupId) continue;
    const entries = [group.primaryReferenceId, ...group.documentIds.filter(ident => ident !== group.primaryReferenceId)]
      .map(ident => byId.get(ident));
    if (entries.some(entry => matches(entry, group, query))) {
      directoryGroups.push({...group, documentIds: [...group.documentIds], entries});
    }
  }
  return {directoryGroups, directoryGroupCount: directoryGroups.length,
    documentCount: directoryGroups.reduce((count, group) => count + group.entries.length, 0)};
}
