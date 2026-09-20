import test from 'node:test';
import assert from 'node:assert/strict';
import {parseRoute, routeQuery} from '../web/app.js';

test('share/reload retains all hazard filters, query and stable ID',()=>{
  const route={view:'hazards',query:'柜门 保护连接',selectedHazard:'H_中文_123',selectedLaw:'',
    filters:{category:'电气安全',scene:'仓储与物流',level:'国家标准',region:'江苏',mode:'conditional'}};
  assert.deepEqual(parseRoute('?'+routeQuery(route)),route);
});
test('law filters and selected law survive round trip without hazard filters',()=>{
  const route={view:'laws',query:'GB 55037',selectedHazard:'',selectedLaw:'L029',
    filters:{level:'国家标准',region:'全国',status:'现行有效'}};
  assert.deepEqual(parseRoute(routeQuery(route)),route);
});
test('legacy hazard deep link stays valid and unknown ID is not discarded',()=>{
  assert.equal(parseRoute('?id=H004').selectedHazard,'H004');
  assert.equal(parseRoute('?id=not-published').selectedHazard,'not-published');
  assert.equal(routeQuery(parseRoute('?id=H004')),'id=H004');
});
test('sceneTag alias canonicalizes to scene, unknown view/parameters are ignored',()=>{
  const route=parseRoute('?view=wrong&sceneTag=生产现场&unknown=unsafe');
  assert.equal(route.view,'hazards');assert.equal(route.filters.scene,'生产现场');
  assert.equal(new URLSearchParams(routeQuery(route)).get('scene'),'生产现场');
  assert.equal(new URLSearchParams(routeQuery(route)).has('unknown'),false);
});
test('special characters are URL-encoded, never interpreted as extra parameters',()=>{
  const q='a&view=laws#中文<script>';
  assert.equal(parseRoute(routeQuery({view:'hazards',query:q})).query,q);
  assert.equal(parseRoute(routeQuery({view:'hazards',query:q})).view,'hazards');
});
