// Retrieval boundaries only: these checks do not decide that a site has a hazard.
// Keep object identity, observed defect and documentary evidence separate. The
// same metadata is available to the local workbench and offline evaluation.
import {analyzeFieldObservation} from './query-intent.js';
const choice = (label, query, note) => ({label, query, note});
const stop = (reason, notice, requiredFacts, suggestions = [], classification = 'needs_conditions') => ({
  suppressResults: true, notice, suggestions,
  assessment: {classification, reason, requiredFacts},
});
const compact = value => String(value ?? '').normalize('NFKC').replace(/[\s，。？！?!]/g, '');

export function observationStateBoundary(value) {
  const q = compact(value);
  const observation = analyzeFieldObservation(value);
  // Polarity belongs to a specific state. “检定超期，但没有损坏” still
  // supports looking up verification candidates, without claiming breakage.
  if (observation.activeClaims.length) return null;
  // These qualifiers are meaningful even in the middle of a long sentence.
  // Do not let the colloquial fallback discard them and manufacture a defect.
  if (observation.hasUncertainty) {
    return stop('unconfirmed_observation', '原话含有待核实、疑问或不确定状态。请先核实对象和实际情况；不能删掉这些状态词，直接认定已经存在缺陷。',
      ['对象与适用场景', '现场当前状态及观察或检测证据'], [], 'fact_unconfirmed');
  }
  if (observation.claims.some(claim=>claim.polarity==='negated')
      // A terminal “断” is a state. “断路器” and “断电” are different
      // predicates/objects and must not be swallowed by a one-character guard.
      || /(?:没有|没|未|不)(?:明显|再)?断(?:了)?(?:$|[,，;；。])/.test(String(value??'').normalize('NFKC').trim())
      || /(?:未发现|没有发现|未见)(?!.*(?:报告|记录|台账|签到表)).*(?:损坏|故障|失效|缺陷|堵|堆|失压|接地|异常|隐患)/.test(q)
      || /(?:没有|没|未|不|不存在)(?:明显|再)?(?:坏(?:掉)?|损坏|故障|失灵|失效|破损|断裂|断开|堵(?:塞|住)?|被堵|遮挡|被挡|堆(?:放|积|东西|杂物|纸箱)|放(?:置|着|有)?(?:杂物|纸箱|东西|货物|物料)|漏气|泄漏|超期|过期|失压|异常|隐患(?!排查|记录|治理|整改))/.test(q)
      || /(?:没有|没|未)(?:超过|超出).*(?:有效期|周期)/.test(q)
      || /(?:不是|并非|不属于).*(?:没|未|没有|损坏|故障|失效|失压|超期|过期|堵塞|遮挡)/.test(q)) {
    return stop('negated_observation', '原话表示未发生或未发现所说的缺陷。已保留否定和状态词，不把正常、未发现或双重否定的描述改成隐患；需要时请按实际待查问题重新检索。',
      ['现场当前状态及证据'], [], 'fact_unconfirmed');
  }
  if (observation.unresolvedReference) return stop('observed_object_unidentified',
    '原话中的已知设备是位置参照，不能把旁边、上方或下方另一设备的故障归给它。请明确实际故障设备的名称、类型和状态，再核对适用依据。',
    ['实际故障设备的名称和类型','位置参照与故障对象的关系','实际故障及当前状态证据']);
  if (observation.hasHistorical) return stop('historical_observation',
    '原话中的历史、已排除或已恢复状态词已保留，不能将过去的问题当成当前隐患。请依据复查记录核实当前设备状态。',
    ['当前设备状态','复查或检测证据'], [], 'fact_unconfirmed');
  const currentFailure=/(?:但|仍|还是|又|再次).*(?:没|未|不亮|不动作|损坏|故障|失压|失效|堵塞|破损|漏气|泄漏)/.test(q);
  if (!currentFailure && (observation.claims.some(claim=>claim.polarity==='normal'&&claim.subjects.length)
      || /(?<!未)(?:已经|已)(?:修好|修复|整改完成|更换|换好|维修完成|处理完|清理完|清走|清掉|疏通|排除|恢复正常|接好|完成)(?:了)?/.test(q)
      || /(?:现在|目前)(?:已经|已)?(?:正常|完好|畅通)/.test(q)
      || /(?:已经|(?<!未)已)(?:安装|配置|配备|接地|固定|佩戴|检测|检验|检定|校验|培训|演练|审批|签字)(?:完成|合格|有效|了)?$/.test(q)
      || /(?:正常|完好无损|压力充足|仍在有效期|还没到期|尚未到期)$/.test(q))) {
    return stop('completed_observation', '原话表示已修复、已完成或目前正常。检索保留完成状态词，不将历史问题改成当前隐患；复查时请记录当前事实及证据。',
      ['修复后的当前状态', '复查或检测证据'], [], 'fact_unconfirmed');
  }
  return null;
}

