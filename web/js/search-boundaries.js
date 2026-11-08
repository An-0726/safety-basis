// Retrieval boundaries only: these checks do not decide that a site has a hazard.
// Keep object identity, observed defect and documentary evidence separate. The
// same metadata is available to the local workbench and offline evaluation.
const choice = (label, query, note) => ({label, query, note});
const stop = (reason, notice, requiredFacts, suggestions = [], classification = 'needs_conditions') => ({
  suppressResults: true, notice, suggestions,
  assessment: {classification, reason, requiredFacts},
});
const compact = value => String(value ?? '').normalize('NFKC').replace(/[\s，。？！?!]/g, '');

export function fieldSafetyBoundary(value) {
  const q = compact(value);
  if (/^(?:现场|本次检查)?(?:未见|未发现|尚未确认|尚未核实|未查明).*(?:损坏|故障|失效|缺陷|是否)/.test(q)) {
    return stop('unconfirmed_observation', '原话表示未发现或尚未核实。请保留这一状态，确认对象和实际事实后再匹配；不能把待核问题写成已确认隐患。',
      ['核实对象', '实际观察或检测事实'], [], 'fact_unconfirmed');
  }
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
  return null;
}

// Explicit pressure-gauge states must occur in the rule heading, not solely in
// applicability/exclusion prose. Full title lookup is handled before this guard.
// Never make verification and periodic equipment inspection synonyms.
export function pressureGaugeStateBoundary(query) {
  const q = compact(query);
  if (!q.includes('压力表')) return null;
  const overdue = /(?:检定(?:超期|过期)|超过检定有效期)/.test(q);
  const damaged = /(?:损坏|故障|玻璃(?:破裂|破损|碎了)|指针松动|弹簧管泄漏)/.test(q);
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
