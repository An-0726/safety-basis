// A small, inspectable parser for field observations. It only prepares retrieval;
// it never decides whether the observation proves a statutory non-compliance.
import {EQUIVALENT_GROUPS} from './search-vocabulary.js';

const textOf = value => String(value ?? '').normalize('NFKC').trim();
const compact = value => textOf(value).replace(/\s+/g, '');
const equivalentNames = word => EQUIVALENT_GROUPS.find(group => group.includes(word)) || [word];

// Objects, rather than arbitrary character fragments. Long names are scanned
// first, so 自行车 does not become 行车 and 灭火器压力表 is one object.
const OBJECT_NAMES = [
  ['灭火器压力表', ['灭火器压力表', '灭火器压力指示器']],
  ['灭火器', equivalentNames('灭火器')],
  ['消火栓箱', equivalentNames('消火栓箱')],
  ['消火栓', equivalentNames('消火栓')],
  ['消防车道', equivalentNames('消防车道')],
  ['疏散通道', equivalentNames('疏散通道')],
  ['通道', ['通道', '过道', '走道', '走廊']],
  ['疏散指示标志', [...equivalentNames('疏散指示标志'), ...equivalentNames('安全出口标志'), '疏散指示灯']],
  ['安全出口', equivalentNames('安全出口')],
  ['防火门', ['防火门']], ['消防门', ['消防门']],
  ['应急灯', [...equivalentNames('应急灯'), '消防应急照明灯具', '消防应急照明灯', '疏散照明']],
  ['感烟探测器', equivalentNames('感烟探测器')],
  ['火灾自动报警系统', equivalentNames('火灾自动报警系统')],
  ['消防控制室', equivalentNames('消防控制室')],
  ['可燃气体报警器', [...equivalentNames('可燃气体报警器'), '可燃气体报警装置', '可燃气体探测器']],
  ['报警器', ['报警器', '报警装置', '报警仪']],
  ['通信装置', ['通信装置', '通讯装置', '通信设备', '通讯设备']],
  ['配电箱', [...equivalentNames('配电箱'), '电箱', '开关箱']],
  ['配电室', equivalentNames('配电室')],
  ['电气线路', [...equivalentNames('电气线路'), '电线', '电源线', '电缆']],
  ['插座', ['插座']], ['插排', equivalentNames('插排')],
  ['漏电保护器', [...equivalentNames('漏电保护器'), ...equivalentNames('漏电保护')]],
  ['电动自行车', ['电动自行车', '电瓶车']], ['自行车', ['自行车']],
  ['起重机', [...equivalentNames('起重机'), '起重机械', '起重设备', '桥式起重机', '门式起重机', '龙门吊']],
  ['起升高度限位器', ['起升高度限位器', '起升高度限制器', '起升高度限位装置', '高度限位装置', '高度限位器', '上限位器', '上限位', '限位器']],
  ['吊钩', ['吊钩']], ['电动葫芦', equivalentNames('电动葫芦')], ['叉车', ['叉车']],
  ['气瓶', ['气瓶', '钢瓶', '氧气瓶', '乙炔瓶', '溶解乙炔气瓶']],
  ['固定式压力容器', ['固定式压力容器', '压力容器']],
  ['压力表', ['压力表']], ['安全阀', ['安全阀']],
  ['洗眼器', equivalentNames('洗眼器')],
  ['防护罩', ['防护罩', '护罩', '防护装置', '罩子']],
  ['安全带', ['安全带']], ['安全帽', ['安全帽']], ['防护栏杆', equivalentNames('防护栏杆')],
  ['危险化学品仓库', equivalentNames('危险化学品仓库')],
  ['普通化学品', ['普通化学品']], ['危险化学品', equivalentNames('危险化学品')],
  ['危险废物', equivalentNames('危险废物')], ['有限空间', equivalentNames('有限空间')],
  ['培训记录', ['培训记录', '培训签到表', '培训档案']],
  ['消防检测报告', ['消防检测报告', '消防设施检测报告', '年度消防检测报告']],
  ['检验报告', ['检验报告', '检测报告', '检定报告', '校验报告']],
  ['检查记录', ['检查记录', '检查台账']],
  ['培训', ['培训', '安全教育']], ['应急演练', equivalentNames('应急演练')],
];
const OBJECT_TOKENS = OBJECT_NAMES.flatMap(([key, names]) => [...new Set(names)].map(name => ({key, name})))
  .sort((a, b) => b.name.length - a.name.length);

