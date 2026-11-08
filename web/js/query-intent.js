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
  ['疏散指示标志', [...equivalentNames('疏散指示标志'), ...equivalentNames('安全出口标志'), ...equivalentNames('疏散指示灯'), ...equivalentNames('安全出口指示灯')]],
  ['安全出口', equivalentNames('安全出口')],
  ['防火门', ['防火门']], ['消防门', ['消防门']],
  ['应急灯', [...equivalentNames('应急灯'), '消防应急照明灯具', '消防应急照明灯', '疏散照明']],
  ['感烟探测器', [...equivalentNames('感烟探测器'), ...equivalentNames('点型感烟探测器'), '点型火灾探测器']],
  ['洒水喷头', equivalentNames('洒水喷头')],
  ['火灾自动报警系统', equivalentNames('火灾自动报警系统')],
  ['消防控制室', equivalentNames('消防控制室')],
  ['可燃气体报警器', [...equivalentNames('可燃气体报警器'), '可燃气体报警装置', '可燃气体探测器']],
  ['报警器', ['报警器', '报警装置', '报警仪']],
  ['通信装置', ['通信装置', '通讯装置', '通信设备', '通讯设备']],
  ['配电箱', [...equivalentNames('配电箱'), '电箱', '开关箱']],
  ['配电室', equivalentNames('配电室')],
  ['电气线路', [...equivalentNames('电气线路'), ...equivalentNames('电源线'), '电线', '电缆']],
  ['插座', [...equivalentNames('插座'), ...equivalentNames('三孔插座')]], ['插排', equivalentNames('插排')],
  ['漏电保护器', [...equivalentNames('漏电保护器'), ...equivalentNames('漏电保护')]],
  ['电动自行车', ['电动自行车', '电瓶车']], ['自行车', ['自行车']],
  ['起重机', [...equivalentNames('起重机'), '起重机械', '起重设备', '桥式起重机', '门式起重机', '龙门吊']],
  ['起升高度限位器', ['起升高度限位器', '起升高度限制器', '起升高度限位装置', '高度限位装置', '高度限位器', '上限位器', '上限位', '限位器']],
  ['吊钩', ['吊钩']], ['电动葫芦', equivalentNames('电动葫芦')], ['叉车', ['叉车']],
  ['气瓶', ['气瓶', '钢瓶', ...equivalentNames('氩气瓶'), ...equivalentNames('氮气瓶'), ...equivalentNames('氧气瓶'), ...equivalentNames('溶解乙炔气瓶')]],
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

