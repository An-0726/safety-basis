from pathlib import Path
import json, sys
ROOT=Path('.').resolve(); KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools'/'v4'))
from canonical import content_hash
STAMP='2026-09-21T00:30:00+08:00'

def rd(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def wr(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rev(entity,etype,decision,reviewType,reason,evidenceRefs=None,extra=None):
    r={"entityType":etype,"entityId":entity['id'],"reviewType":reviewType,"decision":decision,
       "reviewedContentHash":content_hash(entity),"checkedAt":STAMP,"reviewer":"ChatGPT / Engineering Audit",
       "reason":reason,"evidenceRefs":evidenceRefs or []}
    if extra:r.update(extra)
    return r

def refresh_link_review(kid, decision=None, reason=None, evidenceRefs=None):
    link=rd(KNOW/'links'/f'{kid}.json'); rp=KNOW/'reviews'/'links'/f'{kid}.json'; r=rd(rp)
    h=rd(KNOW/'hazards'/f"{link['hazardId']}.json"); c=rd(KNOW/'clauses'/f"{link['clauseId']}.json")
    r['reviewedContentHash']=content_hash(link)
    r['contextHashes']={'hazard':content_hash(h),'clause':content_hash(c),'link':content_hash(link)}
    if decision is not None:r['decision']=decision
    if reason is not None:r['reason']=reason
    if evidenceRefs is not None:r['evidenceRefs']=evidenceRefs
    r['checkedAt']=STAMP; r['reviewer']='ChatGPT / Engineering Audit'
    wr(rp,r)

m=rd(KNOW/'manifest.json')
m.setdefault('counts',{})['hazards']=2051;m['counts']['links']=1922;m['hazards']=2051;m['links']=1922
m['activeHazards']=1718;m['proposedHazards']=246;m['supersededHazards']=87;m['lifecycle']={'active':1718,'proposed':246,'superseded':87}

law={
 'aliases':['GB 14784-2013','GB14784-2013','带式输送机 安全规范'],
 'canonicalName':'带式输送机 安全规范','documentKind':'强制性国家标准','id':'LF_STD_GB14784',
 'identityKey':'带式输送机 安全规范|国家质量监督检验检疫总局、国家标准化管理委员会|cn|强制性国家标准',
 'issuer':'中华人民共和国国家质量监督检验检疫总局、国家标准化管理委员会','jurisdictionCode':'CN','lifecycle':'active'}
lv={
 'documentNumber':'GB 14784-2013','effectiveDate':'2014-07-01','endDate':'','id':'LV_STD_GB14784_2013','lawId':law['id'],
 'level':'强制性国家标准','officialName':'带式输送机 安全规范','scope':'CN',
 'sourceUrl':'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=B657F06CA772BEF9C6B2CFB95C63D0D7',
 'validityStatus':'active','versionKey':'2013-12-31'}
cl={
 'id':'C_GB14784_4_1_11_i','lawVersionId':lv['id'],'articlePath':'第4.1.11条i）',
 'quote':'沿输送机人行通道的全长应设置急停拉绳开关。拉绳开关的间距不得大于60 m。当输送机的长度小于30 m时，允许不设拉绳开关而用急停按钮代替，但从输送机长度方向上的任何一点到急停按钮的距离不得大于10 m。',
 'sourceUrl':'https://snamr.shaanxi.gov.cn/sy/ztzl/sbgxhxfpyjhx/bzcx/gjbz/202409/P020250320612395936729.pdf',
 'lifecycle':'active','jurisdictionCode':'CN'}
ev1={'id':'E_GB14784_STATUS_SAMR','locator':'国家标准全文公开系统：GB 14784-2013《带式输送机 安全规范》，状态现行，2013-12-31发布，2014-07-01实施。','page':'','retrievedAt':STAMP,'snapshotSha256':'','tier':'authoritative-public','url':lv['sourceUrl']}
ev2={'id':'E_GB14784_TEXT_SHAANXI','locator':'陕西省市场监督管理局公开GB 14784-2013全文，第4.1.11条i）急停拉绳/短于30m急停按钮替代要求。','page':'第11页；4.1.11 i）','retrievedAt':STAMP,'snapshotSha256':'','tier':'authoritative-public','url':cl['sourceUrl']}
h={
 'id':'H_BELT_CONVEYOR_ESTOP','title':'沿人行通道的带式输送机未按要求设置紧急停止装置',
 'description':'沿带式输送机人行通道全长未设置符合要求的紧急停止装置；输送机长度小于30 m时，如采用急停按钮替代拉绳开关，任一点至急停按钮的距离不应大于10 m。',
 'measures':'结合设备长度和人行通道布置整改：一般应沿人行通道全长设置急停拉绳开关，拉绳开关间距不大于60 m；输送机长度小于30 m时可用急停按钮代替，但应保证输送机长度方向任一点至急停按钮不大于10 m。整改后进行停机功能测试。',
 'conditions':'仅适用于GB 14784-2013适用范围内且沿输送机设有人行通道的带式输送机；长度小于30 m时不得机械要求必须设置拉绳急停，可按标准采用急停按钮替代。',
 'category':'机械设备安全','places':['粮食仓储','生产车间','仓储装卸'],
 'aliases':['输送带未设置急停','带式输送机未设置急停拉绳'],
 'keywords':['带式输送机','输送带','急停','拉绳急停','急停按钮','30m','10m'],'lifecycle':'active','mode':'direct','note':'2026-09-21商贸检查专项补录；不得在未确认设备长度及人行通道布置的情况下写死“必须拉绳急停”。','mergedInto':None}
k={'id':'K_BELT_CONVEYOR_ESTOP_GB14784_4_1_11_i','entityType':'link','hazardId':h['id'],'clauseId':cl['id'],'role':'direct','applicability':'适用于沿人行通道布置的带式输送机急停装置；长度小于30 m时允许急停按钮替代，但任一点至按钮不大于10 m。','jurisdictionCode':'CN','reason':'GB 14784-2013第4.1.11条i）直接规定该设备场景的急停拉绳及短机长按钮替代条件。','createdAt':'2026-09-21','lifecycle':'active','priority':10}
for d,o in [('laws',law),('law-versions',lv),('clauses',cl),('evidence',ev1),('evidence',ev2),('hazards',h),('links',k)]: wr(KNOW/d/f"{o['id']}.json",o)
wr(KNOW/'reviews'/'laws'/f"{law['id']}.json", rev(law,'law','verified','identity','国家标准全文公开系统核实GB 14784-2013标准身份、名称及现行状态。',[ev1['id']]))
wr(KNOW/'reviews'/'law-versions'/f"{lv['id']}.json", rev(lv,'lawVersion','verified','version','GB 14784-2013自2014-07-01实施，国家标准全文公开系统当前标注为现行；修订项目20254330-Q-339尚未替代现行版本。',[ev1['id'],ev2['id']]))
wr(KNOW/'reviews'/'clauses'/f"{cl['id']}.json", rev(cl,'clause','verified','text','陕西省市场监督管理局公开的GB 14784-2013全文核实第4.1.11条i）原文。',[ev2['id']]))
wr(KNOW/'reviews'/'hazards'/f"{h['id']}.json", rev(h,'hazard','verified','definition','隐患构成严格限定于第4.1.11条i）的设备场景，并保留小于30 m时急停按钮替代条件。',[ev1['id'],ev2['id']]))
kr=rev(k,'link','verified','applicability','隐患与GB 14784-2013第4.1.11条i）的适用对象、急停形式及距离条件直接对应。',[ev2['id']],{'contextHashes':{'hazard':content_hash(h),'clause':content_hash(cl),'link':content_hash(k)}})
wr(KNOW/'reviews'/'links'/f"{k['id']}.json",kr)

# Keep source/publication/law-index.json a 1:1 metadata projection of law versions.
pub_index_path=ROOT/'source'/'publication'/'law-index.json'
pub_index=rd(pub_index_path)
pub_index=[row for row in pub_index if row.get('id') != lv['id']]
pub_index.append({
 'id':lv['id'],'name':'带式输送机 安全规范 GB 14784-2013',
 'aliases':['带式输送机 安全规范','GB 14784-2013'],'documentNumber':lv['documentNumber'],
 'level':lv['level'],'scope':'全国','status':'现行有效','checked':'2026-09-21',
 'effectiveDate':lv['effectiveDate'],'sourceUrl':lv['sourceUrl'],'replaces':[],'replacedBy':[],
 'clauseRefs':[{'clauseId':cl['id'],'clauseShard':'','hazardIds':[h['id']]}],
 'hazardCount':1,'clauseCount':1,
 'searchText':'lv std gb14784 2013 带式输送机 安全规范 gb 14784 2013 国家质量监督检验检疫总局 国家标准化管理委员会 cn'
})
pub_index.sort(key=lambda row: str(row.get('id') or ''))
wr(pub_index_path,pub_index)

canon_id='H_43C6C076F9FC456DB09138A19A'; canon=rd(KNOW/'hazards'/f'{canon_id}.json')
old_title=canon['title']; canon.update({
 'title':'装有电器的可开启配电箱（柜）门与金属框架未可靠连接',
 'description':'装有电器的可开启配电箱（柜）门与金属框架接地端子之间未设置符合要求的保护连接。',
 'measures':'按GB 50303-2015第5.1.1条，对装有电器的可开启门与金属框架接地端子采用截面积不小于4 mm²的黄绿色绝缘铜芯软导线连接并设置标识，整改后检查连接可靠性。',
 'conditions':'仅适用于装有电器的可开启配电箱（柜）门。柜门未安装电器元件时，不得仅凭“未设软铜跨接线”直接判定本隐患。',
 'keywords':['配电箱','配电柜','柜门','箱门','装有电器','保护连接','接地端子','黄绿色软导线'],
 'aliases':sorted(set((canon.get('aliases') or [])+[old_title,'配电箱箱体与箱门未使用编织软铜线跨接','装有电器的可开启门未用黄绿绝缘软导线连接']))})
canon['note']='2026-09-21工程审计：将3条重复柜门跨接隐患归并为本条；适用前提收紧为“装有电器的可开启门”，避免把所有金属柜门一律认定为必须跨接。'
wr(KNOW/'hazards'/f'{canon_id}.json',canon)
hrp=KNOW/'reviews'/'hazards'/f'{canon_id}.json'; hr=rd(hrp); hr.update({'decision':'verified','reviewedContentHash':content_hash(canon),'checkedAt':STAMP,'reviewer':'ChatGPT / Engineering Audit','reason':'GB 50303-2015第5.1.1条直接适用于装有电器的可开启门；本次收紧适用条件并归并重复实体。'}); wr(hrp,hr)
refresh_link_review('K_43C6C076_GB50303_5_1_1',decision='verified',reason='GB 50303-2015第5.1.1条直接要求装有电器的可开启门与金属框架接地端子间采用规定软导线连接并标识。')
for dup,kid in [('H_5565236C0E354D5D8428BC1DEB','K_5565236C_GB50303_5_1_1'),('H_265A5682E86D43F0B813544099','K_265A5682_GB50303_5_1_1')]:
    d=rd(KNOW/'hazards'/f'{dup}.json'); d['lifecycle']='superseded'; d['mergedInto']=canon_id; d['note']=(d.get('note') or '')+'\n\n2026-09-21工程审计：与'+canon_id+'重复，保留Stable ID并归并。'; wr(KNOW/'hazards'/f'{dup}.json',d)
    rp=KNOW/'reviews'/'hazards'/f'{dup}.json'; rr=rd(rp); rr.update({'decision':'verified','reviewedContentHash':content_hash(d),'checkedAt':STAMP,'reviewer':'ChatGPT / Engineering Audit','reason':'重复隐患已归并至'+canon_id+'，历史Stable ID保留。'}); wr(rp,rr)
    l=rd(KNOW/'links'/f'{kid}.json'); l['lifecycle']='superseded'; wr(KNOW/'links'/f'{kid}.json',l)
    refresh_link_review(kid,decision='superseded',reason='对应重复隐患已归并至'+canon_id+'；原关联保留历史但不参与发布。')

hid='H_3B67F679C467451EA96B99072A'; wh=rd(KNOW/'hazards'/f'{hid}.json')
wh.update({
 'title':'库房物品堆放不符合仓储消防“五距”及分堆要求',
 'description':'库房物品堆放未按要求保持与楼板或平屋顶、照明灯、墙、柱以及相邻堆垛之间的安全距离，或未按要求分类、分堆、限额存放。',
 'measures':'按XF 1131-2014重新整理库房堆放：与楼板或平屋顶距离不小于0.3 m、与照明灯不小于0.5 m、与墙不小于0.5 m、与柱不小于0.3 m、堆垛之间不小于1 m；同时按第6.6条落实分类、分堆、限额和主通道要求。',
 'keywords':['仓储五距','五距','顶距','灯距','墙距','柱距','垛距','纸箱堆放','仓库堆垛']})
wh['note']='2026-09-21工程审计：按XF 1131-2014第6.6、6.8条收敛表述并补齐“五距”检索词；第6.8条具体距离直接进入正式关联。'
wr(KNOW/'hazards'/f'{hid}.json',wh)
hr=rd(KNOW/'reviews'/'hazards'/f'{hid}.json'); hr.update({'decision':'verified','reviewedContentHash':content_hash(wh),'checkedAt':STAMP,'reviewer':'ChatGPT / Engineering Audit','reason':'隐患表述已与XF 1131-2014第6.6条及第6.8条逐项对应。'}); wr(KNOW/'reviews'/'hazards'/f'{hid}.json',hr)
refresh_link_review('K_FIX_3B67F679C4_6',decision='verified',reason='XF 1131-2014第6.6条直接规定分类、分堆、限额存放及主通道要求。')
l8=rd(KNOW/'links'/'K_FIX_3B67F679C4_8.json'); l8['lifecycle']='active'; l8.pop('status',None); l8['reason']='XF 1131-2014第6.8条逐项规定顶距、灯距、墙距、柱距和垛距，为本隐患“五距”部分的直接依据。'; wr(KNOW/'links'/'K_FIX_3B67F679C4_8.json',l8)
refresh_link_review('K_FIX_3B67F679C4_8',decision='verified',reason='XF 1131-2014第6.8条逐项规定库房堆垛与楼板/平屋顶、照明灯、墙、柱及相邻堆垛的最小距离，直接支持“五距”隐患。')
refresh_link_review('K_1a74e03fdb2e62f935a360a9')

ph={
 'id':'H_EXTINGUISHER_REPAIR_CERT_MISSING','title':'经维修的灭火器未见维修合格证',
 'description':'现场能够确认灭火器已经维修，但灭火器本体未见维修合格证，无法核对维修编号、维修日期等追溯信息。',
 'measures':'先核对灭火器出厂日期、维修记录和实际维修状态；对已经维修的灭火器，核查维修单位及维修合格证，无法追溯或已达到维修、报废条件的按规定送修或更换。',
 'conditions':'仅适用于能够确认已经维修的手提式或推车式灭火器。尚未维修的原厂灭火器不能仅因无“维修合格证”判定本隐患。',
 'category':'消防安全','places':['仓库','生产车间','通用场所'],'aliases':['灭火器未见维修合格标识','灭火器未见检验合格标识'],
 'keywords':['灭火器','维修合格证','维修标识','维修日期','合格标识'],'lifecycle':'proposed','mode':'candidate',
 'note':'2026-09-21商贸检查专项候选。XF 95-2015当前状态已核实为现行，但本次未取得可作为正式证据链的官方标准全文原件，故不进入正式发布。','mergedInto':None}
wr(KNOW/'hazards'/f"{ph['id']}.json",ph)
wr(KNOW/'reviews'/'hazards'/f"{ph['id']}.json",rev(ph,'hazard','pending','definition','现场判定需要先确认灭火器确实经过维修；XF 95-2015官方身份/现行状态已核实，正式条款证据链待补。',[]))


# Audit wording cleanup: fire acceptance hazard should read as an inspection finding,
# not as a verbatim statutory obligation restatement.
fire_hid='H_E802C3AF73D1BDF70B0251EE4A_1'
fire_path=KNOW/'hazards'/f'{fire_hid}.json'
if fire_path.is_file():
    fire=rd(fire_path)
    old_title=fire.get('title') or ''
    fire['title']='建设工程未经消防验收或验收不合格即投入使用'
    fire['description']='依法应当进行消防验收的建设工程，未经消防验收或者消防验收不合格即投入使用。'
    fire['measures']='停止使用，依法申报并完成消防验收；消防验收合格后方可投入使用。'
    fire['conditions']='仅适用于依法应当进行消防验收的建设工程。现场检查应先确认该建设工程是否属于法定消防验收范围。'
    fire['aliases']=sorted(set((fire.get('aliases') or [])+[old_title])) if old_title else sorted(set(fire.get('aliases') or []))
    fire['note']='2026-09-21工程审计：将法条复述式标题改为检查记录表述，并删除与本隐患无直接关系的泛化整改内容。'
    wr(fire_path,fire)
    fire_review_path=KNOW/'reviews'/'hazards'/f'{fire_hid}.json'
    fire_review=rd(fire_review_path)
    fire_review['decision']='verified'
    fire_review['reviewedContentHash']=content_hash(fire)
    fire_review['checkedAt']=STAMP
    fire_review['reviewer']='ChatGPT / Engineering Audit'
    fire_review['reason']='隐患构成未变化，仅将法条复述式标题、描述和措施收敛为现场检查口径；仍限于依法应当进行消防验收的建设工程。'
    wr(fire_review_path,fire_review)
    for link_path in sorted((KNOW/'links').glob('*.json')):
        link=rd(link_path)
        if link.get('hazardId') != fire_hid:
            continue
        review_path=KNOW/'reviews'/'links'/f"{link['id']}.json"
        if not review_path.is_file():
            continue
        review=rd(review_path)
        review['reviewedContentHash']=content_hash(link)
        ctx=review.get('contextHashes') or {}
        ctx['hazard']=content_hash(fire)
        ctx['link']=content_hash(link)
        review['contextHashes']=ctx
        review['checkedAt']=STAMP
        review['reviewer']='ChatGPT / Engineering Audit'
        wr(review_path,review)

from collections import Counter
entity_dirs={'laws':'laws','lawVersions':'law-versions','clauses':'clauses','hazards':'hazards','links':'links','evidence':'evidence','successions':'successions','requirements':'requirements'}
for key,d in entity_dirs.items():
    cnt=len(list((KNOW/d).glob('*.json'))); m.setdefault('counts',{})[key]=cnt
    if key in m:m[key]=cnt
lc=Counter(rd(p).get('lifecycle') for p in (KNOW/'hazards').glob('*.json'))
m['activeHazards']=lc['active'];m['proposedHazards']=lc['proposed'];m['supersededHazards']=lc['superseded'];m['lifecycle']={k:lc[k] for k in ('active','proposed','superseded')};m['asOf']='2026-09-21'
if not any(x.get('id')=='commerce-audit-remediation-20260921' for x in m.setdefault('batches',[])):
    m['batches'].append({'id':'commerce-audit-remediation-20260921','lawsAdded':1,'lawVersionsAdded':1,'clausesAdded':1,'hazardsAdded':2,'hazardsMerged':2,'linksAdded':1,'evidenceAdded':2,'selection':'Engineering audit remediation: GB 14784-2013 conveyor emergency stop; cabinet-door duplicate merge; XF 1131-2014 five-distance direct link; extinguisher repair-certificate candidate boundary.'})
wr(KNOW/'manifest.json',m)
print('DONE',m['counts'],m['lifecycle'])