function scanFieldObjects(value) {
  const text = compact(value).toLowerCase(), found = [];
  for (let i = 0; i < text.length;) {
    const match = OBJECT_TOKENS.find(item => text.startsWith(item.name, i)
      && !(item.name === '行车' && (text[i - 1] === '自' || /^(?:制动|道|路线|速度)/.test(text.slice(i + 2))))
      && !(item.name === '天车' && /[露每]/.test(text[i - 1] || '')));
    if (match) {found.push({...match, index: i}); i += match.name.length;} else i++;
  }
  return found;
}

export function fieldObjects(value) {
  return [...new Map(scanFieldObjects(value).map(item => [item.key, item])).values()];
}

const UNCERTAIN = /(?:未确认|未核实|未查明|没查清|没确认|没核实|待核实|待确认|待核查|不确定|不知道|不清楚|疑似(?!职业病)|怀疑|好像|似乎|或许|可能|大概|是否|是不是|有没有|坏没坏|失压与否)/;
const NEGATIVE_PREFIX = /(?:(?:没有|没|未|不|不存在)(?:明显|再次|再|真的|真正)?(?:被[^,，;；。]{0,12})?|(?:未发现|没有发现|没发现|未见|未查出|没查出)[^,，;；。]{0,18}|(?:不是|并非|不属于)[^,，;；。]{0,12})$/;
const COMPLETED = /(?<!未)(?:已经|已)(?:修好|修复|整改完成|更换|换好|维修完成|处理完|清理完|清走|清掉|疏通|排除|恢复正常|接好)(?:了)?/g;
const NORMAL = /(?:压力(?:正常|充足)|完好无损|玻璃完整|刻度清楚|(?:还|仍)(?:在)?有效期内|还没到期|尚未到期|(?:现在|目前)(?:已经|已)?(?:正常|完好|畅通)|(?:正常|完好|畅通)$)/;
const STATE_PATTERNS = [
  ['pressure_loss', /失压|欠压|没(?:有)?压力|一点压力都没有|压力(?:都)?(?:没了|没有了|不足|不够)/g],
  ['grounding', /(?:没(?:有)?|未)(?:可靠|正确)?(?:保护)?接地|(?:没(?:有)?|未)(?:做|作|设置)?(?:保护连接|保护导体连接|跨接)|(?:接地线|地线|PE线).{0,8}(?:断开|断了|脱落|没接|未接)/gi],
  ['damaged', /损坏|坏了|坏掉|坏(?=$)|失效|故障|失灵|破损|破裂|裂了|裂开|碎了|不亮|不能正常|不能点亮|不动作|不工作|未保持(?:正常|适用)/g],
  ['absent', /(?:未|没有|没)(?:曾经)?(?:按规定)?(?:安装|装设|设置|配置|配备|装)(?:过)?|缺少|缺失/g],
  ['obstructed', /堵塞|堵住|堵了|被堵|被挡|挡住|遮挡|受阻|不畅通|堆(?:放|积|东西|杂物|纸箱|物|满|着|了)|塞满|占用|圈占|过不去|走不过去|无法通行|不能通行|无法通过/g],
  ['charging_wiring', /(?:飞线|拉线|拖线)充电/g],
  ['not_worn', /(?:没(?:有)?|未|不)(?:正确)?(?:佩戴|戴|系)(?:好|上)?(?:安全帽|安全带)?/g],
  ['understaffed', /只有(?:一|1)(?:名|个)?人|(?:仅|只)(?:安排|有)(?:一|1)(?:名|个)?人|(?:单人|一人)(?:值班|值守|在岗)|无人值守|没人值班/g],
];
const uniqueObjects = objects => [...new Map(objects.map(object => [object.key, object])).values()];