const UNCERTAIN = /(?:未确认|未核实|未查明|没查清|没确认|没核实|待核实|待确认|待核查|(?:不能|不可|无法|未能)(?:确认|确定|核实|证实|认定|排除)|(?:没有|没|尚无|暂无|无)(?:充分|确凿|足够)?证据|证据(?:尚)?不足|不确定|不知道|不清楚|疑似(?!职业病)|怀疑|好像|似乎|或许|可能|大概|是否|是不是|有没有|坏没坏|失压与否)/;
const NEGATED_OBSERVATION = /(?:没有发现|未发现|没发现|未见|未查出|没有查出|没查出)/;
const HISTORICAL = /以前|曾经|先前|过去|早先|当时|之前/;
const CURRENT_RESET = /现在|目前|当前|如今|现已|仍然|还是|又|再次|重新|已经确认|已确认|确实/g;
const NEGATIVE_PREFIX = /(?:(?:没有|没|未|不|不存在)(?:明显|再次|再|真的|真正)?(?:被[^,，;；。]{0,12})?|(?:未发现|没有发现|没发现|未见|未查出|没查出)[^,，;；。]{0,18}|(?:不是|并非|不属于)[^,，;；。]{0,12})$/;
const COMPLETED = /(?<!未)(?:已经|已)(?:修好|修复|整改完成|更换|换好|维修完成|处理完|清理完|清走|清掉|疏通|排除|恢复正常|接好|解锁|拆除|取下|补划|补画)(?:了)?/g;
const NORMAL = /(?:压力(?:正常|充足)|完好无损|玻璃完整|刻度清楚|(?:还|仍)(?:在)?有效期内|还没到期|尚未到期|(?:现在|目前)(?:已经|已)?(?:正常|完好|畅通)|(?:正常|完好|畅通)$)/;
const STATE_PATTERNS = [
  ['pressure_loss', /失压|欠压|没(?:有)?压力|没气(?:了)?|一点压力都没有|(?:压力|气压)(?:都)?(?:没了|没有了|不足|不够)/g],
  ['grounding', /(?:没(?:有)?|未)(?:可靠|正确)?(?:保护)?接地|(?:没(?:有)?|未)(?:做|作|设置)?(?:保护连接|保护导体连接|跨接)|(?:接地线|地线|PE线).{0,8}(?:断开|断了|脱落|没接|未接)/gi],
  ['damaged', /损坏|坏了|坏掉|坏(?=$)|失效|故障|失灵|破损|破裂|裂了|裂开|碎了|不亮|不能正常|不能点亮|不动作|不工作|未保持(?:正常|适用)/g],
  ['absent', /(?:未|没有|没)(?:曾经)?(?:按规定)?(?:安装|装设|设置|配置|配备|装)(?:过)?|缺少|缺失/g],
  ['obstructed', /堵塞|堵住|堵了|被堵|被挡|挡住|遮挡|受阻|不畅通|堆(?:放|积|东西|杂物|纸箱|物|满|着|了)|塞满|占用|圈占|过不去|走不过去|无法通行|不能通行|无法通过/g],
  ['locked', /上(?:了)?(?:挂)?锁|锁闭|锁住|封闭/g],
  ['unsecured', /(?:未|没(?:有)?)(?:采取|设置|安装|做好|做|作)?(?:可靠的?|有效的?)?(?:防倾倒|防倒|固定)(?:措施|装置)?|(?:没(?:有)?|未)(?:绑|装|用|设置)?(?:支架|卡箍|链条|固定夹|防倒链)|(?:放置|立放|固定)不(?:稳|牢)|(?:瓶身|瓶体)(?:就|还|仍)?(?:晃|摇晃)/g],
  ['pressure_mark_missing', /(?:未|没(?:有)?)(?:划|画|标(?:出|注)?)?(?:出)?(?:指示)?(?:工作压力的?)?红线|(?:工作压力的?)?红线(?:缺失|缺少|未划|没划)/g],
  ['overload', /超负荷|过载|超载/g],
  ['entry_elevator', /(?:推入|推进|搬入|带入|进入).{0,16}(?:住宅)?(?:电梯|户内)|(?:进|入)(?:住宅)?电梯/g],
  ['charging_wiring', /(?:飞线|拉线|拖线)充电/g],
  ['not_worn', /(?:没(?:有)?|未|不)(?:正确)?(?:佩戴|戴|系)(?:好|上)?(?:安全帽|安全带)?/g],
  ['understaffed', /只有(?:一|1)(?:名|个)?人|(?:仅|只)(?:安排|有)(?:一|1)(?:名|个)?人|(?:单人|一人)(?:值班|值守|在岗)|无人值守|没人值班/g],
];
const uniqueObjects = objects => [...new Map(objects.map(object => [object.key, object])).values()];

function statePrefix(prefix) {
  // An explicit current observation ends an earlier narrative qualifier.
  const reset=[...prefix.matchAll(CURRENT_RESET)].at(-1);
  return reset ? prefix.slice(reset.index) : prefix;
}
function componentAspect(prefix) {
  return [...prefix.matchAll(/玻璃|刻度|指针|外壳|弹簧管|芯线绝缘|线芯绝缘|绝缘层|护套|导体/g)].at(-1)?.[0] || '';
}
const securingAspect=text=>[...text.matchAll(/支架|卡箍|固定夹|链条|防倒链/g)].at(-1)?.[0]?.replace('防倒链','链条')||'';
function normalDefect(prefix, text) {
  if (/有效|尚未到期|还没到期/.test(text)) return validityDefect(prefix);
  if (/压力[^,，;；。]{0,6}$/.test(prefix)) return 'pressure_loss';
  if (/接地[^,，;；。]{0,6}$/.test(prefix)) return 'grounding';
  if (/固定(?!式)|防倾倒|防倒|链条|支架|卡箍/.test(prefix.split(/[,，;；。]/).at(-1))) return 'unsecured';
  if (/解锁/.test(text)) return 'locked';
  if (/补划|补画/.test(text)) return 'pressure_mark_missing';
  if (/拆除|取下/.test(text)&&/塑料袋|防尘罩|袋子/.test(prefix)) return 'obstructed';
  if (componentAspect(prefix.split(/[,，;；。]/).at(-1))) return 'damaged';
  if (/畅通/.test(text)) return 'obstructed';
  return '*';
}

