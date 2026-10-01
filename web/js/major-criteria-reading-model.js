// Independently reviewed official source text for reading. This model never
// creates a current clause, a hazard association, or a field determination.
import {validateMajorDirectory} from './major-criteria-directory-model.js';

const ROOT = ['schemaVersion','asOf','catalogScope','referenceOnly','currentDeterminationBasis',
  'reviewedCurrentClauseCount','directHazardCount','standaloneDeterminationAllowed','allIndustryCoverage',
  'notice','readingGroupCount','sourceDocumentCount','firstLevelItemCount','readingGroups'];
const GROUP = ['id','directoryGroupId','primaryReferenceId','requiredReferenceIds','readingReason',
  'warning','checked','documents','publicationBasis'];
const DOCUMENT = ['directoryReferenceId','sourceIdentity','noticeText','sections','firstLevelItemCount',
  'fullTextReviewed','checked','currentUseEvidence','officialClarifications'];
const IDENTITY = ['lawId','lawVersionId','title','documentNumber','versionKey','issuer','documentKind',
  'legalNature','officialLink','officialTextLink','publicationDate','effectiveDate','effectiveDateNote',
  'scopeHint','scopeCaveat','directoryGroup','requiredCompanionIds','supplementsReferenceId'];
const ADMIN_KINDS = ['部门规章','部门规范性文件','部门规范性文件（补充判定情形）',
  '部门规范性文件（以通知印发的判定标准）','部门规范性文件（通知所附判定标准）'];
const check = (ok, code) => { if (!ok) throw new Error(`官方原文查阅数据校验失败：${code}`); };
function record(value, keys, code) {
  check(value !== null && typeof value === 'object' && !Array.isArray(value) &&
    [Object.prototype,null].includes(Object.getPrototypeOf(value)), `${code}_OBJECT`);
  const actual = Reflect.ownKeys(value);
  check(actual.length === keys.length && actual.every(key => keys.includes(key)) && keys.every(key => {
    const d = Object.getOwnPropertyDescriptor(value,key);
    return d && Object.hasOwn(d,'value') && d.enumerable;
  }), `${code}_FIELDS`);
}
function array(value, code, nonempty = false) {
  check(Array.isArray(value) && (!nonempty || value.length > 0), code);
  check(Reflect.ownKeys(value).length === value.length + 1 &&
    Array.from({length:value.length},(_,i)=>i).every(i => {
      const d=Object.getOwnPropertyDescriptor(value,String(i));
      return d && Object.hasOwn(d,'value') && d.enumerable;
    }), `${code}_FIELDS`);
}
const text = (value, maximum = 50000, empty = false) => typeof value === 'string' &&
  (empty || Boolean(value.trim())) && [...value].length <= maximum && !/[\u0000-\u0009\u000b-\u001f\u007f]/u.test(value);