function claimSubjects(text, clause, claim, objects) {
  const inClause = objects.filter(object => object.index >= clause.index && object.index < clause.end);
  const before = inClause.filter(object => object.index < claim.index);
  const after = inClause.filter(object => object.index >= claim.index + claim.text.length);
  let target;
  // A missing component is the object after the installation verb. The parent
  // machine before that verb is context, not itself an absent machine.
  if (claim.defect === 'absent') {
    target = after.find(object => object.index - claim.index - claim.text.length <= 14);
    const tail = text.slice(claim.index + claim.text.length, clause.end).replace(/^(?:过|任何|相应|规定的|了|的)+/, '');
    if (!target && tail && !/^(?:过|了|而已)$/.test(tail)) return [];
  }
  target ||= before.at(-1);
  target ||= inClause.filter(object => object.index >= claim.index && object.index < claim.index + claim.text.length).at(-1);
  target ||= after.find(object => object.index - claim.index - claim.text.length <= 16);
  if (!target) {
    // Only a grammatical continuation may inherit the preceding device. A new
    // unknown subject such as “旁边的窗户坏了” is not a fault of the last device.
    const continuation = /^(?:还|也|仍|却|又|现在|目前|其|它|该(?:表|灯|设备|装置)|表(?:本身|的)?|玻璃|刻度|指针|外壳|检定|检验|有效期|柜门|箱门|门板|门与|门和|断电|通电|试验|测试|人都|人已|帽子|安全帽|已|已经|没有|没|未|不)/.test(clause.text);
    if (continuation) target = objects.filter(object => object.index < clause.index).at(-1);
  }
  if (!target) return [];
  const bridge = text.slice(target.index + target.name.length, claim.index);
  if (claim.defect === 'damaged' && /(?:旁边|附近|旁的).{0,8}$/.test(bridge)) return [];
  const selected = [target];
  const previous = inClause.filter(object => object.index < target.index).at(-1);
  if (previous && /^(?:和|与|及|、|或|以及)$/.test(text.slice(previous.index + previous.name.length, target.index))) selected.unshift(previous);
  // A pressure indicator attached to an extinguisher is not an independent
  // pressure-vessel gauge. Preserve this equipment identity across particles.
  if (selected.some(object => object.key === '压力表') && objects.some(object => object.key === '灭火器')) {
    return [{key: '灭火器压力表', name: '灭火器压力表', index: target.index}];
  }
  return selected;
}

/** Each state has its own polarity and subject. A normal glass cover must not
 * cancel a separately observed overdue verification, and “没有被货物堵住”
 * must not become a positive blockage merely because 堵住 is present. */
