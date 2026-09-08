import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const DIR = path.join(ROOT, 'content', 'batches');
const DATE = '2026-09-08';

const files = [
  '2026-09-08-batch-003a.json',
  '2026-09-08-batch-003b.json',
  '2026-09-08-batch-003c.json',
  '2026-09-08-batch-003d.json',
  '2026-09-08-batch-003e.json'
];

const batches = [];
for (const name of files) {
  const file = path.join(DIR, name);
  batches.push({ name, file, data: JSON.parse(await fs.readFile(file, 'utf8')) });
}

const lawSource = {
  L001: 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_e9e34f0731c249a891ea9c925e17f237.html',
  L002: 'https://www.mem.gov.cn/fw/flfgbz/fg/202107/t20210716_416558.shtml',
  L009: 'https://files.anshan.gov.cn/files/ueditor/ASJKQ/jsp/upload/file/20211201/1638343166465002256.pdf',
  L010: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=1C5996A8BAD63FF484CCFE024D98849C',
  L012: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4BB90BF6C7015DF7E4905694A80F7C57',
  L013: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/other/hjbhgc/201304/t20130403_250331.htm',
  L014: 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_ad5e293574484b48b45047ee0ede6099.html',
  L015: 'https://std.samr.gov.cn/hb/search/stdHBDetailedCNF?id=BDDBA08EC6856C70E05397BE0A0A640D',
  L016: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/other/hjbhgc/201012/t20101224_199112.htm',
  L017: 'https://std.samr.gov.cn/db/search/stdDBDetailed?id=E395E2E5CA792B21E05397BE0A0AFCB3',
  L018: 'https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/201102/t20110201_405595.shtml',
  L019: 'https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/202305/t20230523_451578.shtml',
  L020: 'https://www.jsrd.gov.cn/qwfb/sjfg/202304/t20230410_1221265.shtml',
  L021: 'https://zhc.dicp.ac.cn/info/1033/2831.htm',
  L022: 'https://openstd.samr.gov.cn/',
  L023: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/gtfwwrkzbz/202302/t20230224_1017500.shtml',
  L024: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BD4BA33D46B2AD5DCA3F1EBA7E99BEE6',
  L025: 'https://openstd.samr.gov.cn/',
  L026: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=76D3F954F575512DC1A4894370A8A84F',
  L027: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/other/hjbhgc/201212/t20121231_244484.htm',
  L028: 'https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/201606/t20160603_405633.shtml',
  L029: 'https://jst.sc.gov.cn/scjst/jsgcxfsyzxzzWsxx/2023/11/20/67491d2844b040cbb81324b61c2ceb99/files/%E3%80%8A%E5%BB%BA%E7%AD%91%E9%98%B2%E7%81%AB%E9%80%9A%E7%94%A8%E8%A7%84%E8%8C%83%E3%80%8B%E8%A7%A3%E8%AF%BB.pdf'
};

const lawPatch = {
  L012: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L012, effectiveDate:'2023-07-01' },
  L013: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L013, effectiveDate:'2013-07-01' },
  L014: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L014, effectiveDate:'2014-01-01' },
  L015: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L015, effectiveDate:'2014-11-13' },
  L016: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L016, effectiveDate:'2011-03-01' },
  L017: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L017, effectiveDate:'2022-08-02' },
  L018: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L018, effectiveDate:'2011-02-01' },
  L019: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L019, effectiveDate:'2023-05-15' },
  L020: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L020, effectiveDate:'2023-07-01' },
  L021: { name:'科研建筑设计标准 JGJ 91—2019', aliases:['JGJ 91-2019','JGJ91','科研建筑设计标准'], level:'行业标准（工程建设）', status:'现行有效', checked:DATE, sourceUrl:lawSource.L021, effectiveDate:'2020-01-01' },
  L022: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L022, effectiveDate:'2011-10-01' },
  L023: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L023, effectiveDate:'2023-07-01' },
  L024: { name:'易燃易爆性商品储存养护技术条件 GB 17914—2013', aliases:['GB 17914-2013','GB17914','易燃易爆性商品储存养护技术条件'], level:'强制性国家标准', status:'现行有效', checked:DATE, sourceUrl:lawSource.L024, effectiveDate:'2014-07-01' },
  L025: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L025 },
  L026: { name:'喷漆室安全技术要求 GB 14444—2025', aliases:['GB 14444-2025','GB14444','喷漆室安全技术要求'], level:'强制性国家标准', status:'现行有效', checked:DATE, sourceUrl:lawSource.L026, effectiveDate:'2026-08-01' },
  L027: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L027 },
  L028: { status:'现行有效', checked:DATE, sourceUrl:lawSource.L028, effectiveDate:'2019-09-01' }
};