function validityDefect(context) {
  const kinds=[['verification_overdue', /检定/g], ['inspection_overdue', /定期检验|年检/g], ['calibration_overdue', /校验|复校/g]];
  return kinds.map(([defect,pattern])=>({defect,index:[...context.matchAll(pattern)].at(-1)?.index??-1}))
    .filter(item=>item.index>=0).sort((a,b)=>b.index-a.index)[0]?.defect || '*';
}

// A small numeric grammar, not a unit/threshold inference engine. Only a
// stated rating and actual load of the same device and dimension are compared.
function numericValue(raw) {
  if (/^\d+(?:\.\d+)?$/.test(raw)) return Number(raw);
  const digits={零:0,〇:0,一:1,二:2,两:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};
  const [whole,fraction]=raw.split('点');
  let value=0,current=0;
  if (!/[十百千]/.test(whole)) value=Number([...whole].map(char=>digits[char]).join(''));
  else for (const char of whole) {
    if (char in digits) current=digits[char];
    else {value+=(current||1)*({十:10,百:100,千:1000}[char]||0);current=0;}
  }
  if (/[十百千]/.test(whole)) value+=current;
  if (fraction) value+=Number(`0.${[...fraction].map(char=>digits[char]).join('')}`);
  return value;
}

export function fieldQuantities(value) {
  const text=compact(value), objects=scanFieldObjects(text), measurements=[];
  const pattern=/(\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千]+(?:点[零〇一二两三四五六七八九]+)?)\s*(安培|毫安|千瓦|MPa|kPa|mm|cm|kg|m³|m3|个月|小时|分钟|厘米|毫米|公斤|千伏|kW|mA|安|瓦|伏|升|米|年|月|天|吨|%|A|W|V|m)(?![a-z])/gi;
  for(const match of text.matchAll(pattern)) {
    const unit=match[2].toLowerCase(), current=/^(?:a|安|安培|ma|毫安)$/.test(unit), power=/^(?:w|瓦|kw|千瓦)$/.test(unit);
    const dimension=current?'current':power?'power':'other';
    const scale=/^(?:ma|毫安)$/.test(unit)?0.001:/^(?:kw|千瓦)$/.test(unit)?1000:1;
    const prefix=text.slice(Math.max(0,match.index-40),match.index).split(/[;；。]/).at(-1);
    const rated=[...prefix.matchAll(/额定|铭牌|标称/g)].at(-1)?.index??-1;
    const actual=[...prefix.matchAll(/实测|实际|测得|测出|测量|同时(?:运行|开|使用)|达到/g)].at(-1)?.index??-1;
    const kind=actual>rated?'actual':rated>=0?'rated':'';
    let owner=objects.filter(object=>object.index<match.index&&object.key==='插排').at(-1);
    if(owner){
      const clauseStart=Math.max(text.lastIndexOf('，',match.index),text.lastIndexOf(',',match.index),text.lastIndexOf('；',match.index),text.lastIndexOf(';',match.index),text.lastIndexOf('。',match.index))+1;
      const clausePrefix=text.slice(clauseStart,match.index);
      const intervening=objects.some(object=>object.index>owner.index&&object.index<match.index);
      const continuation=/^(?:(?:现场|电工|维修人员)(?:确认|测量)?)?(?:实测|实际|测得|测出|测量|同时(?:运行|开|使用)|额定|铭牌|其|它|这块|该插排)/.test(clausePrefix);
      const newSubject=/(?:旁边|隔壁|另一|另外).{0,20}(?:实测|实际|测得|测出)/.test(text.slice(owner.index+owner.name.length,match.index));
      if(intervening||newSubject||(owner.index<clauseStart&&!continuation))owner=null;
    }
    measurements.push({raw:match[0],value:numericValue(match[1])*scale,unit:current?'A':power?'W':match[2],dimension,kind,index:match.index,
      owner:owner?{...owner}:null,unconfirmed:/(?:没(?:有)?|未)(?:看|量|测|核实|确认)|不知道|不清楚/.test(prefix)});
  }
  return measurements;
}