export function analyzeFieldObservation(value) {
  const text = compact(value), objects = scanFieldObjects(text), claims = [], clauses = [];
  const clausePattern = /[^,，;；。!?？！\n]+/g;
  for (const match of text.matchAll(clausePattern)) {
    let start = 0;
    const contrasts = [...match[0].matchAll(/但是|但|然而|不过|可是|而是/g)];
    for (const contrast of [...contrasts, {index: match[0].length, 0: ''}]) {
      const body = match[0].slice(start, contrast.index);
      if (body) clauses.push({text: body, index: match.index + start, end: match.index + contrast.index});
      start = contrast.index + contrast[0].length;
    }
  }
  for (const clause of clauses) {
    const add = (defect, match) => {
      const prefix = clause.text.slice(0, match.index);
      const claim = {defect, text: match[0], index: clause.index + match.index,
        polarity: UNCERTAIN.test(clause.text) ? 'uncertain' : NEGATIVE_PREFIX.test(prefix) ? 'negated' : 'affirmed'};
      claim.subjects = claimSubjects(text, clause, claim, objects);
      claims.push(claim);
    };
    for (const [defect, pattern] of STATE_PATTERNS) for (const match of clause.text.matchAll(pattern)) add(defect, match);
    // Validity is a state, not a synonym for breakage. Identify which validity
    // is being discussed from the nearest explicit verification/inspection term.
    for (const match of clause.text.matchAll(/超期|过期|超过(?:检定|检验)?有效期|有效期(?:已经|已)?(?:过了|到期了)/g)) {
      const context = text.slice(0, clause.index + match.index + match[0].length);
      const verification = context.lastIndexOf('检定'), inspection = Math.max(context.lastIndexOf('定期检验'), context.lastIndexOf('年检'));
      if (verification >= 0 || inspection >= 0) add(verification > inspection ? 'verification_overdue' : 'inspection_overdue', match);
    }
    if (/压力表|刻度/.test(text)) for (const match of clause.text.matchAll(/(?:看不清|模糊不清|刻度不清)/g)) add('damaged', match);
    for (const match of clause.text.matchAll(/(?:没有|没|无)(?:任何)?(?=报警装置|报警器|通信装置|通讯装置|通信设备|通讯设备|配电箱|灭火器|应急灯|起升高度限位|高度限位|上限位)/g)) add('absent', match);
    // A clearly described omission during work; merely putting a helmet aside
    // outside work is not enough to infer non-use or an obligation to wear it.
    if (objects.some(object => object.key === '安全帽')) {
      for (const match of clause.text.matchAll(/(?:安全帽|帽子)(?:却|还|仍)?(?:放|搁|摆)(?:在|到)?(?:一边|旁边|旁|地上).{0,10}(?:开工|干活|作业|上岗)/g)) add('not_worn', match);
    }
  }
  claims.sort((a,b) => a.index - b.index);
  const completed = [...text.matchAll(COMPLETED)];
  for (const claim of claims) {
    if (claim.polarity !== 'affirmed') continue;
    const completion = completed.find(match => match.index > claim.index);
    if (completion && !['verification_overdue', 'inspection_overdue'].includes(claim.defect)) claim.polarity = 'historical';
  }
  // Later corrections of the same state apply to that state, not all devices
  // and all other states in the sentence.
  const latest = new Map();
  for (const claim of claims) for (const object of claim.subjects) latest.set(`${object.key}:${claim.defect}`, claim);
  const activeClaims = claims.filter(claim => claim.polarity === 'affirmed' && claim.subjects.some(object => latest.get(`${object.key}:${claim.defect}`) === claim));
  const uncertainTail = clauses.at(-1);
  if (uncertainTail && /^(?:尚未核实|尚未确认|还没核实|还没确认|未查明|是不是这样|是否如此)/.test(uncertainTail.text)
      && !claims.some(claim => claim.index >= uncertainTail.index)) activeClaims.length = 0;
  return {claims, activeClaims, objects: uniqueObjects(objects),
    subjects: uniqueObjects(activeClaims.flatMap(claim => claim.subjects)),
    defects: [...new Set(activeClaims.map(claim => claim.defect))],
    negatedDefects: [...new Set(claims.filter(claim => claim.polarity === 'negated').map(claim => claim.defect))],
    hasUncertainty: UNCERTAIN.test(text), hasCompleted: completed.length > 0, hasNormal: NORMAL.test(text),
    hasState: claims.length > 0 || UNCERTAIN.test(text) || completed.length > 0 || NORMAL.test(text)};
}

const completeIssue = value => {
  const interpretation = interpretFieldQuery(value);
  return interpretation.objects.length > 0 && interpretation.observation.hasState;
};

/** Split only when both sides name an object and a state. Commas in a condition
 * or a formal title, an object list with a shared state, and explanatory tails
 * are not arbitrarily turned into independent AND requirements. Exact titles
 * are handled by the caller before this function. */
