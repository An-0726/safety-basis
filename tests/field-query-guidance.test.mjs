import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed} from '../web/js/search.js';
import {fieldQueryGuidance} from '../web/js/field-query-guidance.js';

const corpus=JSON.parse(fs.readFileSync(new URL('./field-query-cases.json',import.meta.url),'utf8'));
const ids=[...new Set(corpus.cases.flatMap(c=>c.expectedTargetIds))];
const rows=ids.map(id=>{
  const h=JSON.parse(fs.readFileSync(new URL(`../knowledge/hazards/${id}.json`,import.meta.url),'utf8'));
  return {...h,lawNames:[],levels:[],scopes:['全国'],searchText:[h.title,...(h.aliases||[]),...(h.keywords||[])].join(' ').normalize('NFKC').toLowerCase()};
});
for(const intent of new Set(corpus.cases.map(c=>c.intent))){
  test(`现场检索意图 ${intent} 的对象、条件和既有目标`,()=>{
    for(const c of corpus.cases.filter(c=>c.intent===intent)){
      const guidance=fieldQueryGuidance(c.query);
      assert.ok(guidance,c.query);assert.equal(guidance.suppressResults,c.suppressResults,c.query);
      const result=searchHazardsDetailed(rows,c.query);
      assert.ok(result.queryNotice,c.query);
      if(c.suppressResults){
        assert.equal(result.rows.length,0,c.query);
        const reached=result.suggestions.flatMap(s=>{
          const found=searchHazardsDetailed(rows,s.query).rows;
          assert.ok(found.length,c.query+' -> '+s.query);
          assert.ok(found.every(r=>r.title===s.query),c.query+' -> '+s.query);
          return found.map(r=>r.id);
        });
        assert.deepEqual([...new Set(reached)].sort(),[...c.expectedTargetIds].sort(),c.query);
      }
    }
  });
}

test('完整现有标题保留；场景提示不抢占专用规则查询',()=>{
  for(const row of rows){
    assert.ok(!fieldQueryGuidance(row.title)?.suppressResults,row.id);
    assert.deepEqual(searchHazardsDetailed([row],row.title).rows.map(r=>r.id),[row.id]);
  }
});

test('明确否定缺陷、已完成和未查明表述不当作现场缺陷',()=>{
  for(const query of ['配电箱接地线没有断','材料垛没有歪','新员工已经培训合格','货架已装地脚螺栓','未查明电线头是否外露','仓库应急灯正常','今年已经做应急演练'])assert.equal(fieldQueryGuidance(query),null,query);
});

test('选择有条件建议仍保留专业和地区筛选',()=>{
  const result=searchHazardsDetailed(rows,'动火没办作业票',{category:'职业卫生',region:'江苏'});
  assert.equal(result.rows.length,0);
  for(const suggestion of result.suggestions)assert.equal(searchHazardsDetailed(rows,suggestion.query,{category:'职业卫生',region:'江苏'}).rows.length,0);
  assert.match(result.suggestions[2].note,/南京/);
});

test('完整标题只返回同名条目，筛选排除时不退回正文提及的其他义务',()=>{
  const title='噪声工程控制不能满足要求时未结合防降噪设施与个体防护';
  const a={...rows[0],id:'A',title,category:'职业卫生',searchText:title};
  const duplicate={...a,id:'B'};
  const incidental={...a,id:'BODY',title:'未按优先顺序采取降噪措施',category:'机械设备与设施'};
  const result=searchHazardsDetailed([a,duplicate,incidental],title);
  assert.deepEqual(result.rows.map(r=>r.id),['A','B']);
  assert.equal(searchHazardsDetailed([a,duplicate,incidental],title,{category:'机械设备与设施'}).rows.length,0);
  assert.equal(searchHazardsDetailed([a,duplicate,incidental],'噪声').rows.length,3);
});
