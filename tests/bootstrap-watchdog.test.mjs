import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../web/js/bootstrap-watchdog.js',import.meta.url),'utf8');
function setup({caches,serviceWorker}={}){
  const nodes=new Map(['loadStatus','loadTitle','loadMessage','loadActions','summary','retryLoad','recoverCache'].map(id=>[id,{hidden:id==='loadActions',textContent:'',disabled:false,classList:{add(value){this[value]=true}}}]));
  const timers=new Map();const events=new Map();let next=0,reloads=0;
  const context={document:{getElementById:id=>nodes.get(id)},navigator:serviceWorker?{serviceWorker}:{},location:{href:'https://test.invalid/safety-basis/index.html?v=release',reload(){reloads++}},URL,Promise,
    setTimeout(fn,ms){timers.set(++next,{fn,ms});return next},clearTimeout(id){timers.delete(id)}};
  context.window=context;context.addEventListener=(type,fn)=>events.set(type,fn);if(caches)context.caches=caches;
  vm.createContext(context);new vm.Script(source).runInContext(context);
  return {nodes,timers,events,api:context.__safetyBasisBoot,get reloads(){return reloads}};
}
test('missing module shows a bounded startup failure with working reload and cache recovery controls',()=>{
  const app=setup();assert.equal([...app.timers.values()][0].ms,20000);
  [...app.timers.values()][0].fn();
  assert.equal(app.nodes.get('loadActions').hidden,false);
  assert.match(app.nodes.get('loadMessage').textContent,/脚本未能加载/);
  app.nodes.get('retryLoad').onclick();assert.equal(app.reloads,1);
});
test('successful module start cancels the watchdog before core loading takes over',()=>{
  const app=setup();app.api.start();assert.equal(app.timers.size,0);
  assert.equal(app.nodes.get('loadActions').hidden,true);
});
test('a failed application script produces an immediate actionable reason',()=>{
  const app=setup();app.events.get('error')({target:{tagName:'SCRIPT',src:'https://test.invalid/safety-basis/app.js?v=release'}});
  assert.equal(app.timers.size,0);assert.match(app.nodes.get('loadMessage').textContent,/检索脚本加载失败/);
});
test('cache recovery clears only this application cache prefix and exact application scope',async()=>{
  const deleted=[],unregistered=[];
  const app=setup({caches:{keys:async()=>['safety-basis-v1','other-project-v1','safety-basis-v2'],delete:async key=>deleted.push(key)},serviceWorker:{getRegistrations:async()=>[
    {scope:'https://test.invalid/safety-basis/',unregister:async()=>unregistered.push('app')},
    {scope:'https://test.invalid/',unregister:async()=>unregistered.push('root')},
    {scope:'https://test.invalid/other/',unregister:async()=>unregistered.push('other')},
  ]}});
  await app.api.recover();
  assert.deepEqual(deleted,['safety-basis-v1','safety-basis-v2']);assert.deepEqual(unregistered,['app']);assert.equal(app.reloads,1);
});
test('cache cleanup error leaves direct reload usable and explains why retry is needed',async()=>{
  const app=setup({caches:{keys:async()=>{throw new Error('storage unavailable')}}});await app.api.recover();
  assert.equal(app.reloads,0);assert.equal(app.nodes.get('recoverCache').disabled,false);
  assert.match(app.nodes.get('loadMessage').textContent,/storage unavailable/);
  app.nodes.get('retryLoad').onclick();assert.equal(app.reloads,1);
});
