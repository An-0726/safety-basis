import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const BATCH_DIR = path.join(ROOT, 'content', 'batches');
const CHECKED = '2026-09-08';

const targetFiles = [
  '2026-09-08-batch-003a.json',
  '2026-09-08-batch-003b.json',
  '2026-09-08-batch-003c.json',
  '2026-09-08-batch-003d.json',
  '2026-09-08-batch-003e.json'
];

const SOURCES = {
  safetyLaw: 'https://www.mem.gov.cn/fw/flfgbz/fg/202107/t20210716_416558.shtml',
  fireLaw: 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_e9e34f0731c249a891ea9c925e17f237.html',
  specialEquipment: 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_ad5e293574484b48b45047ee0ede6099.html',
  gb15603: 'https://openstd.samr.gov.cn/',
  hj2026: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/other/hjbhgc/201304/t20130403_250331.htm',
  hj2000: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/other/hjbhgc/201012/t20101224_199112.htm',
  db324293: 'https://std.samr.gov.cn/db/search/stdDBDetailed?id=E395E2E5CA792B21E05397BE0A0AFCB3',
  threeSimultaneous: 'https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/201102/t20110201_405595.shtml',
  majorHazard: 'https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/202305/t20230523_451578.shtml',
  jiangsuSafety: 'https://www.jsrd.gov.cn/qwfb/sjfg/202304/t20230410_1221265.shtml',
  jgj91: 'https://www.zhc.dicp.ac.cn/info/1033/2831.htm',
  gb50057: 'https://openstd.samr.gov.cn/',
  gb18597: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/gtfwwrkzbz/202302/t20230224_1017500.shtml',
  gb17914: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BD4BA33D46B2AD5DCA3F1EBA7E99BEE6',
  gb50016: 'https://js.119.gov.cn/202111/715323810e37465891fc6a5f66b9589d_c_3d35986ea8ea4ce781db.html',
  gb14444: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=76D3F954F575512DC1A4894370A8A84F',
  hj2025: 'https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/other/hjbhgc/201212/t20121231_244484.htm',
  emergencyPlan: 'https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/201606/t20160603_405633.shtml',
  xf1131: 'https://js.119.gov.cn/202111/206aebe848d24575894f22639ff3e721_c_f81c74d68ace4f1db1c5.html',
  gb55037: 'https://js.119.gov.cn/group1/M00/01/D6/rBPe7Wi5YSWATAAkABU9IFBisPA109.pdf',
  gb50054: 'https://files.anshan.gov.cn/files/ueditor/ASJKQ/jsp/upload/file/20211201/1638343166465002256.pdf',
  gbt13869: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=1C5996A8BAD63FF484CCFE024D98849C'
};