const hazardDescriptions = {
  H033:'危险化学品储存设施未根据化学品危险特性、防火要求及化学品安全技术说明书规定进行选择。',
  H034:'主要负责人或安全生产管理人员不具备与本单位生产经营活动相应的安全生产知识和管理能力，或依法应考核合格的人员未按规定考核合格。',
  H035:'有机废气吸附治理系统与主体生产装置之间的管道系统未按规范设置阻火器（防火阀），或阻火器性能不符合要求。',
  H036:'特种设备使用单位未在检验合格有效期届满前按规定提出定期检验要求，或继续使用未经定期检验、检验不合格的特种设备。',
  H037:'室内储存场所设置员工宿舍，或甲、乙类物品室内储存场所设置办公室；其他室内储存场所确需设置办公室但防火条件不符合要求。',
  H038:'大气污染治理工程风机选型未与所处理介质特性相匹配，未按爆炸、易燃、腐蚀、高温或高含尘等工况选择相应型式。',
  H039:'有机废气吸附治理现场的风机、电机、电气仪表等防爆等级低于现场要求，或特定降压解吸回收工艺未采用符合要求的本安型防爆器件。',
  H040:'工贸企业特种作业人员未按规定经专门安全作业培训并取得相应资格即上岗作业。',
  H041:'危险化学品使用作业场所内设置了与生产无关的生活设施。',
  H042:'建设项目安全设施未由取得相应资质的施工单位施工，或未与主体工程同时施工。',
  H043:'仓储场所未开展消防法律法规、防火安全知识教育，或未按要求对员工开展消防安全培训。',
  H044:'仓储场所的消防通道、安全出口或消防车通道被占用、堵塞，未保持畅通。',
  H045:'生产经营单位未对重大危险源登记建档、定期检测评估监控、制定应急预案并告知应急措施，或未按规定报送有关重大危险源信息。',
  H046:'江苏省生产经营单位主要负责人未按规定每季度至少组织并参与一次安全生产全面检查。',
  H047:'江苏省生产经营单位主要负责人未按规定每年至少组织并参与一次生产安全事故应急救援演练。',
  H048:'江苏省生产经营单位主要负责人未按规定每年至少组织一次全面安全风险辨识并制定完善管控措施。',
  H049:'江苏省生产经营单位发生生产安全事故时，主要负责人未迅速组织抢救，或未按规定及时、如实报告事故并履行后续职责。',
  H050:'江苏省生产经营单位主要负责人未按规定每年向从业人员报告或通报安全生产工作及个人履职情况并接受监督。',
  H051:'生产、经营、储存、使用危险物品的车间、商店、仓库与员工宿舍设置在同一建筑内，或未保持安全距离；生产经营场所、员工宿舍出口或疏散通道设置、畅通情况不符合要求。',
  H052:'库房内物品与照明灯之间的距离小于0.5m。', H053:'库房内物品与墙之间的距离小于0.5m。', H054:'库房内物品堆垛与柱之间的距离小于0.3m。', H055:'库房内物品堆垛与堆垛之间的距离小于1m。',
  H056:'实验室气体管道系统存在渗漏，或耐压、耐温、耐腐蚀性能不符合要求；明露管道周围未留足清洁、维护和维修空间。',
  H057:'有大量灰尘场所的配电线路敷设未采取措施避免灰尘聚集影响布线散热。', H058:'仓储场所在岗人员消防安全教育频次不足，未达到至少每半年一次的要求。',
  H059:'仓储场所未按规定设置防雷与接地系统，或未按仓储场所消防管理要求开展周期性检测。',
  H060:'仓储场所消火栓缺少明显标志，室内消火栓箱上锁或箱内设备不齐全、不完好，或室外消火栓、水泵接合器周边存在影响正常使用的障碍物。',
  H061:'工贸企业未对承包单位、承租单位安全生产工作统一协调、管理，或未定期开展安全检查。', H062:'仓储场所防火检查频次不足，未达到场所每月至少一次、部门（班组）每周至少一次的要求。',
  H063:'科研建筑地下室或半地下室内储存甲、乙类危险物品。', H064:'危险废物产生、收集、贮存、利用或处置单位未按现行标准建造危险废物贮存设施或设置贮存场所。', H065:'易燃气体与助燃气体在同一库房储存。',
  H066:'消防车道或兼作消防车道的道路净宽、净空高度、转弯、承载、坡度或障碍物等通行条件不能满足消防车安全、快速通行和救援作业要求。',
  H067:'仓储场所未按要求组织或协助有关部门对消防安全责任人、消防安全管理人、消防控制室值班操作人员开展消防安全专门培训。', H068:'性质不相容的危险废物混合包装或在同一容器内混装，存在相互反应风险。',
  H069:'库房内堆垛上部与楼板、平屋顶之间的距离小于0.3m，或人字屋架条件下未从横梁起满足相应距离。', H070:'吸附有机气体后的吸附床温度不符合控制要求，或吸附装置超过83℃时不能自动报警并立即启动降温装置。',
  H071:'电气作业人员作业前未熟悉作业环境，未根据作业类型和性质采取相应防护措施，或使用的电工个体防护用品不合格、不适配。', H072:'电气特种作业人员未按规定取得相应特种作业资格即上岗，或电气作业使用的个体防护用品不合格、不适配。',
  H073:'在具有火灾、爆炸危险的场所吸烟、使用明火，或特殊情况需要明火作业时未按规定办理审批并落实消防安全措施。', H074:'从事电焊、气焊等具有火灾危险作业的人员未按规定持证上岗，或作业中未遵守消防安全操作规程。',
  H075:'危险化学品使用作业场所占用疏散通道，或设置影响逃生、灭火救援的障碍物。', H076:'喷漆室未设置安全通风装置或漆雾捕集装置。', H077:'使用强酸、强碱等存在化学品危险隐患的实验室未就近设置应急洗眼器及应急喷淋。',
  H078:'危险废物收集、贮存、运输单位未建立规范的管理和技术人员培训制度，或未按要求定期开展相关培训。', H079:'生产经营单位在建设项目初步设计阶段未委托有相应资质的设计单位同步开展安全设施设计并编制安全设施设计文件。',
  H080:'易发生火灾、爆炸、极低温或其他危险化学品事故的实验室与其他用房相邻时，未形成符合要求的独立防护单元，或耐火分隔、防火门窗、独立通风、泄压等措施不符合要求。', H081:'生产经营单位未制定生产安全事故应急救援预案，未与所在地县级以上地方人民政府相关预案衔接，或未定期组织演练。'
};

