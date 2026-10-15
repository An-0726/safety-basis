// Ambiguous field wording must not silently acquire a site, duty or defect.
import {fieldQueryGuidance} from './field-query-guidance.js';
const suggestion=(label,query,note)=>({label,query,note});
export function hazardSearchGuidance(value){
  const query=String(value??'').normalize('NFKC').replace(/\s+/g,'').replace(/[，。？！?!]/g,'');
  const fieldGuidance=fieldQueryGuidance(query);
  if(fieldGuidance)return fieldGuidance;
  // A missing sign is not a failed lamp, and a missing extinguisher is not a placement defect.
  const absence='(?:未(?:设置|安装|装设|配置)|没有(?:设置|安装|装|配置|放)|没(?:设置|安装|装|配置|放|配)|未装|未设|缺少|缺失)(?:过|了)?';
  const absentSign=new RegExp('^(?:安全出口(?:指示|标志)灯|(?:疏散|出口)(?:指示|标志)灯|(?:安全出口|疏散)指示标志(?:灯(?:具)?)?)'+absence+'$');
  if(absentSign.test(query))return {
    suppressResults:true,notice:'未设置指示标志与已经设置但灯具损坏是不同缺陷；还需核实建筑、场所和标志类型。',
    suggestions:[suggestion('查灯光疏散指示标志未设置','应设灯光疏散指示标志的场所未设置或位置、方向不符合要求','仅适用于条款列明应设置的建筑和场所；不能用灯具故障或接线盒安装规则替代。')],
  };
  if(new RegExp('^(?:(?:车间|仓库)(?:里)?)?灭火器'+absence+'$').test(query)||/^(?:(?:车间|仓库)(?:里)?)?(?:没有|没配)灭火器$/.test(query))return {
    suppressResults:true,notice:'未配置灭火器与摆放不稳、铭牌朝向或维护失效是不同问题；先确认建筑与配置条件。',
    suggestions:[suggestion('查建筑灭火器配置要求','应配置灭火器的建筑内未配置灭火器','须核实建筑、使用性质和应配置条件；不能仅因提到灭火器就套用某地充电场所规则。')],
  };
  if(/^插座(?:坏(?:了)?|损坏|破损|不通电|烧坏(?:了)?)$/.test(query))return {
    suppressResults:true,notice:'插座使用中损坏与安装验收时面板未固定牢固不是同一缺陷。请按实际情况区分破损、松动、接地或不通电；本站现有安装验收条目不能直接据此判定使用期损坏。',suggestions:[],
  };
  if(/^叉车(?:(?:没有|没|未)(?:进行)?(?:年检|定期检验)|年检(?:过期|超期)|定期检验(?:过期|超期))$/.test(query))return {
    suppressResults:true,notice:'定期检验与首次投入使用前的首次检验不同。请先确认有效期、是否已申报，以及是否仍在使用。',
    suggestions:[
      suggestion('查未申报定期检验','特种设备未按要求办理定期检验','用于核查是否按要求申报；“没有年检”本身不能证明未申报。'),
      suggestion('查未经定期检验仍继续使用','特种设备未经定期检验或检验不合格仍继续使用','须另行确认仍继续使用，不能由检索原话自动补入这一事实。'),
    ],
  };
  if(/^(?:危化品|危险化学品)(?:仓库|库房|暂存间)(?:没有|没|未)(?:设置|安装)?通风(?:设施|设备|装置)?$/.test(query))return {
    suppressResults:true,notice:'通风设施要求须结合物料危险特性和储存条件确认；没有通风不能改判为灯具不防爆。',
    suggestions:[suggestion('查危化品储存安全设施条件','危险化学品储存单位未按种类危险特性设置相应安全设施','仅在确认属于危险化学品储存单位后核查相应设施，不代表所有仓库都必须设置同一套通风设备。')],
  };
  if(/^安全出口(?:上锁|锁了|锁住(?:了)?|锁闭(?:了)?)$/.test(query))return {
    suppressResults:true,notice:'先确认该门是否承担疏散功能及是否影响通行；普通出口门与控制人员出入的门禁、闸口须分别核查。',
    suggestions:[
      suggestion('查疏散出口通行条件','疏散通道、安全出口或消防车通道被占用、堵塞、封闭','须核实出口疏散用途及实际占用、堵塞或封闭情况，检索原话不能替代现场核实。'),
      suggestion('查门禁或闸口疏散出口','控制人员出入的闸口或门禁疏散出口火灾释放、内部开启或标识不符合要求','仅在确认属于门禁或闸口疏散出口后核查，不能替代所有普通出口门的要求。'),
    ],
  };
  // Explicit installation absence must not broaden into faults of installed lamps.
  const absentLight=/^(?:消防)?(?:应急(?:照明)?灯(?:具)?|(?:疏散|应急|通道)照明(?:灯(?:具)?)?)(?:未(?:设置|安装|装设)|没有(?:设置|安装|装)|没(?:设置|安装|装)|未装|未设|缺少|缺失)(?:过|了)?$/;
  const absentLightInPassage=/^通道(?:缺少|缺失|未设置|未安装|没装|没有)(?:疏散|应急)?(?:照明|灯)(?:了)?$/;
  if(absentLight.test(query)||absentLightInPassage.test(query))return {
    suppressResults:true,notice:'未安装、未设置与已装灯具损坏是不同缺陷。请先确认是否依法需要配置，以及具体建筑和部位。',
    suggestions:[suggestion('查建筑疏散照明未设置','应设疏散照明的建筑部位未设置疏散照明','仅适用于条款列明的建筑、部位及例外，须核实现场条件；不代表所有通道都须设应急灯。')],
  };
  if(/^(?:疏散)?通道(?:没|没有)灯(?:了)?$/.test(query))return {
    suppressResults:true,notice:'请先区分普通照明、疏散照明和疏散指示标志；未设置与灯具损坏是不同缺陷。',
    suggestions:[
      suggestion('查疏散照明未设置','应设疏散照明的建筑部位未设置疏散照明','仅适用于条款列明的建筑、部位及例外，不代表所有通道都必须设应急灯。'),
      suggestion('查已设应急灯损坏','已设置的消防应急照明灯具损坏、不能正常点亮','仅在已经设置灯具且功能失效时使用。'),
      suggestion('查疏散指示灯损坏','安全出口或疏散指示标志灯具损坏、不能正常指示','指示标志与照明功能分别核查。'),
    ],
  };
  const oilyFloor=/^((?:普通)?(?:工业|机械)?车间(?:里)?)?(?:地上|地面)(?:有油(?:污)?|湿滑)(?:了)?$/.exec(query);
  if(oilyFloor)return {
    suppressResults:true,notice:'请核实场所和实际滑跌风险；餐饮食品处理区的防滑要求不能直接套用于普通工业车间。',
    suggestions:!oilyFloor[1]?[suggestion('查看餐饮食品处理区防滑','餐饮食品处理区地面未保持防滑','仅供确认属于餐饮食品处理区后选择；普通车间油污的对题依据仍待补。')]:[],
  };
  if(/^(?:化学品|普通化学品|危化品)(?:随便放|乱放)(?:了)?$/.test(query))return {
    suppressResults:true,notice:'请先确认是否属于危险化学品，以及生产储存、仓库储存等具体情形；“随便放”不足以确定缺陷。',
    suggestions:query.startsWith('普通')?[]:[
      suggestion('查生产过程危化品分类储存','生产过程危险化学品未按物性分区分类储存','须先确认物料属于危险化学品，并核对生产过程及物性条件。'),
      suggestion('查危化品仓库储存方式','危险化学品仓库未采用规定的储存方式','仅适用于危险化学品仓库，不能代表普通化学品均适用。'),
    ],
  };
  if(/(?:旋转|转动|车床|钻床|钻孔).*(?:没|未|没有)(?:正确)?(?:佩戴|戴)手套/.test(query))return {
    suppressResults:true,notice:'旋转作业不能仅凭未戴手套判定不符合。应先评估手部防护需求及装备造成的缠绕等附加风险。',
    suggestions:[suggestion('查看手部防护装备附加风险','手部防护装备的选用增加缠绕或点火等风险','这是装备选用引入风险的规则，不代表所有旋转作业都必须戴手套或都禁止戴手套。')],
  };
  if(/(?:气瓶|钢瓶).*(?:没|缺|无|未).*防震(?:胶)?圈/.test(query))return {
    suppressResults:true,notice:'缺防震圈与缺瓶帽、保护罩不是同一缺陷。本站尚无可据此认定所有在用气瓶不符合要求的通用规则，应核实际瓶型、行业和装卸运输要求。',suggestions:[],
  };
  if(/^压力表(?:不走(?:了)?|不动(?:了)?|指针不动(?:了)?|玻璃(?:碎(?:了)?|破(?:了)?|破裂))$/.test(query))return {
    suppressResults:true,notice:'先确认压力表所属设备及实际缺陷；指针不动不能单独证明部件损坏，也不能当成未检定。',
    suggestions:[suggestion('查固定式压力容器压力表损坏','固定式压力容器压力表玻璃破裂、刻度不清或部件损坏','仅在确认固定式压力容器及条款列明的实际缺陷后使用；一般仪表或单纯示值不变须另核。')],
  };
  if(/^压力表检定(?:超期|过期)$/.test(query))return {
    suppressResults:true,notice:'检定超期与仪表损坏分开核查，并须确认所属设备及检定有效期。',
    suggestions:[suggestion('查固定式压力容器压力表检定','固定式压力容器压力表未经检定或超过检定有效期','仅在确认属于条款适用的固定式压力容器压力表后使用，不延伸到所有仪表。')],
  };
  if(/^(?:没戴|未戴|没有戴)手套$/.test(query))return {notice:'先核实岗位危害评估及手部防护需求；不能将所有作业一律要求戴手套，也不能把未佩戴当成防静电性能不合格。',suggestions:[]};
  if(/压力表(?:坏了|损坏|坏)$/.test(query))return {notice:'下列压力表损坏规则限固定式压力容器及条款列明的缺陷；一般仪表是否适用须另核，损坏不等于未检定。',suggestions:[]};
  if(/^材料堆太高(?:了)?$/.test(query))return {notice:'堆高须结合物料、堆垛基础和已核安全要求判断，不能套用统一高度；仓库顶部净距是另一项要求。',suggestions:[]};
  return {notice:'',suggestions:[]};
}