const lawPatch = {
  L016: {name:'大气污染治理工程技术导则 HJ 2000—2010',aliases:['HJ 2000-2010','HJ2000','大气污染治理工程技术导则'],level:'行业标准',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.hj2000,effectiveDate:'2011-03-01',replaces:[],replacedBy:[]},
  L017: {name:'工业企业危险化学品安全管理指南 DB32/T 4293—2022',aliases:['DB32/T 4293-2022','DB32T4293','工业企业危险化学品安全管理指南'],level:'地方标准',scope:'江苏／南京',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.db324293,effectiveDate:'2022-08-02',replaces:[],replacedBy:[]},
  L018: {name:'建设项目安全设施“三同时”监督管理办法',aliases:['安全设施三同时监督管理办法','建设项目安全设施三同时'],level:'部门规章',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.threeSimultaneous,effectiveDate:'2011-02-01',replaces:[],replacedBy:[]},
  L019: {name:'工贸企业重大事故隐患判定标准（应急管理部令第10号）',aliases:['应急管理部令第10号','工贸企业重大事故隐患判定标准','工贸重大事故隐患判定标准'],level:'部门规章',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.majorHazard,effectiveDate:'2023-05-15',replaces:[],replacedBy:[]},
  L020: {name:'江苏省安全生产条例（2023修订）',aliases:['江苏省安全生产条例'],level:'地方性法规',scope:'江苏／南京',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.jiangsuSafety,effectiveDate:'2023-07-01',replaces:[],replacedBy:[]},
  L021: {name:'科研建筑设计标准 JGJ 91—2019',aliases:['JGJ 91-2019','JGJ91-2019','科研建筑设计标准'],level:'行业标准',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.jgj91,effectiveDate:'2020-01-01',replaces:[],replacedBy:[]},
  L024: {name:'易燃易爆性商品储存养护技术条件 GB 17914—2013',aliases:['GB 17914-2013','GB17914','易燃易爆性商品储存养护技术条件'],level:'强制性国家标准',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.gb17914,effectiveDate:'2014-07-01',replaces:[],replacedBy:[]},
  L026: {name:'喷漆室安全技术要求 GB 14444—2025',aliases:['GB 14444-2025','GB14444-2025','喷漆室安全技术要求'],level:'强制性国家标准',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.gb14444,effectiveDate:'2026-08-01',replaces:[],replacedBy:[]},
  L028: {name:'生产安全事故应急预案管理办法（应急管理部令第2号修正）',aliases:['生产安全事故应急预案管理办法','应急预案管理办法','应急管理部令第2号'],level:'部门规章',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.emergencyPlan,effectiveDate:'2016-07-01',replaces:[],replacedBy:[]}
};

const newLaw = {id:'L029',name:'建筑防火通用规范 GB 55037—2022',aliases:['GB 55037-2022','GB55037','建筑防火通用规范'],level:'强制性国家标准',scope:'全国',status:'现行有效',checked:CHECKED,sourceUrl:SOURCES.gb55037,effectiveDate:'2023-06-01',replaces:[],replacedBy:[]};

