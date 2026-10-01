// Pure model for the controlled major-criteria catalog. No DOM, fetch, or app boot.
import {searchLawsDetailed, searchHazardsDetailed, normalize as normalized} from './search.js';
import {administrativeNumberMatches} from './major-criteria-directory-model.js';
import {validateNormativeClause} from './normative-content.js';

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const count = value => Number.isSafeInteger(value) && value >= 0;
const nullableCount = value => value === null || count(value);

function check(condition, code) {
  if (!condition) throw new Error(`重大隐患专题数据校验失败：${code}`);
}

function dateText(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function sourceUrl(value) {
  if (!text(value)) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && Boolean(url.hostname) && !url.username && !url.password;
  } catch { return false; }
}

function ids(value, code) {
  check(Array.isArray(value) && value.every(text), code);
  check(new Set(value).size === value.length, `${code}_DUPLICATE`);
  return new Set(value);
}

function sameIds(left, right) {
  return left.size === right.size && [...left].every(id => right.has(id));
}

/** Validate both same-snapshot projections before exposing any results.
 * searchIndex is the existing public search-index.json array. The returned H
 * objects retain their original category and other public-index fields.
 */
export function validateMajorData(catalog, topic, searchIndex, expectedAsOf) {
  for (const [name, value] of [['CATALOG', catalog], ['TOPIC', topic]]) {
    check(object(value) && value.schemaVersion === 1, `${name}_SCHEMA`);
    check(dateText(value.asOf), `${name}_DATE`);
    check(value.wholeNormNotFieldFinding === true, `${name}_FINDING_BOUNDARY`);
  }
  check(catalog.asOf === topic.asOf, 'SNAPSHOT_MISMATCH');
  if (expectedAsOf !== undefined) {
    check(dateText(expectedAsOf) && catalog.asOf === expectedAsOf, 'EXPECTED_SNAPSHOT_MISMATCH');
  }
  check(catalog.catalogScope === 'controlled_reviewed_standards_only' &&
    catalog.allIndustryCoverage === false, 'CATALOG_SCOPE');
  check(Array.isArray(catalog.standards), 'STANDARDS');
  check(Array.isArray(topic.associations), 'ASSOCIATIONS');
  const topicIds = ids(topic.hazardIds, 'TOPIC_HAZARD_IDS');
  check(Array.isArray(searchIndex), 'SEARCH_INDEX');
  const byHazard = new Map();
  for (const row of searchIndex) {
    check(object(row) && text(row.id) && !byHazard.has(row.id), 'SEARCH_INDEX_ID');
    byHazard.set(row.id, row);
  }

  const byStandard = new Map(), byVersion = new Map(), clauseVersions = new Map(), tableIds = new Set();
  for (const standard of catalog.standards) {
    check(object(standard) && text(standard.id) && !byStandard.has(standard.id), 'STANDARD_ID');
    check(text(standard.lawVersionId) && !byVersion.has(standard.lawVersionId), 'STANDARD_VERSION_ID');
    byStandard.set(standard.id, standard);
    byVersion.set(standard.lawVersionId, standard);
    const version = standard.standardVersion;
    check(object(version) && ['lawId', 'name', 'documentNumber', 'versionKey', 'validityStatus']
      .every(key => text(version[key])) && dateText(version.effectiveDate) &&
      (version.endDate === '' || dateText(version.endDate)) && sourceUrl(version.officialSourceUrl), 'STANDARD_VERSION');
    const scope = standard.officialScope;
    check(object(scope) && text(scope.label) && Array.isArray(scope.sourceUrls) &&
      scope.sourceUrls.length > 0 && scope.sourceUrls.every(sourceUrl) &&
      typeof scope.wholeStandardComplete === 'boolean', 'OFFICIAL_SCOPE');
    if (Object.hasOwn(standard, 'publicationBasis')) {
      const p = standard.publicationBasis;
      check(object(p) && Object.keys(p).sort().join(',') === 'basis,checked,fullTextPublicationApproved,legalSourceUrl' &&
        p.basis === 'copyright_law_article_5_official_administrative_document' &&
        p.fullTextPublicationApproved === true && sourceUrl(p.legalSourceUrl) &&
        new URL(p.legalSourceUrl).hostname.endsWith('.gov.cn') &&
        typeof p.checked === 'string' && dateText(p.checked.slice(0, 10)) && p.checked.slice(0, 10) <= catalog.asOf &&
        (p.checked.length === 10 || (/[zZ]|[+-]\d{2}:\d{2}$/.test(p.checked) && Number.isFinite(Date.parse(p.checked)))),
      'PUBLICATION_BASIS');
    }
    check(!scope.wholeStandardComplete || standard.publicationBasis?.fullTextPublicationApproved === true,
      'COMPLETE_BODY_REVIEW');
    check(Array.isArray(standard.clauses), 'CLAUSES');
    let tableCount = 0;
    for (const clause of standard.clauses) {
      check(object(clause) && text(clause.clauseId) && !clauseVersions.has(clause.clauseId), 'CLAUSE_ID');
      clauseVersions.set(clause.clauseId, clause.lawVersionId);
      check(clause.lawVersionId === standard.lawVersionId, 'CLAUSE_VERSION');
      check(clause.granularity === 'whole_clause', 'CLAUSE_GRANULARITY');
      check(text(clause.article) && text(clause.quote) && text(clause.status) &&
        typeof clause.checked === 'string' && (clause.checked === '' ||
          (dateText(clause.checked.slice(0, 10)) && (clause.checked.length === 10 || Number.isFinite(Date.parse(clause.checked))))) &&
        sourceUrl(clause.sourceUrl), 'CLAUSE_CONTENT');
      ids(clause.directHazardIds, 'CLAUSE_HAZARD_IDS');
      for (const id of validateNormativeClause(clause)) {
        check(!tableIds.has(id), 'TABLE_ID_DUPLICATE'); tableIds.add(id); tableCount++;
      }
      if (Object.hasOwn(clause, 'applicationNotes')) {
        check(Array.isArray(clause.applicationNotes) && clause.applicationNotes.length > 0 &&
          standard.publicationBasis?.fullTextPublicationApproved === true, 'APPLICATION_NOTES');
        const sources = new Set();
        for (const note of clause.applicationNotes) {
          check(object(note) && Object.keys(note).sort().join(',') === 'checked,isOfficialNormText,kind,sourceDate,sourceUrl,summary' &&
            note.kind === 'official_application_clarification' && note.isOfficialNormText === false &&
            text(note.summary) && note.summary.length <= 1000 && sourceUrl(note.sourceUrl) &&
            !/\s/u.test(note.sourceUrl) && new URL(note.sourceUrl).hostname.endsWith('.gov.cn') &&
            dateText(note.sourceDate) && note.sourceDate <= catalog.asOf &&
            note.checked === standard.publicationBasis.checked && note.sourceDate <= note.checked.slice(0, 10) &&
            !sources.has(note.sourceUrl), 'APPLICATION_NOTE_CONTENT');
          sources.add(note.sourceUrl);
        }
      }
    }
    const coverage = standard.coverage;
    check(object(coverage) && ['reviewed_scope_complete', 'partial'].includes(coverage.status) &&
      ['reviewedClauseCount', 'reviewedWholeClauseCount', 'reviewedSubitemClauseCount', 'expectedWholeClauseCount']
        .every(key => count(coverage[key])) && nullableCount(coverage.expectedJudgmentItemCount) &&
      nullableCount(coverage.reviewedJudgmentItemCount) && typeof coverage.wholeStandardComplete === 'boolean',
    'STANDARD_COVERAGE');
    check(coverage.wholeStandardComplete === scope.wholeStandardComplete &&
      (!coverage.wholeStandardComplete || coverage.status === 'reviewed_scope_complete'), 'COMPLETE_BODY_COVERAGE');
    if (tableCount || Object.hasOwn(coverage, 'expectedTableCount') || Object.hasOwn(coverage, 'reviewedTableCount')) {
      check(standard.publicationBasis?.fullTextPublicationApproved === true && count(coverage.expectedTableCount) &&
        coverage.expectedTableCount > 0 && count(coverage.reviewedTableCount) &&
        coverage.reviewedTableCount === tableCount && coverage.expectedTableCount >= tableCount &&
        (coverage.status !== 'reviewed_scope_complete' || coverage.expectedTableCount === tableCount), 'TABLE_COVERAGE');
    }
    check(coverage.reviewedClauseCount === standard.clauses.length &&
      coverage.reviewedWholeClauseCount === standard.clauses.length &&
      coverage.reviewedSubitemClauseCount === 0 &&
      coverage.expectedWholeClauseCount >= coverage.reviewedWholeClauseCount,
    'COVERAGE_COUNTS');
    check(coverage.status !== 'reviewed_scope_complete' ||
      coverage.expectedWholeClauseCount === coverage.reviewedWholeClauseCount, 'COVERAGE_COMPLETENESS');
    if (coverage.expectedJudgmentItemCount !== null && coverage.reviewedJudgmentItemCount !== null) {
      check(coverage.reviewedJudgmentItemCount <= coverage.expectedJudgmentItemCount, 'JUDGMENT_COUNTS');
    }
    check(coverage.status !== 'reviewed_scope_complete' || coverage.expectedJudgmentItemCount === null ||
      coverage.reviewedJudgmentItemCount === coverage.expectedJudgmentItemCount, 'JUDGMENT_COMPLETENESS');
    const directIds = ids(standard.directHazardIds, 'STANDARD_HAZARD_IDS');
    check(count(standard.directHazardCount) && standard.directHazardCount === directIds.size,
      'STANDARD_HAZARD_COUNT');
  }

  const linkedHazards = new Set(), linkIds = new Set();
  for (const association of topic.associations) {
    check(object(association) && ['hazardId', 'linkId', 'clauseId', 'lawVersionId', 'applicability']
      .every(key => text(association[key])) &&
      (association.jurisdictionCode === null || text(association.jurisdictionCode)), 'ASSOCIATION_CONTENT');
    check(association.role === 'direct', 'ASSOCIATION_ROLE');
    check(!linkIds.has(association.linkId), 'ASSOCIATION_DUPLICATE');
    linkIds.add(association.linkId);
    check(byVersion.has(association.lawVersionId), 'ASSOCIATION_VERSION');
    check(byHazard.has(association.hazardId), 'ASSOCIATION_HAZARD_MISSING');
    // An approved direct association can refer to an exact excerpt that is not
    // a canonical whole clause in this catalog. A known C must still match LV.
    check(!clauseVersions.has(association.clauseId) ||
      clauseVersions.get(association.clauseId) === association.lawVersionId, 'ASSOCIATION_CLAUSE_VERSION');
    linkedHazards.add(association.hazardId);
  }
  check(sameIds(topicIds, linkedHazards), 'TOPIC_HAZARD_MEMBERSHIP');
  for (const standard of catalog.standards) {
    const associations = topic.associations.filter(row => row.lawVersionId === standard.lawVersionId);
    check(sameIds(new Set(standard.directHazardIds), new Set(associations.map(row => row.hazardId))),
      'STANDARD_HAZARD_MEMBERSHIP');
    for (const clause of standard.clauses) {
      check(sameIds(new Set(clause.directHazardIds), new Set(associations
        .filter(row => row.clauseId === clause.clauseId).map(row => row.hazardId))), 'CLAUSE_HAZARD_MEMBERSHIP');
    }
  }
  for (const id of topicIds) {
    const row = byHazard.get(id);
    check(object(row) && text(row.title) && typeof row.searchText === 'string' &&
      text(row.displayCategory ?? row.category) && row.status === '已核验' && row.publishable !== false, 'TOPIC_HAZARD_CONTENT');
  }
  return {catalog, topic, standards: catalog.standards, hazards: topic.hazardIds.map(id => byHazard.get(id))};
}