const hazardPatch = {
  H034:{ note:'《安全生产法》第二十七条对主要负责人和安全生产管理人员的知识、能力提出通用要求；危险物品生产、经营、储存、装卸及矿山、金属冶炼、建筑施工、运输单位的相关人员还需依法经主管部门考核合格，不应泛化为所有行业均须“取得资格证书”。' },
  H040:{ title:'工贸企业特种作业人员未按规定取得相应资格上岗', places:['工贸企业'], note:'在工贸企业中，本情形同时属于《工贸企业重大事故隐患判定标准》第三条第（二）项规定的重大事故隐患；一般生产经营单位还应遵守《安全生产法》第三十条。' },
  H049:{ title:'江苏生产经营单位事故发生后主要负责人未按要求组织抢救并报告', places:['江苏生产经营单位','工贸企业'], note:'本条按《江苏省安全生产条例》第十五条第（四）项核验，仅作为江苏范围直接依据；全国通用事故抢救、报告义务还应结合《安全生产法》等上位法判断。' },
  H059:{ note:'XF 1131—2014第8.11条要求仓储场所按GB 50057设置防雷与接地系统并每年检测一次，其中甲、乙类仓储场所防雷装置每半年检测一次。检测周期属于仓储消防管理要求，不应误写为GB 50057本身的条款。' },
  H061:{ title:'工贸企业承包、承租单位安全生产统一协调管理或定期检查不到位', places:['工贸企业'], note:'在工贸企业中，本情形同时属于《工贸企业重大事故隐患判定标准》第三条第（一）项规定的重大事故隐患；一般发包、出租场景还应遵守《安全生产法》第四十九条。' },
  H064:{ title:'危险废物未按要求设置贮存设施或场所', aliases:['危废无贮存设施','危废暂存场所不符合'], note:'已按GB 18597—2023现行文本重新定位至第4.1条，不再沿用旧版“所有产生者均建造专用贮存设施”的表述。设施/场所类型应根据危险废物类别、数量和环境风险选择。' },
  H066:{ title:'消防车道净宽、净空高度或通行条件不符合要求', aliases:['消防车道不足4m','消防车道净高不足','消防车道通行条件不符合'], note:'现行强制性工程建设规范GB 55037—2022第3.4.5条以“满足消防车安全、快速通行要求”为直接强制依据。GB 50016—2014（2018年版）7.1.8中的4.0m具体数值在适用时可作为技术核对依据，但不得脱离现行通用规范机械套用。' },
  H072:{ title:'电气作业个体防护或特种作业资格管理不到位', note:'个体防护要求按现行GB/T 13869—2017第9章核验；属于法定特种作业的电气作业人员资格要求同时执行《安全生产法》第三十条。GB/T 13869—2026将于2027-02-01实施，届时需重新核对条款。' },
  H076:{ note:'已按2026-08-01实施的现行强制性国家标准GB 14444—2025核验；GB 14444—2006已被全部代替，不再作为当前直接依据。' },
  H078:{ title:'危险废物收集、贮存、运输管理和技术人员培训制度不到位', aliases:['危废管理人员未培训','危险废物培训制度缺失'], note:'HJ 2025—2012第4.3条要求危险废物收集、贮存、运输单位建立管理和技术人员培训制度并定期培训；原候选“所有危险废物产生单位对本单位工作人员培训”的表述范围过宽，已纠正。' }
};

