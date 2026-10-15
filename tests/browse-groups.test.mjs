import test from 'node:test';
import assert from 'node:assert/strict';
import {BROWSE_GROUPS} from '../web/js/browse-groups.js';
import {searchHazardsDetailed} from '../web/js/search.js';
import {parseRoute,routeQuery} from '../web/app.js';

const row=(id,displayCategory,title='未设置防护')=>({id,title,displayCategory,searchText:title,aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国']});

test('六个入口无重复覆盖现有十二类，设备入口保留三类设备',()=>{
  const categories=BROWSE_GROUPS.flatMap(group=>group.categories);
  assert.equal(new Set(categories).size,12);
  assert.equal(categories.length,12);
  const rows=[row('E','电气安全'),row('M','机械设备与设施'),row('T','特种设备'),row('F','消防安全')];
  assert.deepEqual(new Set(searchHazardsDetailed(rows,'',{browse:'equipment'}).rows.map(r=>r.id)),new Set(['E','M','T']));
  assert.deepEqual(searchHazardsDetailed(rows,'',{browse:'equipment',category:'特种设备'}).rows.map(r=>r.id),['T']);
  assert.equal(searchHazardsDetailed(rows,'',{browse:'unknown'}).rows.length,0);
});

test('分类与关键词共同生效，入口分享刷新后仍保留筛选',()=>{
  const rows=[row('A','消防安全','灭火器失压'),row('B','消防安全','通道堵塞'),row('C','特种设备','压力表失压')];
  const route=parseRoute(routeQuery({view:'hazards',query:'失压',filters:{browse:'fire'}}));
  assert.equal(route.filters.browse,'fire');
  assert.deepEqual(searchHazardsDetailed(rows,route.query,route.filters).rows.map(r=>r.id),['A']);
});
