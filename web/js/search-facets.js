// Navigation facets use the published item itself. They do not infer legal
// applicability from incidental words in law text, descriptions or searchText.
const normal = value => String(value ?? '').normalize('NFKC');
const sourceNames = row => normal([row.title, ...(row.aliases || [])].join(' '));
const industryDefs = [
  ['工贸企业', /工贸/],
  ['建筑施工', /建筑施工|施工现场|建设工程|市政施工/],
  ['危化品生产经营', /危险化学品|危化|化工企业|化工装置|加油站/],
  ['仓储物流', /仓储|物流|仓库|库房/],
  ['餐饮商业', /餐饮|饭店|厨房|商场|商业综合体|宾馆|酒店/],
  ['人员密集场所', /人员密集|公共聚集|公共娱乐场所/],
];
const equipmentDefs = [
  ['灭火器', /灭火器/], ['消火栓', /消火栓|消防栓/],
  ['疏散与通道设施', /疏散|安全出口|消防车道|防火门|应急照明|应急灯/],
  ['配电与电气设备', /配电|开关箱|电箱|电气|电线|电缆|漏电保护|接地|插座|插排/],
  ['起重机械', /起重|吊钩|吊索|电动葫芦|天车|桥式|门式|龙门吊|(?<!自)行车(?!道|路线|速度|制动)/],
  ['叉车', /叉车/], ['电动自行车', /电动自行车|电瓶车/],
  ['气瓶', /气瓶|钢瓶|氧气瓶|乙炔瓶/], ['压力设备', /压力容器|锅炉|压力表|安全阀|压力管道/],
  ['报警与探测装置', /报警|探测器|检测仪/],
  ['通信装置', /通信装置|通讯装置|通信设备|通讯设备/],
  ['机械与防护装置', /机械|机床|砂轮|冲压|防护罩|防护装置|传动|输送机/],
  ['危化品与危险废物', /危险化学品|危化|化学品|危险废物|危废/],
  ['劳动防护用品', /安全帽|安全带|防护用品|防护服|防护眼镜|防毒面具/],
];
const problemDefs = [
  ['缺少或未安装', /未(?:安装|设置|配置|配备|设立)|没有(?:安装|设置|配置|配备)|(?:缺少|缺失)(?:灭火器|消火栓|防护|安全|接地|跨接|报警|照明|标志|护栏|盖板|装置)|(?:灭火器|消火栓|防护罩|安全阀|接地线|跨接线|报警器|标志|护栏|盖板|装置)(?:缺失|缺少)/],
  ['损坏或失效', /损坏|破损|故障|失效|失灵|失压|压力不足|无法(?:使用|启动)|不能(?:使用|启动)/],
  ['检验检定超期', /超期|过期|未(?:定期)?(?:检验|检定|校验)|超过.{0,6}(?:检验|检定|校验)|检定有效期/],
  ['资料记录缺失', /未(?:记录|留存|保存|建档)|未提供.{0,8}(?:资料|报告|记录|台账|档案)|(?:资料|报告|记录|台账|档案).{0,8}(?:缺失|缺少|不全|未提供|不完整)|(?:缺少|无).{0,4}(?:资料|报告|记录|台账|档案)/],
  ['实际活动未实施', /未(?:开展|组织|实施|进行|落实|培训|演练)|没有(?:开展|组织|实施)/],
  ['堵塞占用', /堵塞|阻塞|堵住|占用|堆放|堆物|遮挡|封闭|锁闭/],
  ['接地与电气防护', /接地|跨接|漏电|绝缘|裸露|触电/],
  ['作业与管理要求', /作业许可|违章|操作规程|管理制度|安全距离|混放|混存|违规/],
];
export function hazardFacetValues(row = {}) {
  const names = sourceNames(row);
  const places = normal((row.places || []).join(' '));
  const industry = industryDefs.filter(([, test]) => test.test(places)).map(([label]) => label);
  const equipment = equipmentDefs.filter(([, test]) => test.test(names)).map(([label]) => label);
  const problem = problemDefs.filter(([, test]) => test.test(names)).map(([label]) => label);
  return {
    industry: industry.length ? industry : ['未标注行业或场所'],
    equipment: equipment.length ? equipment : ['其他或未明确设备'],
    problem: problem.length ? problem : ['其他问题'],
  };
}
export function filterHazardFacets(rows, filters = {}) {
  const keys = ['industry', 'equipment', 'problem'].filter(key => filters[key]);
  if (!keys.length) return rows;
  return rows.filter(row => {
    const values = hazardFacetValues(row);
    return keys.every(key => values[key].includes(filters[key]));
  });
}
export function hazardFacetOptions(rows = []) {
  const available = {industry: new Set(), equipment: new Set(), problem: new Set()};
  for (const row of rows) {
    const values = hazardFacetValues(row);
    for (const key of Object.keys(available)) for (const value of values[key]) available[key].add(value);
  }
  const definitions = {industry: industryDefs, equipment: equipmentDefs, problem: problemDefs};
  const other = {industry: '未标注行业或场所', equipment: '其他或未明确设备', problem: '其他问题'};
  return Object.fromEntries(Object.entries(available).map(([key, values]) => [key,
    [...definitions[key].map(([label]) => label), other[key]].filter(label => values.has(label))]));
}