const clausePatch = {
  C032:{lawId:'L012',article:'5.2',quote:'应选择符合危险化学品的特性、防火要求及化学品安全技术说明书中储存要求的仓储设施进行储存。',sourceUrl:SOURCES.gb15603},
  C033:{lawId:'L002',article:'第二十七条',quote:'生产经营单位的主要负责人和安全生产管理人员必须具备与本单位所从事的生产经营活动相应的安全生产知识和管理能力。',sourceUrl:SOURCES.safetyLaw},
  C034:{lawId:'L013',article:'6.5.2',quote:'治理系统与主体生产装置之间的管道系统应安装阻火器（防火阀），阻火器性能应符合GB 13347的规定。',sourceUrl:SOURCES.hj2026},
  C035:{lawId:'L014',article:'第四十条',quote:'特种设备使用单位应当按照安全技术规范的要求，在检验合格有效期届满前一个月向特种设备检验机构提出定期检验要求。特种设备检验机构接到定期检验要求后，应当按照安全技术规范的要求及时进行安全性能检验。特种设备使用单位应当将定期检验标志置于该特种设备的显著位置。未经定期检验或者检验不合格的特种设备，不得继续使用。',sourceUrl:SOURCES.specialEquipment},
  C036:{lawId:'L015',article:'6.3',quote:'室内储存场所不应设置员工宿舍。甲、乙类物品的室内储存场所内不应设办公室。其他室内储存场所确需设办公室时，其耐火等级应为一、二级，且门、窗应直通库外。',sourceUrl:SOURCES.xf1131},
  C037:{lawId:'L016',article:'5.4.1',quote:'风机应符合国家和行业相应产品标准，其选型应满足所处理介质的要求。输送有爆炸和易燃气体的应选防爆型风机。当离心通风机布置在非爆炸环境场所时，宜选择风机叶轮防爆而风机电机不防爆的防爆风机；输送煤粉的应选择煤粉风机；输送有腐蚀性气体的应选择防腐风机；在高温场合工作或输送高温气体的应选择高温风机；输送浓度较大的含尘气体应选用排尘风机等。',sourceUrl:SOURCES.hj2000},
  C038:{lawId:'L013',article:'6.5.3',quote:'风机、电机和置于现场的电气仪表等应不低于现场防爆等级。当吸附剂采用降压解吸方式再生且解吸后的高浓度有机气体采用液体吸收工艺进行回收时，风机、真空解吸泵和电气系统均应采用符合GB 3836.4要求的本安型防爆器件。',sourceUrl:SOURCES.hj2026},
  C039:{lawId:'L002',article:'第三十条',quote:'生产经营单位的特种作业人员必须按照国家有关规定经专门的安全作业培训，取得相应资格，方可上岗作业。',sourceUrl:SOURCES.safetyLaw},
  C040:{lawId:'L017',article:'8.3',quote:'危险化学品使用作业场所内不得设置与生产无关的生活设施等。',sourceUrl:SOURCES.db324293},
  C041:{lawId:'L018',article:'第十七条',quote:'建设项目安全设施的施工应当由取得相应资质的施工单位进行，并与建设项目主体工程同时施工。',sourceUrl:SOURCES.threeSimultaneous},
  C042:{lawId:'L015',article:'4.1',quote:'开展消防法律法规和防火安全知识的教育，对员工进行消防安全培训。',sourceUrl:SOURCES.xf1131},
  C043:{lawId:'L001',article:'第二十八条',quote:'不得占用、堵塞、封闭疏散通道、安全出口、消防车通道。',sourceUrl:SOURCES.fireLaw},
  C044:{lawId:'L002',article:'第四十条',quote:'生产经营单位对重大危险源应当登记建档，进行定期检测、评估、监控，并制定应急预案，告知从业人员和相关人员在紧急情况下应当采取的应急措施。',sourceUrl:SOURCES.safetyLaw},
  C045:{lawId:'L020',article:'第十五条第（一）项',quote:'每季度至少组织并参与一次安全生产全面检查，研究分析和解决安全生产存在问题。',sourceUrl:SOURCES.jiangsuSafety},
  C046:{lawId:'L020',article:'第十五条第（二）项',quote:'每年至少组织并参与一次生产安全事故应急救援演练。',sourceUrl:SOURCES.jiangsuSafety},
  C047:{lawId:'L020',article:'第十五条第（三）项',quote:'每年至少组织一次全面的安全风险辨识，制定完善管控措施。',sourceUrl:SOURCES.jiangsuSafety},
  C048:{lawId:'L002',article:'第八十三条',quote:'单位负责人接到事故报告后，应当迅速采取有效措施，组织抢救，防止事故扩大，减少人员伤亡和财产损失，并按照国家有关规定立即如实报告当地负有安全生产监督管理职责的部门。',sourceUrl:SOURCES.safetyLaw},
  C049:{lawId:'L020',article:'第十五条第（五）项',quote:'每年通过职工大会或者职工代表大会、信息公示栏等，向从业人员报告或者通报安全生产工作以及个人履行安全生产职责的情况，接受从业人员监督。',sourceUrl:SOURCES.jiangsuSafety},
  C050:{lawId:'L002',article:'第四十二条',quote:'生产、经营、储存、使用危险物品的车间、商店、仓库不得与员工宿舍在同一座建筑物内，并应当与员工宿舍保持安全距离。生产经营场所和员工宿舍应当设有符合紧急疏散要求、标志明显、保持畅通的出口、疏散通道。',sourceUrl:SOURCES.safetyLaw},
  C051:{lawId:'L015',article:'6.8 b)',quote:'物品与照明灯之间的距离不小于0.5m。',sourceUrl:SOURCES.xf1131},
  C052:{lawId:'L015',article:'6.8 c)',quote:'物品与墙之间的距离不小于0.5m。',sourceUrl:SOURCES.xf1131},
  C053:{lawId:'L015',article:'6.8 d)',quote:'物品堆垛与柱之间的距离不小于0.3m。',sourceUrl:SOURCES.xf1131},
  C054:{lawId:'L015',article:'6.8 e)',quote:'物品堆垛与堆垛之间的距离不小于1m。',sourceUrl:SOURCES.xf1131},
  C055:{lawId:'L021',article:'10.2.5',quote:'气体管道系统应不渗漏、耐压、耐温、耐腐蚀。实验室内应有足够的清洁、维护和维修明露管道的空间。',sourceUrl:SOURCES.jgj91},
  C056:{lawId:'L009',article:'7.1.2',quote:'配电线路的敷设，应避免下列外部环境的影响：在有大量灰尘的场所，应避免由于灰尘聚集在布线上所带来的影响。',sourceUrl:SOURCES.gb50054},
  C057:{lawId:'L015',article:'3.3.2',quote:'仓储场所在员工上岗、转岗前，应对其进行消防安全培训；对在岗人员至少每半年应进行一次消防安全教育。',sourceUrl:SOURCES.xf1131},
  C058:{lawId:'L015',article:'8.11',quote:'仓储场所应按照GB 50057设置防雷与接地系统，并应每年检测一次，其中甲、乙类仓储场所的防雷装置应每半年检测一次，并应取得专业部门测试合格证书。',sourceUrl:SOURCES.xf1131},
  C059:{lawId:'L015',article:'10.7',quote:'仓储场所设置的消火栓应有明显标志。室内消火栓箱不应上锁，箱内设备应齐全、完好。距室外消火栓、水泵接合器2m范围内不应设置影响其正常使用的障碍物。',sourceUrl:SOURCES.xf1131},
  C060:{lawId:'L002',article:'第四十九条',quote:'生产经营单位对承包单位、承租单位的安全生产工作统一协调、管理，定期进行安全检查，发现安全问题的，应当及时督促整改。',sourceUrl:SOURCES.safetyLaw},
  C061:{lawId:'L015',article:'5.1.1',quote:'仓储场所每月应至少组织一次防火检查，各部门（班组）每周应至少开展一次防火检查。',sourceUrl:SOURCES.xf1131},
  C062:{lawId:'L021',article:'5.2.4',quote:'甲、乙类危险物品不应储存在科研建筑的地下室和半地下室内。',sourceUrl:SOURCES.jgj91},
  C063:{lawId:'L023',article:'4.1',quote:'产生、收集、贮存、利用、处置危险废物的单位应建造危险废物贮存设施或设置贮存场所，并根据需要选择贮存设施类型。',sourceUrl:SOURCES.gb18597},
  C064:{lawId:'L024',article:'4.2.2.5',quote:'易燃气体不应与助燃气体同库储存。',sourceUrl:SOURCES.gb17914},
  C065:{lawId:'L029',article:'3.4.5第1项',quote:'道路的净宽度和净空高度应满足消防车安全、快速通行的要求。',sourceUrl:SOURCES.gb55037},
  C066:{lawId:'L015',article:'3.3.1',quote:'仓储场所应组织或者协助有关部门对消防安全责任人、消防安全管理人、消防控制室的值班操作人员进行消防安全专门培训。',sourceUrl:SOURCES.xf1131},
  C067:{lawId:'L023',article:'6.1.2',quote:'贮存设施应根据危险废物的类别、数量、形态、物理化学性质和污染防治等要求设置必要的贮存分区，避免不相容的危险废物接触、混合。',sourceUrl:SOURCES.gb18597},
  C068:{lawId:'L015',article:'6.8 a)',quote:'堆垛上部与楼板、平屋顶之间的距离不小于0.3m（人字屋架从横梁算起）。',sourceUrl:SOURCES.xf1131},
  C069:{lawId:'L013',article:'6.5.4',quote:'在吸附操作周期内，吸附了有机气体后吸附床内的温度应低于83℃。当吸附装置内的温度超过83℃时，应能自动报警，并立即启动降温装置。',sourceUrl:SOURCES.hj2026},
  C070:{lawId:'L010',article:'第9条',quote:'电气作业人员在进行电气作业前应熟悉作业环境，并根据作业的类型和性质采取相应的防护措施。',sourceUrl:SOURCES.gbt13869},
  C071:{lawId:'L010',article:'第9条',quote:'进行电气作业时，所使用的电工个体防护用品应保证合格并与作业活动相适应。从事电气作业中的特种作业人员应经专门的安全作业培训，在取得相应特种作业操作资格证书后，方可上岗。',sourceUrl:SOURCES.gbt13869},
  C072:{lawId:'L001',article:'第二十一条',quote:'禁止在具有火灾、爆炸危险的场所吸烟、使用明火。因施工等特殊情况需要使用明火作业的，应当按照规定事先办理审批手续，采取相应的消防安全措施。',sourceUrl:SOURCES.fireLaw},
  C073:{lawId:'L001',article:'第二十一条',quote:'进行电焊、气焊等具有火灾危险作业的人员和自动消防系统的操作人员，必须持证上岗，并遵守消防安全操作规程。',sourceUrl:SOURCES.fireLaw},
  C074:{lawId:'L017',article:'8.2',quote:'危险化学品使用作业场所应保持整洁有序，不得占用疏散通道，不得设置影响逃生和灭火救援的障碍物。',sourceUrl:SOURCES.db324293},
  C075:{lawId:'L026',article:'5.3.1',quote:'喷漆区的通风量应确保可燃气体浓度不大于其爆炸下限的25%。',sourceUrl:SOURCES.gb14444},
  C076:{lawId:'L021',article:'5.3.3',quote:'使用强酸、强碱等有化学品危险隐患的实验室，应就近设置应急洗眼器及应急喷淋。',sourceUrl:SOURCES.jgj91},
  C077:{lawId:'L027',article:'4.3',quote:'危险废物产生单位应当对本单位工作人员进行培训。',sourceUrl:SOURCES.hj2025},
  C078:{lawId:'L018',article:'第十条',quote:'生产经营单位在建设项目初步设计时，应当委托有相应资质的设计单位对建设项目安全设施同时进行设计，编制安全设施设计。',sourceUrl:SOURCES.threeSimultaneous},
  C079:{lawId:'L021',article:'5.2.5',quote:'当易发生火灾、爆炸、极低温和其他危险化学品引发事故的实验室与其他用房相邻时，必须形成独立的防护单元，并应符合下列规定：1 防护单元的围护结构，应采用耐火极限不低于1.5h的楼板和耐火极限不低于2.0h的隔墙与其他用房分隔。2 门、窗应采用甲级防火门、窗，并应有防盗功能。3 易发生火灾、爆炸或缺氧危险的实验室应设置独立的通风系统。4 有爆炸危险的实验室应设置泄压设施。',sourceUrl:SOURCES.jgj91},
  C080:{lawId:'L002',article:'第八十一条',quote:'生产经营单位应当制定本单位生产安全事故应急救援预案，与所在地县级以上地方人民政府组织制定的生产安全事故应急救援预案相衔接，并定期组织演练。',sourceUrl:SOURCES.safetyLaw}
};

