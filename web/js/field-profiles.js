// Only verified public projections enter this model. No observations or approvals
// are produced here; routing describes how to check, never a site finding.
export const INSPECTION_LABELS = Object.freeze({
  core_onsite_inspection:'现场检查', document_review:'资料核查',
  special_review:'专项评价', legal_obligation:'法规义务',
});
const nonempty = value => typeof value === 'string' && !!value.trim();
const strings = (value, required=false) => Array.isArray(value) && (!required || value.length > 0) && value.every(nonempty) && new Set(value).size === value.length;
const date = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value;
const shape = (value,required,optional=[]) => value && typeof value === 'object' && !Array.isArray(value) &&
  required.every(key=>Object.hasOwn(value,key)) && Object.keys(value).every(key=>required.includes(key)||optional.includes(key));
const ident = value => nonempty(value) && value===value.trim() && !/[\\/]|\.\.|[\x00-\x1f]/.test(value);
const PROFILE_FIELDS=['schemaVersion','id','revision','hazardId','title','inspectionClass','defaultFieldEntry','contentDisposition','applicability','findingTemplate','evidenceRequirements','correctiveDirection','basisLinkIds','recordKind','observedViolation','sourceHazard','bases'];
const BASIS_FIELDS=['linkId','clauseId','role','applicability','jurisdictionCode','lawVersionId','lawId','lawJurisdictionCode'];
const openEnd = value => value === undefined || value === null || value === '';
const checkedBy = (value, asOf) => value === undefined || (typeof value === 'string' &&
  date(value.slice(0,10)) && value.slice(0,10)<=asOf &&
  (value.length===10 || /^\d{4}-\d{2}-\d{2}[T ](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?$/.test(value) && !Number.isNaN(Date.parse(value))));
export function profileEnvelope(payload, releaseManifest, dataManifest) {
  if (!shape(payload,['schemaVersion','asOf','records']) || !releaseManifest?.fileHashes?.[dataManifest?.files?.fieldProfiles] ||
      !date(releaseManifest.asOf) || payload?.asOf !== releaseManifest.asOf ||
      payload?.schemaVersion !== 1 || !Array.isArray(payload.records) ||
      payload.records.length !== dataManifest?.counts?.fieldProfiles ||
      new Set(payload.records.map(row=>row?.id)).size !== payload.records.length) throw new Error('核查场景与当前已校验发布包不一致');
  return payload.records;
}
export function validateProfileJoin(profile, {hazard, bases}, asOf) {
  const p=profile, a=p?.applicability;
  if (!shape(p,PROFILE_FIELDS,['profileKind']) || !shape(a,['requires','excludes','perUseFacts']) || p.schemaVersion !== 1 || p.recordKind !== 'reusable_field_profile' || p.observedViolation !== false ||
      !nonempty(p.id) || !/^FPR_[A-Za-z0-9_-]+$/.test(p.id) || !ident(p.hazardId) || !nonempty(p.title) || !Number.isInteger(p.revision) || p.revision < 1 ||
      typeof p.inspectionClass!=='string' || !Object.hasOwn(INSPECTION_LABELS,p.inspectionClass) ||
      !['include','conditional','exclude'].includes(p.defaultFieldEntry) ||
      (Object.hasOwn(p,'profileKind') && !['routing_only','conditional_template'].includes(p.profileKind)) ||
      !strings(a?.requires,true) || !strings(a?.excludes) || !strings(a?.perUseFacts,true) ||
      !strings(p.evidenceRequirements,true) || !nonempty(p.correctiveDirection) ||
      !strings(p.basisLinkIds,true) || !p.basisLinkIds.every(ident) || !Array.isArray(p.bases) || p.bases.length !== p.basisLinkIds.length ||
      p.bases.some(b=>!shape(b,BASIS_FIELDS)||!['linkId','clauseId','lawVersionId','lawId'].every(key=>ident(b[key]))||!nonempty(b.applicability)||!nonempty(b.lawJurisdictionCode)||!(b.jurisdictionCode===null||typeof b.jurisdictionCode==='string')) ||
      new Set(p.bases.map(b=>b.linkId)).size !== p.bases.length || !date(asOf)) return false;
  const onsite=p.inspectionClass==='core_onsite_inspection';
  const dispositions={document_review:'document_check',special_review:'special_check',legal_obligation:'legal_obligation'};
  if (onsite ? p.contentDisposition!=='onsite_finding' || !['include','conditional'].includes(p.defaultFieldEntry) ||
      !['applicableRequirementConfirmed','siteTriggerConfirmed','defectObserved'].every(key=>a.perUseFacts.includes(key))
    : p.contentDisposition!==dispositions[p.inspectionClass] || p.defaultFieldEntry!=='exclude') return false;
  if (p.profileKind==='routing_only' || !onsite) {
    if (p.findingTemplate!==null) return false;
  } else {
    const t=p.findingTemplate;
    if (!shape(t,['text','slots']) || !nonempty(t?.text) || !Array.isArray(t.slots) || !t.slots.length ||
        t.slots.some(s=>!shape(s,['key','label'])||!/^[a-z][a-zA-Z0-9_]*$/.test(s.key)||!nonempty(s.label)) || new Set(t.slots.map(s=>s.key)).size!==t.slots.length) return false;
    const placeholders=[...t.text.matchAll(/\{\{([a-z][a-zA-Z0-9_]*)\}\}/g)].map(m=>m[1]);
    if (/\{\{|\}\}/.test(t.text.replace(/\{\{([a-z][a-zA-Z0-9_]*)\}\}/g,'')) || placeholders.length===0 || placeholders.some(key=>!t.slots.some(s=>s.key===key)) ||
        t.slots.some(s=>!placeholders.includes(s.key))) return false;
  }
  if (!shape(p.sourceHazard,['id','title','conditions']) || !Array.isArray(bases) || hazard?.id!==p.hazardId || hazard.status!=='已核验' || hazard.publishable===false ||
      p.sourceHazard?.id!==hazard.id || p.sourceHazard?.title!==hazard.title ||
      !(p.sourceHazard.conditions===null||typeof p.sourceHazard.conditions==='string') || (p.sourceHazard.conditions??'')!==(hazard.conditions??'') || !checkedBy(hazard.checked,asOf)) return false;
  return p.bases.every(b=>{
    const matches=bases.filter(x=>x.ref.linkId===b.linkId);
    if(matches.length!==1 || !p.basisLinkIds.includes(b.linkId)) return false;
    const {ref,clause,law,sourceUrl}=matches[0];
    return ['direct','fallback'].includes(b.role) && ref.role===b.role && ref.clauseId===b.clauseId && clause.id===b.clauseId &&
      ref.applicability===b.applicability && (ref.jurisdictionCode??null)===b.jurisdictionCode &&
      clause.lawId===b.lawVersionId && law.id===b.lawVersionId && law.status==='现行有效' && clause.status==='现行有效' &&
      date(law.effectiveDate) && law.effectiveDate<=asOf &&
      (openEnd(law.endDate) || date(law.endDate) && asOf<law.endDate && law.effectiveDate<law.endDate) &&
      checkedBy(law.checked,asOf) && checkedBy(clause.checked,asOf) && nonempty(clause.quote) &&
      /^https?:\/\//.test(sourceUrl||'');
  });
}
export function profileSummary(profiles=[]) {
  return [...new Set(profiles.map(p=>INSPECTION_LABELS[p.inspectionClass]).filter(Boolean))].join(' / ');
}
export function profileTemplateText(profile) {
  if(profile?.profileKind==='routing_only' || !profile?.findingTemplate) return '';
  return profile.findingTemplate.text.replace(/\{\{([^{}]+)\}\}/g,(_,key)=>`〔${profile.findingTemplate.slots.find(s=>s.key===key)?.label||key}〕`);
}
export function profileReferenceText(profile) {
  const route=INSPECTION_LABELS[profile.inspectionClass];
  return `核查场景参考（非现场结论）：${profile.title}\n核查用途：${route}${profile.defaultFieldEntry==='exclude'?'；不纳入默认现场检查，仍可查阅本项要求':''}\n选择场景不代表已核实适用条件或发现违规。\n\n需核实的适用条件：\n${profile.applicability.requires.join('\n')}\n\n不适用 / 避免误判：\n${profile.applicability.excludes.join('\n')}\n\n最小取证要求：\n${profile.evidenceRequirements.join('\n')}\n\n${profileTemplateText(profile)?`未填描述模板（仅供条件与事实核实后参考）：\n${profileTemplateText(profile)}`:'本项仅提供核查用途与范围，不提供现场隐患描述模板。'}\n\n整改方向参考：\n${profile.correctiveDirection}`;
}