const clausePatch = {
  C032:{ lawId:'L012', article:'5.2', quote:'应选择符合危险化学品的特性、防火要求及化学品安全技术说明书中储存要求的仓储设施进行储存。' },
  C033:{ lawId:'L002', article:'第二十七条', quote:'生产经营单位的主要负责人和安全生产管理人员必须具备与本单位所从事的生产经营活动相应的安全生产知识和管理能力。' },
  C034:{ lawId:'L013', article:'6.5.2', quote:'治理系统与主体生产装置之间的管道系统应安装阻火器（防火阀），阻火器性能应符合GB 13347的规定。' },
  C035:{ lawId:'L014', article:'第四十条', quote:'特种设备使用单位应当按照安全技术规范的要求，在检验合格有效期届满前一个月向特种设备检验机构提出定期检验要求。未经定期检验或者检验不合格的特种设备，不得继续使用。' },
  C036:{ lawId:'L015', article:'6.3', quote:'室内储存场所不应设置员工宿舍。甲、乙类物品的室内储存场所内不应设办公室。其他室内储存场所确需设办公室时，其耐火等级应为一、二级，且门、窗应直通库外。' },
  C037:{ lawId:'L016', article:'5.4.1', quote:'风机应符合国家和行业相应产品标准，其选型应满足所处理介质的要求。输送有爆炸和易燃气体的应选防爆型风机；输送有腐蚀性气体的应选择防腐风机；在高温场合工作或输送高温气体的应选择高温风机；输送浓度较大的含尘气体应选用排尘风机等。' },
  C038:{ lawId:'L013', article:'6.5.3', quote:'风机、电机和置于现场的电气仪表等应不低于现场防爆等级。当吸附剂采用降压解吸方式再生且解吸后的高浓度有机气体采用液体吸收工艺进行回收时，风机、真空解吸泵和电气系统均应采用符合GB 3836.4要求的本安型防爆器件。' },
  C039:{ lawId:'L019', article:'第三条第（二）项', quote:'特种作业人员未按照规定经专门的安全作业培训并取得相应资格，上岗作业的。' }, C040:{ lawId:'L017', article:'8.3', quote:'危险化学品使用作业场所内不得设置与生产无关的生活设施等。' }, C041:{ lawId:'L018', article:'第十七条', quote:'建设项目安全设施的施工应当由取得相应资质的施工单位进行，并与建设项目主体工程同时施工。' },
  C042:{ lawId:'L015', article:'4.1', quote:'开展消防法律法规和防火安全知识的教育，对员工进行消防安全培训。' }, C043:{ lawId:'L015', article:'4.1', quote:'保障仓储场所消防通道、安全出口和消防车通道畅通。' }, C044:{ lawId:'L002', article:'第四十条', quote:'生产经营单位对重大危险源应当登记建档，进行定期检测、评估、监控，并制定应急预案，告知从业人员和相关人员在紧急情况下应当采取的应急措施。生产经营单位应当按照国家有关规定将本单位重大危险源及有关安全措施、应急措施报有关地方人民政府应急管理部门和有关部门备案。' },
  C045:{ lawId:'L020', article:'第十五条第（一）项', quote:'每季度至少组织并参与一次安全生产全面检查，研究分析和解决安全生产存在问题。' }, C046:{ lawId:'L020', article:'第十五条第（二）项', quote:'每年至少组织并参与一次生产安全事故应急救援演练。' }, C047:{ lawId:'L020', article:'第十五条第（三）项', quote:'每年至少组织一次全面的安全风险辨识，制定完善管控措施。' }, C048:{ lawId:'L020', article:'第十五条第（四）项', quote:'发生生产安全事故时迅速组织抢救，并按照规定及时、如实向负有安全生产监督管理职责的部门报告事故情况，做好善后处理工作，配合调查处理。' }, C049:{ lawId:'L020', article:'第十五条第（五）项', quote:'每年通过职工大会或者职工代表大会、信息公示栏等，向从业人员报告或者通报安全生产工作以及个人履行安全生产职责的情况，接受从业人员监督。' },
  C050:{ lawId:'L002', article:'第四十二条', quote:'生产、经营、储存、使用危险物品的车间、商店、仓库不得与员工宿舍在同一座建筑物内，并应当与员工宿舍保持安全距离。生产经营场所和员工宿舍应当设有符合紧急疏散要求、标志明显、保持畅通的出口、疏散通道。禁止占用、锁闭、封堵生产经营场所或者员工宿舍的出口、疏散通道。' },
  C051:{ lawId:'L015', article:'6.8第b项', quote:'物品与照明灯之间的距离不小于0.5m。' }, C052:{ lawId:'L015', article:'6.8第c项', quote:'物品与墙之间的距离不小于0.5m。' }, C053:{ lawId:'L015', article:'6.8第d项', quote:'物品堆垛与柱之间的距离不小于0.3m。' }, C054:{ lawId:'L015', article:'6.8第e项', quote:'物品堆垛与堆垛之间的距离不小于1m。' },
  C055:{ lawId:'L021', article:'10.2.5', quote:'气体管道系统应不渗漏、耐压、耐温、耐腐蚀。实验室内应有足够的清洁、维护和维修明露管道的空间。' }, C056:{ lawId:'L009', article:'7.1.2第4项', quote:'在有大量灰尘的场所，应避免由于灰尘聚集在布线上对散热带来的影响。' }, C057:{ lawId:'L015', article:'3.3.2', quote:'仓储场所在员工上岗、转岗前，应对其进行消防安全培训；对在岗人员至少每半年应进行一次消防安全教育。' }, C058:{ lawId:'L015', article:'8.11', quote:'仓储场所应按照GB 50057设置防雷与接地系统，并应每年检测一次，其中甲、乙类仓储场所的防雷装置应每半年检测一次，并应取得专业部门测试合格证书。' }, C059:{ lawId:'L015', article:'10.7', quote:'仓储场所设置的消火栓应有明显标志。室内消火栓箱不应上锁，箱内设备应齐全、完好。距室外消火栓、水泵接合器2m范围内不应设置影响其正常使用的障碍物。' },
  C060:{ lawId:'L019', article:'第三条第（一）项', quote:'未对承包单位、承租单位的安全生产工作统一协调、管理，或者未定期进行安全检查的。' }, C061:{ lawId:'L015', article:'5.1.1', quote:'仓储场所每月应至少组织一次防火检查，各部门（班组）每周应至少开展一次防火检查。' }, C062:{ lawId:'L021', article:'5.2.4', quote:'甲、乙类危险物品不应储存在科研建筑的地下室和半地下室内。' }, C063:{ lawId:'L023', article:'4.1', quote:'产生、收集、贮存、利用、处置危险废物的单位应建造危险废物贮存设施或设置贮存场所，并根据需要选择贮存设施类型。' }, C064:{ lawId:'L024', article:'4.2.2.5', quote:'易燃气体不应与助燃气体同库储存。' },
  C065:{ lawId:'L029', article:'3.4.5', quote:'消防车道或兼作消防车道的道路应符合下列规定：道路的净宽度和净空高度应满足消防车安全、快速通行的要求；转弯半径应满足消防车转弯的要求；路面及其下面的建筑结构、管道、管沟等，应满足承受消防车满载时压力的要求；坡度应满足消防车满载时正常通行的要求，且不应大于10%。' }, C066:{ lawId:'L015', article:'3.3.1', quote:'仓储场所应组织或者协助有关部门对消防安全责任人、消防安全管理人、消防控制室的值班操作人员进行消防安全专门培训。' }, C067:{ lawId:'L027', article:'5.6第（2）项', quote:'性质类似的废物可收集到同一容器中，性质不相容的危险废物不应混合包装。' }, C068:{ lawId:'L015', article:'6.8第a项', quote:'堆垛上部与楼板、平屋顶之间的距离不小于0.3m（人字屋架从横梁算起）。' }, C069:{ lawId:'L013', article:'6.5.4', quote:'在吸附操作周期内，吸附了有机气体后吸附床内的温度应低于83℃。当吸附装置内的温度超过83℃时，应能自动报警，并立即启动降温装置。' },
  C070:{ lawId:'L010', article:'9（对人员的要求）', quote:'电气作业人员在进行电气作业前应熟悉作业环境，并根据作业的类型和性质采取相应的防护措施；进行电气作业时，所使用的电工个体防护用品应保证合格并与作业活动相适应。' }, C071:{ lawId:'L010', article:'9（对人员的要求）', quote:'进行电气作业时，所使用的电工个体防护用品应保证合格并与作业活动相适应。' },
  C072:{ lawId:'L001', article:'第二十一条', quote:'禁止在具有火灾、爆炸危险的场所吸烟、使用明火。因施工等特殊情况需要使用明火作业的，应当按照规定事先办理审批手续，采取相应的消防安全措施；作业人员应当遵守消防安全规定。' }, C073:{ lawId:'L001', article:'第二十一条', quote:'进行电焊、气焊等具有火灾危险作业的人员和自动消防系统的操作人员，必须持证上岗，并遵守消防安全操作规程。' }, C074:{ lawId:'L017', article:'8.2', quote:'危险化学品使用作业场所应保持整洁有序，不得占用疏散通道，不得设置影响逃生和灭火救援的障碍物。' }, C075:{ lawId:'L026', article:'4.2', quote:'喷漆室应设置安全通风装置和漆雾捕集装置。' }, C076:{ lawId:'L021', article:'5.3.3', quote:'使用强酸、强碱等有化学品危险隐患的实验室，应就近设置应急洗眼器及应急喷淋。' }, C077:{ lawId:'L027', article:'4.3', quote:'危险废物收集、贮存、运输单位应建立规范的管理和技术人员培训制度，定期针对管理和技术人员进行培训。' }, C078:{ lawId:'L018', article:'第十条', quote:'生产经营单位在建设项目初步设计时，应当委托有相应资质的设计单位对建设项目安全设施同时进行设计，编制安全设施设计。' }, C079:{ lawId:'L021', article:'5.2.5', quote:'当易发生火灾、爆炸、极低温和其他危险化学品引发事故的实验室与其他用房相邻时，必须形成独立的防护单元。防护单元的围护结构应采用耐火极限不低于1.5h的楼板和耐火极限不低于2.0h的隔墙与其他用房分隔；门、窗应采用甲级防火门、窗；易发生火灾、爆炸或缺氧危险的实验室应设置独立的通风系统；有爆炸危险的实验室应设置泄压设施。' }, C080:{ lawId:'L002', article:'第八十一条', quote:'生产经营单位应当制定本单位生产安全事故应急救援预案，与所在地县级以上地方人民政府组织制定的生产安全事故应急救援预案相衔接，并定期组织演练。' }
};