const id = value => typeof value === 'string' && /^[A-Za-z0-9_]+$/u.test(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
function unique(seen, value, code) { check(!seen.has(value),code); seen.add(value); }
function ids(value, code, nonempty = false) {
  array(value,code,nonempty); check(value.every(id) && new Set(value).size === value.length,code);
}
function day(value) {
  if(typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(value) || value.startsWith('0000')) return false;
  const parsed=new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0,10) === value;
}
function checked(value) {
  if(day(value)) return true;
  return typeof value === 'string' && day(value.slice(0,10)) &&
    /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/u.test(value) && Number.isFinite(Date.parse(value));
}
function officialUrl(value) {
  if(!text(value) || /[\s\\\p{Cf}]/u.test(value) || /%(?:0[0-9a-f]|1[0-9a-f]|7f)/iu.test(value)) return false;
  const authority=value.match(/^https:\/\/([^/?#]+)(?:[/?#]|$)/iu)?.[1];
  if(!authority || !/^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+gov\.cn$/iu.test(authority)) return false;
  try {const url=new URL(value);return url.protocol==='https:' && !url.username && !url.password && !url.port && url.hostname.toLowerCase()===authority.toLowerCase();} catch{return false;}
}
const sameIds = (a,b) => a.length===b.length && a.every(value=>b.includes(value));
function sameData(a,b) {
  if(a===b) return true;
  if(Array.isArray(a)) return Array.isArray(b) && a.length===b.length && a.every((value,i)=>sameData(value,b[i]));
  if(a && b && typeof a==='object' && typeof b==='object') {
    const keys=Object.keys(a);return keys.length===Object.keys(b).length && keys.every(key=>Object.hasOwn(b,key) && sameData(a[key],b[key]));
  }
  return false;
}

export function validateMajorReading(data, expectedAsOf) {
  record(data,ROOT,'READING');
  check(data.schemaVersion==='safety-major-criteria-reading-v1','SCHEMA');
  check(day(data.asOf) && (expectedAsOf===undefined || (day(expectedAsOf) && data.asOf===expectedAsOf)),'SNAPSHOT');
  check(data.catalogScope==='official_source_reading_only' && data.referenceOnly===true &&
    data.currentDeterminationBasis===false && data.reviewedCurrentClauseCount===0 && data.directHazardCount===0 &&
    data.standaloneDeterminationAllowed===false && data.allIndustryCoverage===false && text(data.notice),'BOUNDARY');
  array(data.readingGroups,'GROUPS');
  const groupIds=new Set(), directoryIds=new Set(), documents=new Set(), versions=new Set(), laws=new Set(), itemIds=new Set(), noteIds=new Set();
  let documentCount=0,itemCount=0;
  for(const group of data.readingGroups) {
    record(group,GROUP,'GROUP');
    check([group.id,group.directoryGroupId,group.primaryReferenceId].every(id),'GROUP_ID');
    unique(groupIds,group.id,'DUPLICATE_GROUP');unique(directoryIds,group.directoryGroupId,'DUPLICATE_DIRECTORY_GROUP');
    ids(group.requiredReferenceIds,'REQUIRED_REFERENCES',true);
    check(group.requiredReferenceIds.includes(group.primaryReferenceId) && group.readingReason==='effective_date_not_fully_verified' &&
      text(group.warning,1000) && checked(group.checked) && group.checked.slice(0,10)<=data.asOf,'GROUP_BOUNDARY');
    record(group.publicationBasis,['basis','legalSourceUrl','checked','referenceTextPublicationApproved'],'PUBLICATION');
    const p=group.publicationBasis;
    check(p.basis==='copyright_law_article_5_official_administrative_document' && officialUrl(p.legalSourceUrl) &&
      p.checked===group.checked && p.referenceTextPublicationApproved===true,'PUBLICATION_BOUNDARY');
    array(group.documents,'DOCUMENTS',true);
    const members=[];
    for(const doc of group.documents) {
      record(doc,DOCUMENT,'DOCUMENT');
      check(id(doc.directoryReferenceId),'DOCUMENT_ID');unique(documents,doc.directoryReferenceId,'DUPLICATE_DOCUMENT');members.push(doc.directoryReferenceId);
      record(doc.sourceIdentity,IDENTITY,'IDENTITY');const identity=doc.sourceIdentity;
      check(id(identity.lawId) && id(identity.lawVersionId),'LAW_ID');unique(laws,identity.lawId,'DUPLICATE_LAW');unique(versions,identity.lawVersionId,'DUPLICATE_VERSION');
      check(ADMIN_KINDS.includes(identity.documentKind) && ['title','documentNumber','versionKey','issuer','legalNature','scopeHint','scopeCaveat'].every(key=>text(identity[key],2000)) &&
        text(identity.effectiveDateNote,1000,true) && officialUrl(identity.officialLink) && officialUrl(identity.officialTextLink),'IDENTITY_METADATA');
      check(day(identity.publicationDate) && identity.publicationDate<=data.asOf &&
        (identity.effectiveDate===null ? text(identity.effectiveDateNote,1000) : day(identity.effectiveDate) && identity.effectiveDate<=data.asOf),'SOURCE_DATE');
      record(identity.directoryGroup,['id','label','role'],'IDENTITY_GROUP');
      check(identity.directoryGroup.id===group.directoryGroupId && text(identity.directoryGroup.label,200) && ['primary','supplement'].includes(identity.directoryGroup.role),'IDENTITY_GROUP');
      ids(identity.requiredCompanionIds,'COMPANIONS');
      check(!identity.requiredCompanionIds.includes(doc.directoryReferenceId) && (identity.supplementsReferenceId===null || id(identity.supplementsReferenceId)),'COMPANION_ID');
      check(doc.fullTextReviewed===true && checked(doc.checked) && doc.checked.slice(0,10)<=group.checked.slice(0,10) && text(doc.noticeText),'DOCUMENT_REVIEW');
      array(doc.sections,'SECTIONS',true);const sections=new Set(),docItems=new Set();
      for(const section of doc.sections) {
        record(section,['id','title','items'],'SECTION');check(id(section.id) && text(section.title,1000),'SECTION_CONTENT');unique(sections,section.id,'DUPLICATE_SECTION');
        array(section.items,'ITEMS',true);
        for(const item of section.items) {
          record(item,['id','articleLabel','quote'],'ITEM');check(id(item.id) && text(item.articleLabel,100) && text(item.quote),'ITEM_CONTENT');
          unique(itemIds,item.id,'DUPLICATE_ITEM');docItems.add(item.id);
        }
      }
      check(count(doc.firstLevelItemCount) && doc.firstLevelItemCount===docItems.size,'ITEM_COUNT');
      array(doc.currentUseEvidence,'CURRENT_USE',true);
      for(const usage of doc.currentUseEvidence) {
        record(usage,['sourceDate','sourceUrl','summary'],'CURRENT_USE');
        check(day(usage.sourceDate) && usage.sourceDate<=group.checked.slice(0,10) && officialUrl(usage.sourceUrl) && text(usage.summary,1000),'CURRENT_USE_CONTENT');
      }
      array(doc.officialClarifications,'CLARIFICATIONS');
      for(const note of doc.officialClarifications) {
        record(note,['id','appliesToItemIds','textMode','text','sourceDate','sourceUrl','sourcePages','checked','isOfficialNormText'],'CLARIFICATION');
        check(id(note.id),'NOTE_ID');unique(noteIds,note.id,'DUPLICATE_NOTE');ids(note.appliesToItemIds,'NOTE_ITEMS',true);
        check(note.appliesToItemIds.every(value=>docItems.has(value)) && ['reviewed_summary','official_link_pending'].includes(note.textMode) &&
          text(note.text,2500) && day(note.sourceDate) && note.sourceDate<=group.checked.slice(0,10) && officialUrl(note.sourceUrl) &&
          note.checked===group.checked && note.isOfficialNormText===false,'NOTE_CONTENT');
        if(note.sourcePages!==null) {array(note.sourcePages,'NOTE_PAGES',true);check(note.sourcePages.every((page,i,a)=>Number.isSafeInteger(page) && page>=1 && page<=1000 && (i===0 || page>a[i-1])),'NOTE_PAGES');}
      }
      documentCount++;itemCount+=doc.firstLevelItemCount;
    }
    check(sameIds(members,group.requiredReferenceIds),'GROUP_DOCUMENTS');
    const primary=group.documents.filter(doc=>doc.sourceIdentity.directoryGroup.role==='primary');
    check(primary.length===1 && primary[0].directoryReferenceId===group.primaryReferenceId && primary[0].sourceIdentity.supplementsReferenceId===null &&
      sameIds(primary[0].sourceIdentity.requiredCompanionIds,members.filter(value=>value!==group.primaryReferenceId)) && group.documents.every(doc=>doc===primary[0] ||
        (doc.sourceIdentity.supplementsReferenceId===group.primaryReferenceId && doc.sourceIdentity.requiredCompanionIds.length===0)),'COMPANION_GRAPH');
    check(group.documents.every(doc=>doc.sourceIdentity.directoryGroup.label===primary[0].sourceIdentity.directoryGroup.label),'GROUP_LABEL');
    check(group.documents.some(doc=>doc.sourceIdentity.effectiveDate===null),'UNKNOWN_DATE_REASON');
  }
  check(count(data.readingGroupCount) && data.readingGroupCount===data.readingGroups.length && count(data.sourceDocumentCount) && data.sourceDocumentCount===documentCount &&
    count(data.firstLevelItemCount) && data.firstLevelItemCount===itemCount,'COUNTS');
  return data;
}

/** Reading is an exact, complete-group supplement to the admitted directory. */
export function validateReadingDirectoryLinks(reading,directory) {
  validateMajorReading(reading);validateMajorDirectory(directory,reading.asOf);
  const groups=new Map(directory.directoryGroups.map(group=>[group.id,group]));
  const entries=new Map(directory.entries.map(entry=>[entry.id,entry]));
  for(const readingGroup of reading.readingGroups) {
    const group=groups.get(readingGroup.directoryGroupId);
    check(group && group.primaryReferenceId===readingGroup.primaryReferenceId && sameIds(group.documentIds,readingGroup.requiredReferenceIds),'DIRECTORY_GROUP_MISMATCH');
    for(const doc of readingGroup.documents) {
      const entry=entries.get(doc.directoryReferenceId);
      check(entry && IDENTITY.every(key=>sameData(entry[key],doc.sourceIdentity[key])),'DIRECTORY_IDENTITY_MISMATCH');
    }
  }
  return reading;
}

// The directory's typography and exact document-identity semantics, kept here
// so its metadata-only search contract does not absorb the new source text.
const normalize=value=>value.normalize('NFKC').toLowerCase().replace(/[〔【﹝(]/gu,'[').replace(/[〕】﹞)]/gu,']').replace(/[‐‑‒–—−]/gu,'-');
const TECHNICAL=/(?<![a-z0-9/])([a-z]{2,8})(?:\s*\/\s*([a-z]))?\s*([1-9]\d*(?:\.\d+)*)(?:\s*-\s*(\d+)|\s+(\d{4})(?!\d))?(?![a-z0-9./-])/gu;
const ADMINISTRATIVE=/([\u3400-\u9fff]{1,40})\s*\[\s*(\d+)\s*\]\s*(\d+)\s*号(?:\s*\[[^\[\]]+\])?/gu;
const ORDER=/(?:([\u3400-\u9fff]{1,40}令)\s*)?第\s*(\d+)\s*号(?:\s*\[[^\[\]]+\])?/gu;
const compact=value=>normalize(value).replace(/\s+/gu,'');
function prepareQuery(value) {
  const technical=[],official=[];
  const remainder=normalize(value).replace(TECHNICAL,(_match,family,kind,number,year,spacedYear)=>{technical.push({family:`${family}${kind?`/${kind}`:''}`,number,year:year||spacedYear||''});return ' ';})
    .replace(ADMINISTRATIVE,match=>{official.push(compact(match));return ' ';}).replace(ORDER,match=>{official.push(compact(match));return ' ';});
  return {technical,official,terms:remainder.trim().split(/\s+/u).filter(Boolean)};
}
function literalMatch(fields,term) {
  if(!/\d/u.test(term)) return fields.some(field=>field.includes(term));
  const escaped=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const pattern=new RegExp(`(?<![a-z0-9.])${escaped}(?![a-z0-9.])`,'u');return fields.some(field=>pattern.test(field));
}
function matches(doc,query) {
  const identity=prepareQuery(doc.sourceIdentity.documentNumber);
  if(!query.technical.every(wanted=>identity.technical.some(available=>wanted.family===available.family && wanted.number===available.number && (!wanted.year || wanted.year===available.year)))) return false;
  if(!query.official.every(wanted=>literalMatch([compact(doc.sourceIdentity.documentNumber)],wanted))) return false;
  const fields=[doc.sourceIdentity.title,doc.sourceIdentity.documentNumber,doc.sourceIdentity.directoryGroup.label,doc.sourceIdentity.scopeHint,doc.noticeText,
    ...doc.sections.flatMap(section=>[section.title,...section.items.flatMap(item=>[item.articleLabel,item.quote])]),...doc.officialClarifications.map(note=>note.text)].map(normalize);
  return query.terms.every(term=>literalMatch(fields,term));
}

/** Literal AND within one document; every match returns the entire group. */
export function selectMajorReading(data,options={}) {
  validateMajorReading(data);
  const group=typeof options?.group==='string'?options.group.trim():'';
  const query=prepareQuery(typeof options?.query==='string'?options.query:'');
  const readingGroups=data.readingGroups.filter(row=>(!group || row.directoryGroupId===group) && row.documents.some(doc=>matches(doc,query)));
  return {readingGroups,readingGroupCount:readingGroups.length,sourceDocumentCount:readingGroups.reduce((n,row)=>n+row.documents.length,0),
    firstLevelItemCount:readingGroups.reduce((n,row)=>n+row.documents.reduce((sum,doc)=>sum+doc.firstLevelItemCount,0),0)};
}