export function splitFieldQuery(value) {
  const query = String(value ?? '').trim();
  if (!query) return [''];
  const separator = /[,，;；。\n]+|(?:另外|还有|而且|并且|同时|以及)|[和与且]/g;
  const issues = [];
  let remaining = query;
  while (issues.length < 7) {
    separator.lastIndex = 0;
    let cut = null;
    const separators=[...remaining.matchAll(separator)].sort((a,b)=>Number(/[;；。\n]/.test(b[0]))-Number(/[;；。\n]/.test(a[0]))||a.index-b.index);
    for (const match of separators) {
      const left = remaining.slice(0, match.index).trim();
      const right = remaining.slice(match.index + match[0].length).trim();
      const firstRightClause=right.replace(/^(?:(?:另外|还有|而且|并且|同时|以及)|[,，\s])+/, '').split(/[,，;；。\n]/)[0];
      // Keep “柜门打不开”“刻度看不清” with the preceding device; a later
      // independently named device must not pull that shared explanation away.
      if (fieldObjects(interpretFieldQuery(firstRightClause).query).length
          && completeIssue(left) && completeIssue(right)) {cut = {left, right}; break;}
    }
    if (!cut) break;
    issues.push(cut.left); remaining = cut.right;
  }
  issues.push(remaining);
  return issues;
}

const TYPO_PAIRS = [
  ['灭活器', '灭火器'], ['灭伙器', '灭火器'], ['灭火气', '灭火器'],
  ['配点箱', '配电箱'], ['输散通道', '疏散通道'], ['疏撒通道', '疏散通道'],
  ['消火拴', '消火栓'], ['消防拴', '消防栓'],
];
const SCENES = ['普通工业车间', '普通车间', '生产车间', '车间', '建筑施工', '市政施工', '施工现场', '工贸企业', '仓库', '库房', '仓储', '喷涂', '喷漆', '餐饮', '加油站', '粉尘涉爆', '人员密集场所', '高层建筑', '江苏', '南京'];

// No blanket removal of 没、未、不、已、是否、好像 or other status words.
// Only conversational framing is removed; the original sentence is retained.
export function interpretFieldQuery(value, {correctTypos = true} = {}) {
  const original = String(value ?? '').trim(), corrections = [];
  let query = textOf(original);
  for (const [wrong, right] of correctTypos ? TYPO_PAIRS : []) if (query.includes(wrong)) {
    corrections.push({from: wrong, to: right}); query = query.replaceAll(wrong, right);
  }
  query = query
    .replace(/^(?:(?:请|麻烦)(?:你)?(?:帮我|帮忙)?(?:查一下|查查|查询|找一下)|帮我(?:查一下|查询|看看))[:：,，\s]*/g, '')
    .replace(/^(?:(?:我(?:们)?(?:今天|刚才)?|今天|刚才)?(?:在)?(?:现场)?(?:检查|巡查)(?:的?时候|时|中)?(?:看到|发现)|(?:我(?:们)?|现场)(?:看到|发现)|今天(?:看到|发现)|发现|看到)[:：,，\s]*/g, '')
    .replace(/[,，\s]*(?:请问)?(?:这个|这种|这类)?(?:问题)?(?:该怎么整改|怎么整改|该怎么办|怎么处理|有什么依据|依据是什么|对应什么条款|应查什么|算不算隐患)(?:呢|啊|吗|[?？])?$/g, '')
    .replace(/^(?:另外|还有|而且|并且|同时)\s*/, '')
    .replace(/(?:这个|那个|这只|那只|这台|那台|这盏|那盏)/g, '')
    .replace(/(?:里面|里边)(?:的)?/g, '内')
    .replace(/电箱/g, '配电箱')
    .replace(/配配电箱/g, '配电箱')
    .replace(/(?:配电箱|配电柜)(?:的)?门(?:上)?没有接地线/g, '配电箱门未接地')
    .replace(/(应急灯|应急照明灯|消防应急灯)(?:安装(?:以后|之后|后)|装好后)/g, '$1')
    .replace(/^(?:安装(?:以后|之后|后)|装好后)(应急灯|应急照明灯|消防应急灯)/g, '$1')
    .replace(/(?:供|用于|用来)(?:人员)?疏散(?:使用|通行)?的?(?:过道|通道|走道)/g, '疏散通道')
    .replace(/(疏散通道|消防通道|消防车道|通道)(?:里|内|中|上|的)?(?:还|也)?(?:堆满|堆着|堆了|堆有|堆放了|摆放了|摆满)(?:了)?(?:许多|很多|大量|一些|一堆|几堆)?(?:纸箱|东西|杂物|物料|货物)/g, '$1堆放')
    .replace(/(灭火器)(?:的)?(?:一点压力都没有|没有压力|压力没有了|压力不足|压力不够|没压力)(?:了)?/g, '$1失压')
    .replace(/(压力表)(?:的)?检定(?:日期|有效期)(?:已经|已)?(?:过了|过期了|到期了)/g, '$1检定超期')
    .trim();
  const scenes = SCENES.filter(scene => original.includes(scene));
  // Location remains available for ranking and interpretation. It is not an
  // added fact about a rule's legal scope and never becomes a silent filter.
  const leadingLocation = /^(?:在)?(?:现场|生产车间|车间|厂房|仓库|库房)(?:内|里|中|的|内的)?/.exec(query);
  if (leadingLocation && fieldObjects(query.slice(leadingLocation[0].length)).length) query = query.slice(leadingLocation[0].length).trim();
  query = query.replace(/^(?:的|内的)/, '').replace(/[。?!？！]+$/, '').trim();
  const observation = analyzeFieldObservation(query);
  const {objects, subjects, defects, negatedDefects} = observation;
  const quantitativeFacts = [...new Set([...textOf(original).matchAll(/\d+(?:\.\d+)?\s*(?:MPa|kPa|mm|cm|kg|m³|m3|m|米|厘米|毫米|年|个月|月|天|小时|分钟|公斤|吨|%)/gi)].map(match=>match[0]))];
  return {original, query, changed: query !== original, corrections, scenes, objects, subjects,
    contextObjects: objects.filter(object=>!subjects.some(subject=>subject.key===object.key)),
    defects, negatedDefects, quantitativeFacts, observation};
}

