// Ambiguous field wording must not silently acquire a site, duty or defect.
const suggestion=(label,query,note)=>({label,query,note});
export function hazardSearchGuidance(value){
  const query=String(value??'').normalize('NFKC').replace(/\s+/g,'').replace(/[，。？！?!]/g,'');
  if(/^(?:疏散)?通道(?:没|没有)灯(?:了)?$/.test(query))return {
    suppressResults:true,notice:'请先区分普通照明、疏散照明和疏散指示标志；未设置与灯具损坏是不同缺陷。',
    suggestions:[
      suggestion('查疏散照明未设置','应设疏散照明的建筑部位未设置疏散照明','仅适用于条款列明的建筑、部位及例外，不代表所有通道都必须设应急灯。'),
      suggestion('查已设应急灯损坏','已设置的消防应急照明灯具损坏、不能正常点亮','仅在已经设置灯具且功能失效时使用。'),
      suggestion('查疏散指示灯损坏','安全出口或疏散指示标志灯具损坏、不能正常指示','指示标志与照明功能分别核查。'),
    ],
  };
  if(/^(?:车间|工业车间|车间里)?地上有油(?:了)?$/.test(query))return {
    suppressResults:true,notice:'请核实场所和实际滑跌风险；餐饮食品处理区的防滑要求不能直接套用于普通工业车间。',
    suggestions:query.startsWith('地上')?[suggestion('查看餐饮食品处理区防滑','餐饮食品处理区地面未保持防滑','仅供确认属于餐饮食品处理区后选择；普通车间油污的对题依据仍待补。')]:[],
  };
  if(/^(?:化学品|普通化学品|危化品)(?:随便放|乱放)(?:了)?$/.test(query))return {
    suppressResults:true,notice:'请先确认是否属于危险化学品，以及生产储存、仓库储存等具体情形；“随便放”不足以确定缺陷。',
    suggestions:query.startsWith('普通')?[]:[
      suggestion('查生产过程危化品分类储存','生产过程危险化学品未按物性分区分类储存','须先确认物料属于危险化学品，并核对生产过程及物性条件。'),
      suggestion('查危化品仓库储存方式','危险化学品仓库未采用规定的储存方式','仅适用于危险化学品仓库，不能代表普通化学品均适用。'),
    ],
  };
  if(/(?:旋转|转动|车床|钻床|钻孔).*(?:没戴|未戴|没有戴)手套/.test(query))return {
    suppressResults:true,notice:'旋转作业不能仅凭未戴手套判定不符合。应先评估手部防护需求及装备造成的缠绕等附加风险。',
    suggestions:[suggestion('查看手部防护装备附加风险','手部防护装备的选用增加缠绕或点火等风险','这是装备选用引入风险的规则，不代表所有旋转作业都必须戴手套或都禁止戴手套。')],
  };
  if(/(?:气瓶|钢瓶).*(?:没|缺|无|未).*防震圈/.test(query))return {
    suppressResults:true,notice:'缺防震圈与缺瓶帽、保护罩不是同一缺陷。本站尚无可据此认定所有在用气瓶不符合要求的通用规则，应核实际瓶型、行业和装卸运输要求。',suggestions:[],
  };
  if(/^(?:没戴|未戴|没有戴)手套$/.test(query))return {notice:'先核实岗位危害评估及手部防护需求；不能将所有作业一律要求戴手套，也不能把未佩戴当成防静电性能不合格。',suggestions:[]};
  if(/压力表(?:坏了|损坏|坏)$/.test(query))return {notice:'下列压力表损坏规则限固定式压力容器及条款列明的缺陷；一般仪表是否适用须另核，损坏不等于未检定。',suggestions:[]};
  if(/^材料堆太高(?:了)?$/.test(query))return {notice:'堆高须结合物料、堆垛基础和已核安全要求判断，不能套用统一高度；仓库顶部净距是另一项要求。',suggestions:[]};
  return {notice:'',suggestions:[]};
}
