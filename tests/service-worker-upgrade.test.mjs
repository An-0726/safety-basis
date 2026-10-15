import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('缓存升级清理接管期间旧页面重新打开的命名空间，保留其他应用缓存',async()=>{
  const source=fs.readFileSync(new URL('../web/sw.js',import.meta.url),'utf8');
  const current=source.match(/const SHELL = '([^']+)'/)[1];
  const stale='safety-basis-shell-previous';
  const keys=new Set([current,stale,'another-app-cache']);
  const listeners=new Map();let claims=0,pending;
  vm.runInNewContext(source,{
    self:{addEventListener:(name,handler)=>listeners.set(name,handler),clients:{claim:async()=>{
      claims++;
      // A still-controlled page queues an old-worker cache open during takeover.
      await Promise.resolve();keys.add(stale);
    }}},
    caches:{keys:async()=>[...keys],delete:async key=>keys.delete(key)},
  });
  listeners.get('activate')({waitUntil:promise=>{pending=promise;}});
  await pending;
  assert.equal(claims,1);
  assert.deepEqual([...keys].sort(),[current,'another-app-cache'].sort());
});

test('页面模块加载完成后可清理迟到的旧缓存，其他消息不触发清理',async()=>{
  const source=fs.readFileSync(new URL('../web/sw.js',import.meta.url),'utf8');
  const current=source.match(/const SHELL = '([^']+)'/)[1];
  const keys=new Set([current,'safety-basis-shell-late','another-app-cache']);
  const listeners=new Map();let pending;
  vm.runInNewContext(source,{self:{addEventListener:(name,handler)=>listeners.set(name,handler)},caches:{keys:async()=>[...keys],delete:async key=>keys.delete(key)}});
  listeners.get('message')({data:{type:'unrelated-message'},waitUntil:()=>assert.fail('unexpected cleanup')});
  assert.ok(keys.has('safety-basis-shell-late'));
  listeners.get('message')({data:{type:'safety-basis:cleanup-shell-caches'},waitUntil:promise=>{pending=promise;}});
  await pending;
  assert.deepEqual([...keys].sort(),[current,'another-app-cache'].sort());
});