const SUBJECT_REFERENCES = [
  [/灯具|这盏灯|该灯|灯本身/, ['疏散指示标志','应急灯']],
  [/芯线|线芯|绝缘(?:层)?|铜导体|护套/, ['电气线路']],
  [/接地孔|接地极|端子|插孔/, ['插座','插排','配电箱']],
  [/表盘|刻度盘|玻璃|刻度|指针|表本身/, ['压力表','灭火器压力表']],
  [/阀体|校验|复校/, ['安全阀']],
  [/瓶身|瓶体|防倒链|支架|卡箍|链条/, ['气瓶']],
  [/塑料袋|防尘罩|袋子/, ['感烟探测器']],
  [/红线/, ['压力表']],
  [/出口门|门锁|解锁/, ['安全出口','防火门','消防门']],
  [/额定|实测|实际负荷|电流|功率/, ['插排']],
];

function inheritedSubject(text,clause, claim, objects) {
  const prior=objects.filter(object=>object.index<clause.index);
  // A typed component or pronoun can refer back through an observer's
  // sentence, while an explicitly different unknown device cannot.
  for(const [pattern,keys] of SUBJECT_REFERENCES) if(pattern.test(clause.text)) {
    if(keys.includes('应急灯')&&/普通(?:照明)?灯/.test(clause.text))continue;
    const target=prior.filter(object=>keys.includes(object.key)).at(-1);
    if(target){
      // Do not jump over a more recent, explicitly different lighting subject
      // merely because it has no matching equipment family in the index.
      if(keys.includes('应急灯')&&/普通(?:照明)?灯(?:具)?/.test(text.slice(target.index+target.name.length,clause.index))){
        claim.referenceOnly=true;return undefined;
      }
      return target;
    }
  }
  const prefix=clause.text.slice(0,claim.index-clause.index);
  const bare=/^(?:(?:也|还|仍|却|又|现在|目前|已经|已|确实|一直|根本|就是|就|从来|从未|从没|没有|没|未|不|还没有|也没有)*)$/.test(prefix);
  const continuation=/^(?:还|也|仍|却|又|现在|目前|其|它|该(?:表|灯|设备|装置)|表(?:本身|的)?|玻璃|刻度|指针|外壳|检定|检验|有效期|柜门|箱门|门板|门与|门和|断电|通电|试验|测试|人都|人已|帽子|安全帽|已|已经|没有|没|未|不)/.test(clause.text);
  return bare||continuation?prior.at(-1):undefined;
}

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
  if (!target) target=inheritedSubject(text,clause,claim,objects);
  if (!target) return [];
  const bridge = text.slice(target.index + target.name.length, claim.index);
  if ((claim.defect === 'damaged'||claim.polarity==='normal')
      && /(?:旁边|附近|旁的|隔壁|(?:上|下|左|右)(?:面|方|侧)|前方|后方).{0,16}$/.test(bridge)) {
    claim.referenceOnly=true;return [];
  }
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
      const scopePrefix=statePrefix(prefix);
      const claim = {defect, text: match[0], index: clause.index + match.index,
        aspect:defect==='damaged'?componentAspect(prefix):defect==='unsecured'?securingAspect(match[0]):'',
        polarity: UNCERTAIN.test(clause.text) ? 'uncertain'
          : NEGATED_OBSERVATION.test(scopePrefix)||NEGATIVE_PREFIX.test(prefix)
            ||/(?:没(?:有)?|未|不)[^,，;；。]{1,14}(?:或|和|以及|、)$/.test(prefix) ? 'negated'
          : HISTORICAL.test(scopePrefix)||/(?:已经|已)(?:排除|消除|修复|修好|解决)/.test(scopePrefix) ? 'historical' : 'affirmed'};
      claim.subjects = claimSubjects(text, clause, claim, objects);
      const typedSubjects={pressure_mark_missing:['压力表'],overload:['插排'],entry_elevator:['电动自行车','自行车']};
      if(typedSubjects[defect])claim.subjects=claim.subjects.filter(subject=>typedSubjects[defect].includes(subject.key));
      claims.push(claim);
    };
    for (const [defect, pattern] of STATE_PATTERNS) for (const match of clause.text.matchAll(pattern)) add(defect, match);
    // Validity is a state, not a synonym for breakage. Identify which validity
    // is being discussed from the nearest explicit verification/inspection term.
    for (const match of clause.text.matchAll(/超期|过期|超过(?:检定|检验|校验)?有效期|(?:有效期|期限|周期|日期)(?:已经|已)?(?:过了|到期了)/g)) {
      const context = text.slice(0, clause.index + match.index + match[0].length);
      const defect=validityDefect(context);
      if(defect!=='*')add(defect,match);
    }
    if(objects.some(object=>object.key==='感烟探测器'))for(const match of clause.text.matchAll(/(?:包着|包住|包裹|套着|套住)(?:塑料袋|防尘罩|袋子)|(?:塑料袋|防尘罩|袋子)(?:还)?(?:未拆|没拆|未取下|没取下)/g))add('obstructed',match);
    if(objects.some(object=>object.key==='电气线路'))for(const match of clause.text.matchAll(/(?:铜)?导体(?:直接)?(?:露在外面|外露|裸露)/g))add('damaged',match);
    if (/压力表|刻度/.test(text)) for (const match of clause.text.matchAll(/(?:看不清|模糊不清|刻度不清)/g)) add('damaged', match);
    for (const match of clause.text.matchAll(/(?:没有|没|无)(?:任何)?(?=报警装置|报警器|通信装置|通讯装置|通信设备|通讯设备|配电箱|灭火器|应急灯|起升高度限位|高度限位|上限位)/g)) add('absent', match);
    // A clearly described omission during work; merely putting a helmet aside
    // outside work is not enough to infer non-use or an obligation to wear it.
    if (objects.some(object => object.key === '安全帽')) {
      for (const match of clause.text.matchAll(/(?:安全帽|帽子)(?:却|还|仍)?(?:放|搁|摆)(?:在|到)?(?:一边|旁边|旁|地上).{0,10}(?:开工|干活|作业|上岗)/g)) add('not_worn', match);
    }
    // Normal and completed states have subjects too. A lamp being repaired
    // cannot resolve a separate extinguisher defect; a complete glass cover
    // does not disprove a broken pointer or an overdue verification.
    for (const match of clause.text.matchAll(/恢复正常|正常|完好(?:无损)?|完整|清楚|清晰|畅通|有效期内|(?:还|仍)有效|尚未到期|还没到期|牢固|稳固|(?<!未)(?:已经|已)(?:修好|修复|整改完成|更换|换好|维修完成|处理完|清理完|清走|清掉|疏通|排除|恢复正常|接好|解锁|拆除|取下|补划|补画)(?:了)?/g)) {
      const prefix=clause.text.slice(0,match.index);
      if (/(?:不能|没有|没|未|不)(?:恢复|保持)?$/.test(prefix)) continue;
      const defect=normalDefect(text.slice(0,clause.index+match.index),match[0]);
      const aspect=defect==='unsecured'?securingAspect(prefix):componentAspect(prefix);
      const claim={defect,aspect,
        text:match[0],index:clause.index+match.index,
        polarity:UNCERTAIN.test(clause.text)?'uncertain':HISTORICAL.test(statePrefix(prefix))?'historical_normal':'normal'};
      claim.subjects=claimSubjects(text,clause,claim,objects);claims.push(claim);
    }
  }
  const quantities=fieldQuantities(text);
  for(const actual of quantities.filter(item=>item.kind==='actual'&&item.owner&&!item.unconfirmed&&item.dimension!=='other')){
    const rated=quantities.filter(item=>item.kind==='rated'&&!item.unconfirmed&&item.owner?.index===actual.owner.index&&item.dimension===actual.dimension&&item.index<actual.index).at(-1);
    if(rated)claims.push({defect:'overload',text:`${rated.raw} / ${actual.raw}`,index:actual.index,aspect:'',
      polarity:actual.value>rated.value?'affirmed':'normal',subjects:[actual.owner],comparison:{rated,actual}});
  }
  claims.sort((a,b) => a.index - b.index);
  const completed = [...text.matchAll(COMPLETED)];
  // Later corrections of the same state apply to that state, not all devices
  // and all other states in the sentence.
  const overrides=(later,claim,object)=>later.index>claim.index
    &&['affirmed','negated','uncertain','normal'].includes(later.polarity)
    &&later.subjects.some(subject=>subject.key===object.key)
    &&(later.defect===claim.defect||(later.defect==='*'&&!['verification_overdue','inspection_overdue','calibration_overdue','pressure_mark_missing'].includes(claim.defect)))
    &&(!later.aspect||later.aspect===claim.aspect);
  const adequateAlternative=(claim,object)=>claim.defect==='unsecured'&&claim.aspect&&claims.some(normal=>
    normal.defect==='unsecured'&&normal.polarity==='normal'&&normal.aspect!==claim.aspect
    &&normal.subjects.some(subject=>subject.key===object.key)
    &&!claims.some(later=>later.index>normal.index&&later.defect==='unsecured'&&later.polarity==='affirmed'
      &&later.subjects.some(subject=>subject.key===object.key)&&(!later.aspect||later.aspect===normal.aspect)));
  const activeClaims = claims.filter(claim => claim.polarity === 'affirmed' && claim.subjects.some(object => !claims.some(later=>overrides(later,claim,object))&&!adequateAlternative(claim,object)));
  const uncertainTail = clauses.at(-1);
  if (uncertainTail && /^(?:尚未核实|尚未确认|还没核实|还没确认|未查明|是不是这样|是否如此)/.test(uncertainTail.text)
      && !claims.some(claim => claim.index >= uncertainTail.index)) activeClaims.length = 0;
  return {claims, activeClaims, objects: uniqueObjects(objects),
    subjects: uniqueObjects(activeClaims.flatMap(claim => claim.subjects)),
    defects: [...new Set(activeClaims.map(claim => claim.defect))],
    negatedDefects: [...new Set(claims.filter(claim => claim.polarity === 'negated').map(claim => claim.defect))],
    hasUncertainty: UNCERTAIN.test(text), hasCompleted: completed.length > 0, hasNormal: NORMAL.test(text),
    hasHistorical:claims.some(claim=>['historical','historical_normal'].includes(claim.polarity)),
    unresolvedReference:claims.some(claim=>claim.referenceOnly&&claim.polarity==='affirmed'),
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
export function splitFieldIssues(value) {
  const query = String(value ?? '').trim();
  if (!query) return [{query:''}];
  const separator = /[,，;；。\n]+|(?:另外|还有|而且|并且|同时|以及)|[和与且]/g;
  const issues = [];
  let remaining = query, inherited=null;
  while (issues.length < 7) {
    separator.lastIndex = 0;
    let cut = null;
    const separators=[...remaining.matchAll(separator)].sort((a,b)=>Number(/[;；。\n]/.test(b[0]))-Number(/[;；。\n]/.test(a[0]))||a.index-b.index);
    for (const match of separators) {
      const left = remaining.slice(0, match.index).trim();
      const right = remaining.slice(match.index + match[0].length).trim();
      if (/^(?:和|与|且|以及|而且|并且)$/.test(match[0])) {
        const meaning=interpretFieldQuery(left);
        const first=meaning.observation.claims.find(claim=>claim.defect!=='*'&&claim.subjects.length);
        const firstSubject=first?.subjects[0]?.index;
        const prefix=firstSubject===undefined?'':compact(meaning.query).slice(0,firstSubject);
        // “未发现 A 和 B” describes one shared observation scope. Cutting
        // at 和 would strip the qualifier from B and invent a positive fact.
        if (NEGATED_OBSERVATION.test(prefix)||UNCERTAIN.test(prefix)||HISTORICAL.test(prefix)
            ||/(?:已经|已)(?:排除|消除|修复|修好|解决)/.test(prefix)) continue;
      }
      const firstRightClause=right.replace(/^(?:(?:另外|还有|而且|并且|同时|以及)|[,，\s])+/, '').split(/[,，;；。\n]/)[0];
      // Keep “柜门打不开”“刻度看不清” with the preceding device; a later
      // independently named device must not pull that shared explanation away.
      const leftLookup=inherited?`${inherited.name}，${left}`:left;
      if ((fieldObjects(interpretFieldQuery(firstRightClause).query).length||/[;；。\n]/.test(match[0]))
          && completeIssue(leftLookup) && completeIssue(right)) {cut = {left, right}; break;}
      // Independent defects can concern the same object. Carry only an
      // explicitly typed subject into the second query; do not turn a second
      // description of the same breakage into another hazard.
      const meaning=interpretFieldQuery(leftLookup);
      const subject=meaning.subjects.at(-1);
      if(subject&&!fieldObjects(firstRightClause).length&&/[,，;；。\n]/.test(match[0])){
        const rightMeaning=interpretFieldQuery(`${subject.name}，${right}`);
        const rightClaims=rightMeaning.observation.activeClaims;
        const firstRightClaim=rightClaims.find(claim=>claim.subjects.some(object=>object.key===subject.key));
        if(firstRightClaim&&meaning.defects.length
            &&rightClaims.every(claim=>claim.subjects.every(object=>object.key===subject.key))
            &&rightMeaning.defects.every(defect=>!meaning.defects.includes(defect))){
          cut={left,right,inherited:subject};break;
        }
      }
    }
    if (!cut) break;
    issues.push({query:cut.left,inheritedSubject:inherited}); remaining = cut.right;inherited=cut.inherited||null;
  }
  issues.push({query:remaining,inheritedSubject:inherited});
  return issues;
}

export const splitFieldQuery=value=>splitFieldIssues(value).map(issue=>issue.query);

const TYPO_PAIRS = [
  ['灭活器', '灭火器'], ['灭伙器', '灭火器'], ['灭火气', '灭火器'],
  ['配点箱', '配电箱'], ['输散通道', '疏散通道'], ['疏撒通道', '疏散通道'],
  ['消火拴', '消火栓'], ['消防拴', '消防栓'], ['插坐', '插座'],
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
  const quantities=fieldQuantities(original);
  const quantitativeFacts = [...new Set(quantities.map(item=>item.raw))];
  return {original, query, changed: query !== original, corrections, scenes, objects, subjects,
    contextObjects: objects.filter(object=>!subjects.some(subject=>subject.key===object.key)),
    defects, negatedDefects, quantitativeFacts, quantities, observation};
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
  inspection_overdue: /未.{0,14}定期检验|(?:超过|超出).{0,8}检验(?:有效期|期限|周期)|(?:定期检验|检验有效期).*(?:超期|过期)/,
  calibration_overdue: /未.{0,14}(?:校验|复校)|(?:超过|超出).{0,8}校验(?:有效期|期限|周期)|校验.*(?:超期|过期)/,
  damaged: /损坏|破损|破裂|失效|失灵|故障|不能正常|无法正常|功能.*不符合|未保持(?:正常|适用)/,
  absent: /未(?:按规定)?(?:设置|安装|配置|配备|装设|装|设)|缺(?:少|失)|无(?:防护|盖板|扶手|栏杆)/,
  obstructed: /堵塞|堆放|堆积|占用|圈占|遮挡|受阻|阻塞|不畅通/,
  locked: /(?:出口|疏散门|通道).*(?:封闭|锁闭|上锁|不畅通|畅通)|(?:封闭|锁闭).*(?:出口|疏散门|通道)/,
  unsecured: /防倾倒|防倒|未.{0,12}固定|固定.{0,12}不(?:可靠|牢)/,
  pressure_mark_missing: /(?:工作压力|刻度盘).*红线|红线.*(?:未划|缺失)/,
  overload: /超负荷|过载|超过额定/,
  entry_elevator: /(?:电动自行车|蓄电池).*(?:进入|进入住宅).*(?:电梯|户内)/,
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
  if(defect==='entry_elevator'&&/物业|管理人|劝阻|制止/.test(heading))return false;
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
  return claims.some(claim=>claim.subjects.some(object=>fieldObjectMatches(row,object)
      ||(claim.defect==='inspection_overdue'&&object.key==='固定式压力容器'&&/^特种设备/.test(row.title||'')))
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