const termIn = (text, term) => term === '行车' ? /(?<!自)行车(?!制动|道|路线|速度)/.test(text) : text.includes(term);
export function fieldObjectMatches(row, object) {
  const names = OBJECT_NAMES.find(([key]) => key === object.key)?.[1] || [object.name];
  const heading = [row.title, ...(row.aliases || []), ...(row.keywords || []), ...(row.fieldProfiles || []).map(profile => profile.title)].join(' ').toLowerCase();
  // A crane is never identified by a bicycle's incidental mention.
  return names.some(name => termIn(heading, name));
}

const DEFECT_HEADINGS = {
  pressure_loss: /失压|欠压|压力(?:不足|不够|指示器)|指针.*绿色范围/,
  grounding: /接地|pe连接|保护导体|门与金属框架未可靠连接|箱门电气连接/i,
  verification_overdue: /检定|检定有效期/,
  inspection_overdue: /定期检验|检验有效期|未经.*检验/,
  damaged: /损坏|破损|破裂|失效|失灵|故障|不能正常|无法正常|功能.*不符合|未保持(?:正常|适用)/,
  absent: /未(?:按规定)?(?:设置|安装|配置|配备|装设|装|设)|缺(?:少|失)|无(?:防护|盖板|扶手|栏杆)/,
  obstructed: /堵塞|堆放|堆积|占用|圈占|遮挡|受阻|阻塞|不畅通/,
  charging_wiring: /飞线充电|私拉.{0,12}充电|充电.{0,12}私拉/,
  not_worn: /未(?:按规定)?(?:正确)?(?:佩戴|戴|使用)|未系|佩戴.*不符合/,
  understaffed: /未实行.{0,10}双人值班|值班.{0,10}(?:少于|不足)|双人值班.*不符合|无人值守/,
};