const hazardPatch = {
  H033:{description:'危险化学品未根据其危险特性、防火要求及化学品安全技术说明书中的储存要求，选择符合条件的仓储设施进行储存。',mode:'直接适用'},
  H034:{description:'生产经营单位主要负责人或安全生产管理人员不具备与本单位生产经营活动相应的安全生产知识和管理能力；依法应接受主管部门考核的单位，其相关人员未按规定考核合格。',mode:'条件适用',note:'《安全生产法》并未要求所有行业主要负责人和安全生产管理人员一律“培训取证”。一般单位适用知识和管理能力要求；危险物品生产、经营、储存、装卸以及矿山、金属冶炼、建筑施工、运输单位还应依法考核合格。'},
  H035:{description:'适用HJ 2026—2013的吸附法工业有机废气治理工程中，治理系统与主体生产装置之间的管道系统未按要求安装阻火器（防火阀），或阻火器性能不符合要求。',mode:'条件适用'},
  H036:{description:'特种设备使用单位未按安全技术规范要求在检验合格有效期届满前一个月提出定期检验要求，或未经定期检验、检验不合格仍继续使用。',mode:'直接适用'},
  H037:{description:'室内储存场所设置员工宿舍；甲、乙类物品室内储存场所设置办公室；其他室内储存场所确需设置办公室但耐火等级、门窗直通库外等条件不符合要求。',mode:'直接适用'},
  H038:{description:'大气污染治理工程风机选型未与所处理介质相匹配，例如输送易燃易爆气体未选用适用的防爆型风机，或腐蚀性、高温、含尘介质未选用相应风机。',mode:'条件适用'},
  H039:{description:'适用HJ 2026—2013的吸附法有机废气治理工程中，风机、电机及现场电气仪表等防爆等级低于现场要求，或特定降压解吸回收工艺的相关设备未按规定采用本安型防爆器件。',mode:'条件适用'},
  H040:{description:'属于法定特种作业范围的人员，未按国家有关规定接受专门安全作业培训并取得相应资格即上岗作业。',mode:'直接适用'},
  H041:{description:'江苏省工业企业危险化学品使用作业场所内设置与生产无关的生活设施。',mode:'条件适用'},
  H042:{description:'建设项目安全设施未由取得相应资质的施工单位施工，或未与主体工程同时施工。',mode:'直接适用'},
  H043:{description:'仓储场所未结合消防法律法规、防火安全知识和岗位风险对员工开展消防安全教育培训。',mode:'条件适用'},
  H044:{description:'疏散通道、安全出口或消防车通道被占用、堵塞、封闭，影响人员疏散或消防救援通行。',mode:'直接适用'},
  H045:{description:'经辨识构成重大危险源的，生产经营单位未按规定登记建档、定期检测评估监控、制定应急预案并告知紧急情况下的应急措施，或未按规定备案有关安全和应急措施。',mode:'条件适用'},
  H046:{description:'江苏省生产经营单位主要负责人未做到每季度至少组织并参与一次安全生产全面检查，研究分析和解决安全生产存在问题。',mode:'直接适用'},
  H047:{description:'江苏省生产经营单位主要负责人未做到每年至少组织并参与一次生产安全事故应急救援演练。',mode:'直接适用'},
  H048:{description:'江苏省生产经营单位主要负责人未做到每年至少组织一次全面的安全风险辨识并制定完善管控措施。',mode:'直接适用'},
  H049:{description:'生产安全事故发生后，单位负责人接到报告后未迅速采取有效措施组织抢救，或未按国家有关规定立即、如实报告当地负有安全生产监督管理职责的部门。',mode:'直接适用'},
  H050:{description:'江苏省生产经营单位主要负责人未按规定每年向从业人员报告或通报安全生产工作及个人履行安全生产职责情况并接受监督。',mode:'直接适用'},
  H051:{description:'生产、经营、储存、使用危险物品的车间、商店、仓库与员工宿舍设置在同一建筑物内，或未保持安全距离；生产经营场所或员工宿舍的出口、疏散通道设置或畅通条件不符合要求。',mode:'直接适用'},
  H052:{description:'库房内物品与照明灯之间的距离小于0.5m。',mode:'直接适用'},
  H053:{description:'库房内物品与墙之间的距离小于0.5m。',mode:'直接适用'},
  H054:{description:'库房内物品堆垛与柱之间的距离小于0.3m。',mode:'直接适用'},
  H055:{description:'库房内物品堆垛与堆垛之间的距离小于1m。',mode:'直接适用'},
  H056:{description:'科研建筑实验室气体管道系统存在渗漏，或耐压、耐温、耐腐蚀性能不符合要求；实验室内未为明露管道保留足够的清洁、维护和维修空间。',mode:'直接适用'},
  H057:{description:'在有大量灰尘的场所，配电线路敷设未避免灰尘聚集在布线上产生的不利影响。',mode:'条件适用'},
  H058:{description:'仓储场所在岗人员消防安全教育频次低于至少每半年一次的要求，或员工上岗、转岗前未开展消防安全培训。',mode:'直接适用'},
  H059:{description:'仓储场所未按GB 50057设置防雷与接地系统，或未按XF 1131规定的周期开展检测。',mode:'直接适用',note:'XF 1131—2014第8.11条要求一般仓储场所防雷与接地系统每年检测一次，其中甲、乙类仓储场所防雷装置每半年检测一次。应结合场所火灾危险性分类适用检测周期。'},
  H060:{description:'仓储场所消火栓无明显标志，室内消火栓箱上锁或箱内设备不齐全、不完好，或距室外消火栓、水泵接合器2m范围内设置影响正常使用的障碍物。',mode:'直接适用'},
  H061:{description:'生产经营项目、场所发包或出租后，生产经营单位未对承包、承租单位安全生产工作统一协调、管理，未定期进行安全检查，或发现安全问题后未及时督促整改。',mode:'直接适用'},
  H062:{description:'仓储场所未做到每月至少组织一次防火检查，或部门（班组）未做到每周至少开展一次防火检查。',mode:'直接适用'},
  H063:{description:'甲、乙类危险物品储存在科研建筑的地下室或半地下室内。',mode:'直接适用'},
  H064:{title:'危险废物未按要求设置贮存设施或贮存场所',description:'产生、收集、贮存、利用、处置危险废物的单位未按现行标准建造危险废物贮存设施或设置贮存场所，或未根据需要选择适当的贮存设施类型。',mode:'直接适用',note:'已按GB 18597—2023现行条文纠正旧版“必须建造专用贮存设施”的表述。现行标准允许依法设置贮存设施或贮存场所，并根据危险废物类别、数量、形态、理化性质和环境风险确定类型与规模。'},
  H065:{description:'易燃气体与助燃气体在同一库房内储存。',mode:'直接适用'},
  H066:{title:'消防车道净宽度或净空高度不满足消防车通行要求',aliases:['消防车道净宽不足','消防车道净空高度不足','消防车通行条件不足'],description:'消防车道或兼作消防车道的道路，其净宽度或净空高度不能满足消防车安全、快速通行要求。',mode:'直接适用',note:'现行《建筑防火通用规范》GB 55037—2022第3.4.5条不再把所有场景机械表述为统一“4m”；应根据需要通行的消防车参数及现行相关技术标准核定。旧GB 50016—2014第7.1.8相关强制性条文已被废止。'},
  H067:{description:'仓储场所未组织或协助有关部门对消防安全责任人、消防安全管理人、消防控制室值班操作人员开展消防安全专门培训。',mode:'直接适用'},
  H068:{title:'不相容危险废物接触或混合贮存',aliases:['不相容危废混合贮存','危废相容性管理不到位','不相容危废未隔离'],description:'危险废物贮存设施未设置必要的贮存分区，导致不相容危险废物存在接触、混合风险。',mode:'直接适用',note:'已按GB 18597—2023现行条文替换旧版“同一容器内禁止混装”的表述；现行要求强调分类贮存并避免不相容危险废物接触、混合。'},
  H069:{description:'库房内堆垛上部与楼板、平屋顶之间的距离小于0.3m；人字屋架应从横梁算起。',mode:'直接适用'},
  H070:{description:'适用HJ 2026—2013的吸附法有机废气治理工程中，吸附操作周期内吸附床温度控制不符合要求，或温度超过83℃时不能自动报警并立即启动降温装置。',mode:'条件适用'},
  H071:{description:'电气作业人员在作业前未熟悉作业环境，或未根据作业类型和性质采取相应防护措施。',mode:'条件适用'},
  H072:{description:'电气作业使用的电工个体防护用品不合格或与作业活动不相适应；属于特种作业的电气作业人员未取得相应特种作业操作资格即上岗。',mode:'条件适用'},
  H073:{description:'在具有火灾、爆炸危险的场所吸烟、使用明火，或因施工等特殊情况需要明火作业时未按规定事先办理审批手续并采取相应消防安全措施。',mode:'直接适用'},
  H074:{description:'进行电焊、气焊等具有火灾危险作业的人员未按规定持证上岗，或作业时未遵守消防安全操作规程。',mode:'直接适用'},
  H075:{description:'江苏省工业企业危险化学品使用作业场所占用疏散通道，或设置影响逃生和灭火救援的障碍物。',mode:'条件适用'},
  H076:{title:'喷漆室通风系统不符合安全要求',aliases:['喷漆房通风不足','喷漆区可燃气体浓度控制不符合','喷漆室通风不符合'],description:'喷漆区通风量不能确保可燃气体浓度不大于其爆炸下限的25%。',mode:'直接适用',note:'原候选引用GB 14444—2006“喷漆室应设置安全通风装置和去除漆雾装置”已不再作为现行直接条文。GB 14444—2025已于2026-08-01实施并替代旧版，本条按现行5.3.1核验。'},
  H077:{description:'使用强酸、强碱等存在化学品危险隐患的实验室，未就近设置应急洗眼器及应急喷淋。',mode:'直接适用'},
  H078:{description:'危险废物产生单位未对本单位工作人员开展危险废物相关培训。',mode:'直接适用'},
  H079:{description:'生产经营单位在建设项目初步设计时，未委托具有相应资质的设计单位对安全设施同时进行设计并编制安全设施设计。',mode:'直接适用'},
  H080:{description:'易发生火灾、爆炸、极低温或其他危险化学品事故的实验室与其他用房相邻时，未形成独立防护单元，或耐火分隔、防火门窗、独立通风、泄压等措施不符合要求。',mode:'直接适用'},
  H081:{description:'生产经营单位未制定本单位生产安全事故应急救援预案，未与所在地县级以上地方人民政府组织制定的相关预案相衔接，或未定期组织演练。',mode:'直接适用'}
};