export function fieldSafetyBoundary(value) {
  const q = compact(value);
  const state = observationStateBoundary(value);
  if (state) return state;
  if (/^(?:(?:现场|车间|仓库)(?:内|里|的)?)?灭火器(?:前面|前|周围|旁边)(?:堆放|堆有|放有|摆放|堆着)(?:了)?(?:纸箱|杂物|货物)$/.test(q)) {
    return stop('extinguisher_access_observation', '灭火器附近堆放物品还需核实是否遮挡识别或实际妨碍取用。请记录位置、距离和取用状态，再选择对应条款；不能仅凭“有纸箱”认定取用受阻。',
      ['灭火器设置点及适用场景', '物品是否遮挡识别或妨碍便捷取用', '现场照片及实际取用核实'], [
        choice('核查灭火器遮挡与取用', '灭火器被遮挡、取用受阻', '仅在确认实际遮挡或取用受阻时选用；不改变原始观察。'),
      ]);
  }
  if (/(?:气瓶|钢瓶).*(?:防震圈|防震胶圈)/.test(q)
      && /(?:没|未|缺|无|丢失|遗失|脱落|损坏)/.test(q)) {
    return stop('cylinder_ring_source_gap', '缺防震圈与缺瓶帽、保护罩不是同一缺陷。本站尚无可据此认定所有在用气瓶不符合要求的通用规则，应核实际瓶型、行业和装卸运输要求。',
      ['气瓶种类', '行业和使用、装卸或运输场景', '对应现行条款及原始证据'], [], 'evidence_gap');
  }
  if (/^普通化学品.*(?:混放|混存|未分类|没有分类|没分类|随便放|乱放)/.test(q)) {
    return stop('ordinary_chemical_identity', '普通化学品不能仅因混放就套用危险化学品储存规则。请核对物料身份、危险特性和实际储存场景；暂无足以直接判断本问题的事实与对题依据。',
      ['物料名称及危险性分类', '物料相容性', '实际储存场景']);
  }
  const missingLight = /^(?:现场|车间|仓库|厂房|楼梯间)(?:里|内|的)?(?:应急灯|应急照明灯|消防应急灯)(?:(?:没有|没|未)(?:设置|安装|装设|配置|装)|缺少|缺失)(?:过|了)?$/;
  if (missingLight.test(q)) {
    return stop('emergency_lighting_absent', '未设置与已经设置但灯具损坏是不同缺陷。还需核实建筑、部位及消防设计要求，不能由“车间”或“仓库”自动补齐应设条件。',
      ['建筑用途及类别', '所在部位', '是否属于条款规定应设疏散照明的情形'], [
        choice('查疏散照明未设置', '应设疏散照明的建筑部位未设置疏散照明', '确认应设条件后再选用；应急照明与疏散指示标志分别核查。'),
      ]);
  }
  if (/^(?:现场|车间|仓库|楼梯间)(?:里|内|的)?消防门(?:坏了|损坏|关不严|关不上|锁住了)?$/.test(q)) {
    return stop('fire_door_object', '“消防门”需先确认为防火门或承担疏散功能的出口门；不能解释成消火栓箱门。核实门的类型、位置和具体功能后选择。',
      ['门的类型', '所在建筑和部位', '关闭或疏散功能的实际状态'], [
        choice('核实防火门', '防火门', '核实建筑和部位及关闭功能，不能仅按口头名称判断。'),
        choice('核实安全出口', '安全出口', '仅在承担疏散功能时继续核查通行条件。'),
      ]);
  }
  if (/^(?:资料核查[：:]?)?(?:建筑)?消防设施(?:年度)?(?:全面)?检测报告(?:缺失|未提供|没有提供|找不到)$/.test(q)
      || /^(?:资料核查[：:]?)?年度消防检测报告(?:缺失|未提供|找不到)$/.test(q)) {
    return stop('fire_document_review', '检测报告未提供是资料待核事实，不能据此认定设施已损坏或年度检测从未实施。应核实检测义务、实际实施和记录保存情况。',
      ['是否负有对应年度检测义务', '实际检测实施情况', '报告与记录的保存或提供情况'], [
        choice('核查年度检测与记录义务', '建筑消防设施年度全面检测、有效状态或记录不符合要求', '该条目包含不同义务，审核时必须指明已证实的具体缺陷，不能把报告缺失转为设施故障。'),
      ]);
  }
  if (/(?:培训签到表|培训记录).*(?:缺签字|未签字|没有签字|缺失|未提供)/.test(q)
      || /^(?:没有|没|未)(?:找到|查到|提供)培训(?:记录|签到表|档案)/.test(q)) {
    return stop('training_document_review', '培训记录或签到签字问题与未开展培训、考核不合格是不同事实。请核实实际培训及依法应记录的内容，不能由缺签字推定未培训。',
      ['实际培训情况', '应记录的培训时间、内容、参加人员和考核结果', '资料缺项及其证据'], [
        choice('核查培训档案与记录', '未建立安全生产教育培训档案并如实记录', '只核查档案及真实记录义务；缺少某个签字不自动等于未建立档案或未培训。'),
      ]);
  }
  if (/^(?:资料核查[：:]?)?(?:(?:没有|没|未)(?:找到|查到|提供).*(?:检验|检测)(?:报告|记录)|.*(?:检验|检测)报告(?:缺失|未提供|找不到))$/.test(q)) {
    return stop('equipment_document_review', '暂未找到检验或检测报告只能记为资料待核，不能推定设备故障、检验超期或未经检验仍在使用。请分别核实设备类别、有效期、实际检验及继续使用情况。',
      ['设备类别', '实际检验及有效期', '报告保存或提供情况', '是否仍继续使用']);
  }
  if (/(?:报告|记录|台账|签到表|档案|证书|合格证).*(?:暂时|暂)?(?:没给|没拿出来|没有拿出来|未拿出|没提供|没有提供|未提供|没有出示|未出示|找不到|没找到|未找到|缺失)/.test(q)
      || /(?:(?:没有|没|未|暂未)(?:找到|查到|提供|出示)|未见).*(?:报告|记录|台账|签到表|档案|证书|合格证)$/.test(q)) {
    return stop('document_availability_unconfirmed', '资料或证书未提供、未出示或暂未找到，只能说明资料仍待核实，不能据此推定培训、检验、检测或检查从未实施、资格无效，也不能推定设备损坏。请分别核实实施事实、有效期和记录义务。',
      ['具体资料和法定记录义务', '活动是否实际实施及其证据', '记录是否保存、是否能够提供']);
  }
  return null;
}

// Explicit pressure-gauge states must occur in the rule heading, not solely in
// applicability/exclusion prose. Full title lookup is handled before this guard.
// Never make verification and periodic equipment inspection synonyms.
export function pressureGaugeStateBoundary(query) {
  const q = compact(query);
  if (!q.includes('压力表') || q.includes('灭火器')) return null;
  const observation = analyzeFieldObservation(query);
  const overdue = observation.defects.includes('verification_overdue');
  const damaged = observation.defects.includes('damaged');
  if (overdue && !damaged) return {
    reason: 'gauge_verification_state',
    heading: /(?:检定|检定有效期)/,
    notice: '检定有效期与压力表部件损坏分别核查；检索候选仍须确认设备适用范围及真实有效期。',
    requiredFacts: ['是否属于固定式压力容器及条款适用范围', '检定有效期及证据'],
  };
  if (damaged && !overdue) return {
    reason: 'gauge_damage_state',
    heading: /(?:损坏|故障|玻璃破裂|刻度不清|指针松动|弹簧管泄漏)/,
    notice: '压力表损坏与检定超期分别核查；检索候选仍须确认所属设备及条款列明的实际损坏。',
    requiredFacts: ['所属设备及条款适用范围', '实际损坏及证据'],
  };
  return null;
}