export function fieldDefectMatches(row, defect, interpretation = null) {
  // Defects must be the subject of the rule. Exclusion notes or generic body
  // text mentioning another fault cannot satisfy a positive field observation.
  const heading = [row.title, ...(row.fieldProfiles || []).map(profile => profile.title)].join(' ')
    .replace(/(?:易|容易|可能)发生(?:故障|危险)/g, '');
  if (DEFECT_HEADINGS[defect] && !DEFECT_HEADINGS[defect].test(heading)) return false;
  if (defect === 'obstructed' && /(?:标志|标识|铭牌|标签)/.test(heading)
      && !/(?:标志|标识|铭牌|标签)/.test(interpretation?.query || '')
      && /(?:缺少|未设置|未设).*(?:标志|标识)|(?:标志|标识|铭牌|标签).*(?:遮挡|被挡)/.test(heading)) return false;
  if (defect === 'absent' && (interpretation?.subjects?.length || interpretation?.objects.length)) {
    const target = (interpretation.subjects?.length ? interpretation.subjects : interpretation.objects).at(-1);
    const names = OBJECT_NAMES.find(([key]) => key === target.key)?.[1] || [target.name];
    const absence = '(?:未(?:按规定)?(?:设置|安装|配置|配备|装设|装|设)|缺少|缺失|无)';
    return names.some(name => {
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      // “配电箱未设置警示标志” concerns a missing sign, not a missing box.
      // Require the missing thing itself after the verb, or an omitted object
      // at the end of the clause after that same named thing.
      return new RegExp(`${absence}(?:相应|安全|可靠的|规定的|必要的)?(?:[^，,。；;]{0,16}[、或和])?${escaped}`).test(heading)
        || new RegExp(`${escaped}.{0,16}${absence}(?:[，,。；;]|$|或(?:位置|数量|配置|方向))`).test(heading)
        || new RegExp(`${escaped}(?:缺少|缺失)`).test(heading);
    });
  }
  return true;
}

export function fieldObservationMatches(row, interpretation) {
  const claims = interpretation.observation?.activeClaims || [];
  if (!claims.length) return interpretation.objects.every(object=>fieldObjectMatches(row,object));
  // A rule may address one stated defect on one stated device. A separate
  // positive state is not silently required in the same database heading.
  return claims.some(claim=>claim.subjects.some(object=>fieldObjectMatches(row,object))
    &&fieldDefectMatches(row,claim.defect,{...interpretation,subjects:claim.subjects}));
}

export function fieldCandidateScore(row, interpretation, position = 0) {
  const title = String(row.title || ''), scopeText = [title, ...(row.places || []), row.applicability || ''].join(' ');
  let score = -Math.min(position, 50);
  for (const object of interpretation.subjects?.length ? interpretation.subjects : interpretation.objects) {
    const names = OBJECT_NAMES.find(([key]) => key === object.key)?.[1] || [object.name];
    score += names.some(name => termIn(title, name)) ? 80 : fieldObjectMatches(row, object) ? 30 : 0;
  }
  for (const defect of interpretation.defects) if (fieldDefectMatches(row, defect, interpretation)) score += 65;
  for (const object of interpretation.contextObjects || []) if (fieldObjectMatches(row,object)) score += 25;
  for (const defect of interpretation.negatedDefects || []) if (!interpretation.defects.includes(defect)&&fieldDefectMatches(row,defect,interpretation)) score -= 40;
  for (const scene of interpretation.scenes) if (scopeText.includes(scene)) score += 45;
  // When the user has not supplied a specialised industry/building, keep a
  // broadly applicable candidate ahead of a rule requiring that extra scene.
  for (const names of [['喷涂', '喷漆'], ['餐饮'], ['加油站'], ['建筑施工', '市政施工', '施工现场'], ['粉尘涉爆'], ['高层建筑'], ['危险化学品', '危化品'], ['仓库', '仓储', '库房']]) {
    if (names.some(name=>scopeText.includes(name)) && !interpretation.scenes.some(value => names.some(name=>value.includes(name)))
      && !interpretation.objects.some(object=>names.some(name=>object.key.includes(name)))) score -= 45;
  }
  if ((row.scopes || []).includes('全国')) score += 8;
  else if ((row.scopes || []).length && !interpretation.scenes.some(scene=>(row.scopes || []).some(scope=>scene.includes(scope)||scope.includes(scene)))) score -= 20;
  if (row.mode === 'direct' || row.mode === '直接适用') score += 2;
  return score;
}