const extraClauses = [
  { id:'C081', lawId:'L002', article:'第三十条', quote:'生产经营单位的特种作业人员必须按照国家有关规定经专门的安全作业培训，取得相应资格，方可上岗作业。', checked:DATE, status:'已核验', sourceUrl:lawSource.L002 },
  { id:'C082', lawId:'L002', article:'第四十九条', quote:'生产经营项目、场所发包或者出租给其他单位的，生产经营单位应当与承包单位、承租单位签订专门的安全生产管理协议，或者在承包合同、租赁合同中约定各自的安全生产管理职责；生产经营单位对承包单位、承租单位的安全生产工作统一协调、管理，定期进行安全检查，发现安全问题的，应当及时督促整改。', checked:DATE, status:'已核验', sourceUrl:lawSource.L002 }
];
const extraLaw = { id:'L029', name:'建筑防火通用规范 GB 55037—2022', aliases:['GB 55037-2022','GB55037','建筑防火通用规范'], level:'强制性工程建设规范', scope:'全国', status:'现行有效', checked:DATE, sourceUrl:lawSource.L029, effectiveDate:'2023-06-01', replaces:[], replacedBy:[] };

const allHazards = batches.flatMap(b => b.data.hazards ?? []); const allLaws = batches.flatMap(b => b.data.laws ?? []); const allClauses = batches.flatMap(b => b.data.clauses ?? []); const allLinks = batches.flatMap(b => b.data.links ?? []);
for (const h of allHazards) { if (!/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(h.id)) continue; if (!hazardDescriptions[h.id]) throw new Error(`Missing description patch for ${h.id}`); h.description=hazardDescriptions[h.id]; h.status='已核验'; h.checked=DATE; h.note='已于2026-09-08按现行法规、标准及官方标准状态信息复核。现场定性仍需结合适用范围、场所条件、行业属性及标准版本判断。'; if (hazardPatch[h.id]) Object.assign(h,hazardPatch[h.id]); }
for (const law of allLaws) if (lawPatch[law.id]) Object.assign(law,lawPatch[law.id]); if (!allLaws.some(x=>x.id===extraLaw.id)) batches[0].data.laws.push(extraLaw);
for (const clause of allClauses) { const p=clausePatch[clause.id]; if (!p) continue; Object.assign(clause,p); clause.checked=DATE; clause.status='已核验'; clause.sourceUrl=lawSource[clause.lawId] ?? clause.sourceUrl; }
for (const clause of extraClauses) if (!batches.some(b=>(b.data.clauses??[]).some(x=>x.id===clause.id))) batches.at(-1).data.clauses.push(clause);
for (const link of allLinks) { if (/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(link.hazardId)) { if (link.hazardId==='H040'&&link.clauseId==='C039') { link.role='工贸重大事故隐患判定依据'; link.priority=10; } else if (link.hazardId==='H061'&&link.clauseId==='C060') { link.role='工贸重大事故隐患判定依据'; link.priority=10; } else { link.role='直接依据'; link.priority=10; } } }
const ensureLink=link=>{ if (!batches.some(b=>(b.data.links??[]).some(x=>x.hazardId===link.hazardId&&x.clauseId===link.clauseId))) batches.at(-1).data.links.push(link); };
ensureLink({hazardId:'H040',clauseId:'C081',role:'上位法通用依据',priority:20}); ensureLink({hazardId:'H061',clauseId:'C082',role:'上位法通用依据',priority:20}); ensureLink({hazardId:'H072',clauseId:'C081',role:'特种作业资格法律依据',priority:20});
const verifiedIds=new Set(allHazards.filter(h=>/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(h.id)).map(h=>h.id)); if (verifiedIds.size!==49) throw new Error(`Expected 49 Batch 003 hazards, got ${verifiedIds.size}`); for (const id of verifiedIds) { const h=allHazards.find(x=>x.id===id); if(h.status!=='已核验'||h.checked!==DATE) throw new Error(`Hazard not finalized: ${id}`); } for (const id of Object.keys(clausePatch)) { const c=allClauses.find(x=>x.id===id); if(!c||c.status!=='已核验'||!c.quote||!c.sourceUrl) throw new Error(`Clause not finalized: ${id}`); }
for (const batch of batches) await fs.writeFile(batch.file,JSON.stringify(batch.data,null,2)+'\n','utf8');
console.log(`Finalized ${verifiedIds.size} Batch 003 hazards and ${Object.keys(clausePatch).length+extraClauses.length} clauses.`);