const defaultNote = '依据现行有效法律、法规、规章或标准于2026-09-08完成复核。现场适用时仍应结合单位行业属性、场所类别、工艺条件、危险物质特性及标准适用范围综合判断。';

for (const name of targetFiles) {
  const file = path.join(BATCH_DIR, name);
  const batch = JSON.parse(await fs.readFile(file, 'utf8'));
  for (const hazard of batch.hazards ?? []) {
    if (!/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(hazard.id)) continue;
    Object.assign(hazard, hazardPatch[hazard.id] ?? {});
    hazard.status = '已核验';
    hazard.checked = CHECKED;
    if (!hazardPatch[hazard.id]?.note) hazard.note = defaultNote;
  }
  for (const law of batch.laws ?? []) if (lawPatch[law.id]) Object.assign(law, lawPatch[law.id]);
  if (name.endsWith('003d.json')) {
    batch.laws ??= [];
    if (!batch.laws.some(x => x.id === newLaw.id)) batch.laws.push(newLaw);
  }
  for (const clause of batch.clauses ?? []) {
    const patch = clausePatch[clause.id];
    if (patch) Object.assign(clause, patch, {checked:CHECKED,status:'已核验'});
  }
  for (const link of batch.links ?? []) {
    if (/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(link.hazardId)) {
      link.role = link.role.includes('候选') ? '直接依据' : link.role;
      link.priority = 10;
    }
  }
  if (batch.ingestionSummary) {
    batch.ingestionSummary.newPendingHazards = 0;
    batch.ingestionSummary.verifiedHazards = (batch.hazards ?? []).filter(x => x.status === '已核验').length;
    batch.ingestionSummary.note = 'Batch 003 已完成逐条法规/标准复核；存在旧版或错误条款的记录已按现行有效依据修正。';
  }
  await fs.writeFile(file, JSON.stringify(batch, null, 2) + '\n', 'utf8');
}

console.log('Batch 003 migration applied: H033-H081 marked verified with corrected current legal/standard bases.');
