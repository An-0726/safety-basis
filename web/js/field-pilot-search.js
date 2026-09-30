import {searchHazards} from './search.js';

export const INSPECTION_LABELS = {
  core_onsite_inspection:'现场检查', document_review:'资料核查',
  special_review:'专项评价', legal_obligation:'法规义务', undetermined:'待定'
};

// A missing condition limits judgment, not the purpose of the concrete check.
export function searchPilot(records, query='', inspectionClass='core_onsite_inspection') {
  const scoped = records.filter(row => row.inspectionClass === inspectionClass &&
    (inspectionClass !== 'core_onsite_inspection' || ['include','conditional'].includes(row.defaultFieldEntry)));
  const results = searchHazards(scoped, query, {});
  // Generic equipment searches lead with concrete defects. Explicit boundary
  // queries keep the normal relevance order so their limitation remains findable.
  return /条件|未知|未确认|不能认定/.test(query) ? results : results.sort((a,b)=>
    Number(a.caseRole==='counterexample') - Number(b.caseRole==='counterexample'));
}