/** Metadata and normative views may describe the same exact version after a
 * separately approved text publication. They keep separate counts and roles.
 */
export function validateDirectoryCatalogLinks(model, directory) {
  const versions = new Map(model.standards.map(row => [row.lawVersionId, row]));
  for (const entry of directory.entries) {
    const standard = versions.get(entry.lawVersionId);
    if (!standard) continue;
    const v = standard.standardVersion;
    check(standard.publicationBasis?.fullTextPublicationApproved === true &&
      entry.lawId === v.lawId && [v.name, `${v.name} ${v.documentNumber}`].includes(entry.title) &&
      entry.documentNumber === v.documentNumber &&
      entry.versionKey === v.versionKey && entry.effectiveDate === v.effectiveDate,
    'DIRECTORY_CATALOG_IDENTITY');
  }
}

function cleanRoute(route = {}) {
  const value = object(route) ? route : {};
  const clean = key => typeof value[key] === 'string' ? value[key].trim() : '';
  return {view: ['hazards', 'references'].includes(value.view) ? value.view : 'clauses',
    standard: clean('standard'), category: clean('category'), query: clean('query').replace(/\s+/g, ' ')};
}

/** URL keys: view, standard, category, q. Unknown view falls back to clauses. */
export function parseMajorRoute(search = '') {
  const params = new URLSearchParams(search);
  return cleanRoute({view: params.get('view'), standard: params.get('standard'),
    category: params.get('category'), query: params.get('q')});
}

/** Return a canonical query without a leading ?, or '' for the default route. */
export function majorRouteQuery(route) {
  const value = cleanRoute(route), params = new URLSearchParams();
  if (value.view !== 'clauses') params.set('view', value.view);
  if (value.standard) params.set('standard', value.standard);
  if (value.category) params.set('category', value.category);
  if (value.query) params.set('q', value.query);
  return params.toString();
}

/** Query terms only narrow the controlled catalog/topic; they never infer H membership. */
export function selectMajorResults(model, route = {}) {
  const value = cleanRoute(route);
  const scopedStandards = model.standards.filter(row => (!value.standard || row.lawVersionId === value.standard) &&
    administrativeNumberMatches(row.standardVersion.documentNumber, value.query));
  const versions = new Set(scopedStandards.map(row => row.lawVersionId));
  const associations = model.topic.associations.filter(row => versions.has(row.lawVersionId));
  const scopedIds = new Set(associations.map(row => row.hazardId));
  // Use the shared standard-number parser to preserve exact family/year rules
  // (GB45067 also finds GB 45067, but not GB450670 or a different edition).
  // These temporary search rows come only from the already validated catalog.
  const clauseRows = scopedStandards.flatMap(standard => standard.clauses.map(clause => ({
    id: clause.clauseId, name: `${standard.standardVersion.name} ${clause.article}`,
    documentNumber: standard.standardVersion.documentNumber, aliases: [], status: clause.status,
    searchText: normalized([standard.standardVersion.name, standard.standardVersion.documentNumber,
      standard.standardVersion.versionKey, clause.article, clause.quote,
      ...(clause.applicationNotes || []).map(note => note.summary)].join(' ')),
  })));
  const clauseMatch=searchLawsDetailed(clauseRows, value.query);
  const matchingClauseIds = new Set(clauseMatch.rows.map(row => row.id));
  const standards = scopedStandards.map(standard => ({...standard,
    clauses: standard.clauses.filter(clause => matchingClauseIds.has(clause.clauseId)),
  })).filter(standard => standard.clauses.length > 0);
  const hazardRows=model.hazards.filter(row=>scopedIds.has(row.id)).map(row=>{
    const links=associations.filter(item=>item.hazardId===row.id);
    const linkedVersions=new Set(links.map(item=>item.lawVersionId));
    const linkedStandards=scopedStandards.filter(standard=>linkedVersions.has(standard.lawVersionId));
    // Only identities in the selected, verified topic chain are searchable as
    // standard numbers here; another basis or historical mention cannot qualify.
    const stdNumbers=linkedStandards.map(standard=>standard.standardVersion.documentNumber);
    const lawNames=linkedStandards.map(standard=>standard.standardVersion.name);
    return {...row,aliases:row.aliases||[],keywords:row.keywords||[],places:row.places||[],levels:row.levels||[],scopes:row.scopes||[],stdNumbers,lawNames,
      searchText:normalized([row.title,row.searchText,...lawNames,...stdNumbers,...links.map(item=>item.applicability)].join(' '))};
  });
  const hazardMatch=searchHazardsDetailed(hazardRows,value.query,{category:value.category});
  const matchingHazardIds=new Set(hazardMatch.rows.map(row=>row.id));
  const hazards=model.hazards.filter(row=>matchingHazardIds.has(row.id));
  const match=value.view==='hazards'?hazardMatch:clauseMatch;
  return {standards,hazards,matchKind:match.matchKind,interpretedQuery:match.interpretedQuery,queryNotice:match.queryNotice};
}

/** Clock-independent notice: the caller supplies today's YYYY-MM-DD when needed. */
export function snapshotNoticeText(date, today = date) {
  if (!dateText(date)) return '数据快照日期缺失或无效，请核对发布版本后使用。';
  if (!dateText(today)) return '当前日期无法确认，请核对设备日期和数据快照。';
  if (date === today) return '';
  if (today < date) return `数据快照日期 ${date} 晚于当前日期 ${today}，请核对设备日期和发布版本。`;
  return `数据快照截至 ${date}，早于当前日期 ${today}；请核对后续版本和效力变化。`;
}
